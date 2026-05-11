# -*- coding: utf-8 -*-
"""
Release mode entry point
Run: py -3.11 -m uvicorn api:app --host 0.0.0.0 --port 8001
"""
import patches  # must be first
import time
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.api_store import APIPersonaStore
from storage.local import InMemoryStateStore
from agent.engine import VirtualAgentEngine
from agent.scheduler import ProactiveScheduler
from persona.compiler import compile_persona_prompt

app           = FastAPI(title="Virtual Agent API")
persona_store = APIPersonaStore()
state_store   = InMemoryStateStore()
engine        = VirtualAgentEngine(persona_store, state_store)
scheduler     = ProactiveScheduler(state_store)


# ── Models ────────────────────────────────────────────────────────

class HistoryMessage(BaseModel):
    role:    str    # "user" or "assistant"
    content: str

class RespondRequest(BaseModel):
    virtual_user_id: str
    real_user_id:    str
    message:         str
    message_type:    str         = "text"
    timezone:        str         = "America/New_York"
    history:         List[HistoryMessage] = []   # Laravel passes chat history here

class GreetRequest(BaseModel):
    virtual_user_id: str
    real_user_id:    str
    timezone:        str = "America/New_York"

class TimeoutCheckRequest(BaseModel):
    virtual_user_id: str
    real_user_id:    str


# ── Session key ───────────────────────────────────────────────────
def session_key(virtual_user_id: str, real_user_id: str) -> str:
    return "%s_%s" % (virtual_user_id, real_user_id)


# ── Endpoints ─────────────────────────────────────────────────────

@app.post("/agent/respond")
def respond(req: RespondRequest):
    sid = session_key(req.virtual_user_id, req.real_user_id)
    raw_message = {"type": req.message_type, "content": req.message}

    # Convert history from request into messages format
    history_messages = [{"role": h.role, "content": h.content} for h in req.history]

    # Two-phase for image URLs
    from input.normalizer import _URL_RE, is_image_request
    has_image_url = bool(_URL_RE.search(req.message)) and not is_image_request(req.message)

    if req.message_type == "image" or has_image_url:
        try:
            result = engine.respond_image_twophase(
                req.virtual_user_id,
                raw_message,
                req.timezone,
                external_history=history_messages,
                session_id=sid,
            )
            # respond_image_twophase returns (phase1, get_phase2_func)
            # get_phase2 can be None if persona not found
            if result is None or not callable(result[1]):
                # Fallback to regular respond
                fallback = engine.respond(req.virtual_user_id, raw_message, req.timezone,
                                          external_history=history_messages, session_id=sid)
                return {
                    "status":          True,
                    "virtual_user_id": req.virtual_user_id,
                    "real_user_id":    req.real_user_id,
                    "messages":        [{"text": fallback["text"], "send_image": False, "delay_seconds": 0}],
                }
            phase1, get_phase2, get_phase3 = result[0], result[1], result[2] if len(result) > 2 else None
            phase2 = get_phase2(timeout=90)
            messages = [{"text": phase1, "send_image": False, "delay_seconds": 0}]
            if phase2:
                messages.append({"text": phase2, "send_image": False, "delay_seconds": 3})
            # Phase 3: follow-up from a different angle
            if get_phase3 and callable(get_phase3):
                phase3 = get_phase3(timeout=90)
                if phase3:
                    messages.append({"text": phase3, "send_image": False, "delay_seconds": 6})
            return {
                "status":          True,
                "virtual_user_id": req.virtual_user_id,
                "real_user_id":    req.real_user_id,
                "messages":        messages,
            }
        except Exception as e:
            print("[API] image twophase error: %s" % e)
            # Fallback to regular respond
            fallback = engine.respond(req.virtual_user_id, raw_message, req.timezone,
                                      external_history=history_messages, session_id=sid)
            return {
                "status":          True,
                "virtual_user_id": req.virtual_user_id,
                "real_user_id":    req.real_user_id,
                "messages":        [{"text": fallback["text"], "send_image": False, "delay_seconds": 0}],
            }

    try:
        result = engine.respond(
            req.virtual_user_id,
            raw_message,
            req.timezone,
            external_history=history_messages,
            session_id=sid,
        )

        messages = [{"text": result["text"], "send_image": False, "delay_seconds": 0}]

        if result.get("send_image"):
            messages[0]["send_image"] = True

        if result.get("followup"):
            messages.append({
                "text":         result["followup"],
                "send_image":   False,
                "delay_seconds": 3,
            })

        return {
            "status":          True,
            "virtual_user_id": req.virtual_user_id,
            "real_user_id":    req.real_user_id,
            "messages":        messages,
            "debug":           result.get("debug", {}),
        }

    except Exception as e:
        import traceback
        print("[API] respond error: %s" % traceback.format_exc())
        return {
            "status":          False,
            "virtual_user_id": req.virtual_user_id,
            "real_user_id":    req.real_user_id,
            "error":           str(e),
            "messages":        [{"text": "hey give me a sec", "send_image": False, "delay_seconds": 0}],
        }


@app.post("/agent/greet")
def greet(req: GreetRequest):
    sid     = session_key(req.virtual_user_id, req.real_user_id)
    persona = persona_store.get(req.virtual_user_id)
    if not persona:
        return {"status": False, "message": "virtual user not found"}

    if not scheduler.can_greet(sid):
        return {"status": True, "triggered": False, "messages": []}

    persona_text = compile_persona_prompt(persona)
    text = scheduler.generate_greeting(
        sid,
        persona.get("name", ""),
        persona_prompt=persona_text,
        timezone=req.timezone,
        llm=engine.llm,
    )
    return {
        "status":          True,
        "virtual_user_id": req.virtual_user_id,
        "real_user_id":    req.real_user_id,
        "triggered":       True,
        "messages": [{"text": text, "send_image": False, "delay_seconds": 0}],
    }


@app.post("/agent/timeout_check")
def timeout_check(req: TimeoutCheckRequest):
    sid  = session_key(req.virtual_user_id, req.real_user_id)
    text = scheduler.get_timeout_message(sid)
    if not text:
        return {"status": True, "triggered": False, "messages": []}
    return {
        "status":          True,
        "virtual_user_id": req.virtual_user_id,
        "real_user_id":    req.real_user_id,
        "triggered":       True,
        "messages": [{"text": text, "send_image": False, "delay_seconds": 0}],
    }


@app.get("/agent/debug")
def debug_state(virtual_user_id: str, real_user_id: str):
    sid     = session_key(virtual_user_id, real_user_id)
    persona = persona_store.get(virtual_user_id)
    mood    = engine.emotion.get_mood(sid, 0.5)
    return {
        "session_key":     sid,
        "virtual_user_id": virtual_user_id,
        "real_user_id":    real_user_id,
        "persona_name":    persona.get("name") if persona else None,
        "mood":            mood,
    }


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": int(time.time())}
