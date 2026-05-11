# -*- coding: utf-8 -*-
import os
import random
from openai import OpenAI

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    IMAGES_DIR, UNANSWERED_THRESHOLD
)
from storage.base import PersonaStore, StateStore
from persona.compiler import compile_persona_prompt, get_consistency_facts
from emotion.engine import EmotionEngine
from memory.manager import MemoryManager
from agent.consistency import ConsistencyTracker
from agent.scheduler import ProactiveScheduler
from input.normalizer import normalize, is_image_request
from utils.time_context import get_time_context, time_aware_hint


class VirtualAgentEngine:
    def __init__(self, persona_store, state_store):
        self.personas = persona_store
        self.emotion = EmotionEngine(state_store)
        self.memory = MemoryManager(state_store)
        self.consistency = ConsistencyTracker(state_store)
        self.scheduler = ProactiveScheduler(state_store)
        self.llm = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=60.0,
            max_retries=1
        )

    def respond(self, virtual_user_id, raw_message, user_timezone="America/New_York", external_history=None,
                session_id=None):
        persona = self.personas.get(virtual_user_id)
        if not persona:
            return {"text": "hey sorry something went wrong on my end",
                    "image_path": None, "followup": None, "debug": {}}

        self.memory.start_session(session_id)
        self.scheduler.record_last_message(session_id)
        self.consistency.init_facts(session_id, get_consistency_facts(persona))

        text_input, input_type = normalize(raw_message)

        # Only send virtual user's image when user explicitly asks for one (text only)
        # Never trigger when user themselves sent an image
        msg_type = raw_message.get("type", "text")
        if input_type == "image_request" and msg_type != "image":
            return self._handle_image_request(virtual_user_id, persona, text_input, session_id=session_id)

        unanswered = self.scheduler.get_unanswered(session_id)
        continuity_hint = (
            "the person has sent a few messages you haven't really responded to yet. "
            "address what they actually said before jumping to anything new."
            if unanswered >= UNANSWERED_THRESHOLD else ""
        )

        mood = self.emotion.get_mood(session_id, persona.get("baseline_pleasure", 0.3))
        user_facts = self.memory.get_user_said_summary(session_id, n=4)

        # Long memory: semantic search from mem0 for relevant past context
        long_mem = self.memory.search(session_id, text_input, limit=4)
        if long_mem:
            mem_str = " | ".join(long_mem)
            user_facts = (user_facts + "\n[long term memory] " + mem_str) if user_facts else "[long term memory] " + mem_str

        system = self._build_system_prompt(
            persona, mood, user_timezone, input_type, continuity_hint, user_facts
        )
        history = external_history if external_history else self.memory.get_history_messages(session_id, n=12)

        response_text = self._call_llm(system, text_input, history)

        self.scheduler.reset_unanswered(session_id)
        self.emotion.decay(session_id, persona.get("baseline_pleasure", 0.3))
        if not response_text.startswith("(error"):
            self.memory.add_turn(session_id, text_input, response_text)

        followup = self.scheduler.get_image_followup(session_id)

        return {
            "text": response_text,
            "image_path": None,
            "followup": followup,
            "debug": {
                "mood": mood["level"],
                "user_type": self.memory.get_user_type_label(session_id),
                "memories": self.memory.turn_count(session_id),
                "input_type": input_type,
            }
        }

    def respond_image_twophase(self, virtual_user_id, raw_message, user_timezone="America/New_York",
                               external_history=None, session_id=None):
        import threading

        persona = self.personas.get(virtual_user_id)
        if not persona:
            return "hey something went wrong", None

        self.memory.start_session(session_id)
        self.scheduler.record_last_message(session_id)
        self.consistency.init_facts(session_id, get_consistency_facts(persona))

        mood = self.emotion.get_mood(session_id, persona.get("baseline_pleasure", 0.3))
        user_facts = self.memory.get_user_said_summary(session_id, n=4)
        history = external_history if external_history else self.memory.get_history_messages(session_id, n=10)

        system1 = self._build_system_prompt(
            persona, mood, user_timezone, "text", "", user_facts
        )
        system1 += (
            "\n[situation] they just sent you a photo but it hasnt loaded yet. "
            "react with excitement — short, natural, like youre genuinely waiting to see it."
        )
        phase1 = self._call_llm(system1, "(they sent a photo, give your first reaction)", history)

        content = (raw_message.get("content") or raw_message.get("url") or "").strip()
        result_holder = [None]
        done_event = threading.Event()

        def _analyze_and_build():
            desc = None
            from input.normalizer import _URL_RE, _download_image, _analyze
            m = _URL_RE.search(content)
            if m:
                url   = m.group(1)
                extra = m.group(2).strip()
            elif content.startswith(("http://", "https://")):
                url   = content
                extra = ""
            else:
                url   = None
                extra = content

            if url:
                tmp = _download_image(url)
                if tmp:
                    try:
                        desc = _analyze(tmp)
                    finally:
                        try: os.unlink(tmp)
                        except: pass

            if desc:
                img_info = "[photo content: %s]" % desc
                if extra:
                    img_info += " they said: %s" % extra
            else:
                if extra:
                    img_info = "[photo didnt load. they said it is: %s]" % extra
                else:
                    img_info = "[photo didnt load]"

            system2 = self._build_system_prompt(
                persona, mood, user_timezone, "image_from_user", "", user_facts
            )
            system2 += (
                "\n[situation] you already sent your first reaction. "
                "now actually comment on something specific you see in the photo, "
                "then naturally ask something. keep it short — 2 sentences max."
            )
            history2 = list(history) + [{"role": "assistant", "content": phase1}]
            text = self._call_llm(system2, img_info, history2)
            result_holder[0] = text
            if len(result_holder) == 1:
                result_holder.append(img_info)  # store for phase3

            combined = "%s | %s" % (phase1, text)
            self.memory.add_turn(session_id, content[:100], combined[:200])
            self.emotion.decay(session_id, persona.get("baseline_pleasure", 0.3))
            done_event.set()

        threading.Thread(target=_analyze_and_build, daemon=True).start()

        def get_phase2(timeout=90):
            done_event.wait(timeout=timeout)
            return result_holder[0] or "ok wait the photo still wont load lol can u resend"

        def get_phase3(timeout=90):
            """Third message - follow up from a different angle after phase2"""
            done_event.wait(timeout=timeout)
            if not result_holder[0]:
                return None
            # Build a follow-up that continues the image conversation
            system3 = self._build_system_prompt(
                persona, mood, user_timezone, "image_from_user", "", user_facts
            )
            system3 += (
                "\n[situation] you already reacted to their photo twice. "
                "now ask ONE natural follow-up question or make one more specific observation "
                "from a different angle — maybe the background, their expression, "
                "the vibe of the photo, or what you imagine the story behind it is. "
                "keep it to 1 sentence, make it feel spontaneous."
            )
            history3 = list(history) + [
                {"role": "assistant", "content": phase1},
                {"role": "assistant", "content": result_holder[0]},
            ]
            img_summary = result_holder[1] if len(result_holder) > 1 else "[photo]"
            return self._call_llm(system3, img_summary, history3)

        return phase1, get_phase2, get_phase3

    def _handle_image_request(self, virtual_user_id, persona, user_text, session_id=None):
        """
        Image sending is handled by the backend.
        We return send_image=True as a flag — backend picks the image
        from its own library and pushes it to the user via Firebase.
        """
        self.scheduler.mark_image_sent(session_id or virtual_user_id)
        pre = random.choice([
            "ok fine here",
            "lol fine",
            "omg ok here u go",
            "dont judge me lol",
            "k here",
            "fine fine",
        ])
        return {
            "text": pre,
            "send_image": True,  # backend: pick a random image and push to user
            "image_path": None,
            "followup": None,
            "debug": {"action": "image_requested"},
        }

    def _build_system_prompt(self, persona, mood, timezone,
                             input_type, continuity_hint, user_facts=""):
        from agent.prompt_rules import get_all_rules

        parts = [compile_persona_prompt(persona)]

        constraint = self.consistency.to_prompt_constraint(persona["id"])
        if constraint:
            parts.append(constraint)

        parts.append("current mood: " + self.emotion.to_text(mood))

        ctx = get_time_context(timezone)
        time_hint = time_aware_hint(ctx)
        if time_hint:
            parts.append(time_hint)

        if continuity_hint:
            parts.append(continuity_hint)

        # All behavioral rules loaded from prompt_rules.py
        parts.append(get_all_rules(input_type=input_type, user_facts=user_facts))

        return "\n".join(parts)

    def _call_llm(self, system, user_text, history=None):
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_text})
        try:
            resp = self.llm.chat.completions.create(
                model=DEEPSEEK_MODEL,
                max_tokens=150,
                timeout=55,
                messages=messages
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return "(error: %s)" % e


def _list_images(directory):
    if not os.path.exists(directory):
        return []
    exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.splitext(f)[1].lower() in exts
    ]
