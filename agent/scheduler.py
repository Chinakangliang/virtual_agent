# -*- coding: utf-8 -*-
import random
import time
import json
from storage.base import StateStore
from config import MAX_PROACTIVE_GREETINGS, TIMEOUT_MINUTES

IMAGE_FOLLOWUP = [
    "wait what do u think lol",
    "ok be honest",
    "right??",
    "thoughts??",
    "lol say something",
]

TIMEOUT_MESSAGES = [
    "heyyy u still there",
    "lol did u fall asleep",
    "ok i see how it is",
    "hellooo",
    "wait did i say something weird",
]


class ProactiveScheduler:
    def __init__(self, state_store):
        self.state = state_store

    def can_greet(self, virtual_user_id):
        count = int(self.state.get("greet_count:%s" % virtual_user_id) or 0)
        return count < MAX_PROACTIVE_GREETINGS

    def generate_greeting(self, virtual_user_id, name, persona_prompt="",
                          timezone="America/New_York", llm=None):
        if not self.can_greet(virtual_user_id):
            return None

        count = int(self.state.get("greet_count:%s" % virtual_user_id) or 0)
        self.state.set("greet_count:%s" % virtual_user_id, str(count + 1))

        hour = time.localtime().tm_hour
        if   hour < 6:  time_hint = "its the middle of the night"
        elif hour < 11: time_hint = "its morning"
        elif hour < 14: time_hint = "its midday"
        elif hour < 18: time_hint = "its afternoon"
        elif hour < 22: time_hint = "its evening"
        else:            time_hint = "its late night"

        styles = ["icebreaker", "suspense", "hook"]
        style  = styles[count % 3]

        style_prompt = {
            "icebreaker": "casual opener, just saying hey in a natural real-person way",
            "suspense":   "start with something that just happened to you, make them curious",
            "hook":       "ask something unexpected that makes them wanna respond",
        }[style]

        if llm:
            try:
                resp = llm.chat.completions.create(
                    model="deepseek-chat",
                    max_tokens=60,
                    timeout=30,
                    messages=[{
                        "role": "user",
                        "content": (
                            "%s. %s. %s. "
                            "send ONE opening text message to start a conversation. "
                            "write it like a real american woman texting — lowercase, "
                            "casual, no apostrophes in contractions, short. "
                            "output only the message, nothing else."
                        ) % (persona_prompt, time_hint, style_prompt)
                    }]
                )
                return resp.choices[0].message.content.strip()
            except Exception:
                pass

        fallbacks = [
            "hey",
            "omg ok i need to tell u something",
            "wait are u busy rn",
            "ok random but i was just thinking about u",
            "heyyy whats good",
            "so this just happened and i had to tell someone lol",
        ]
        random.seed(int(time.time() * 1000) % 99999)
        return random.choice(fallbacks)

    def mark_image_sent(self, virtual_user_id):
        self.state.set("pending_img_followup:%s" % virtual_user_id, "1", ttl_seconds=120)

    def get_image_followup(self, virtual_user_id):
        if self.state.get("pending_img_followup:%s" % virtual_user_id):
            self.state.delete("pending_img_followup:%s" % virtual_user_id)
            return random.choice(IMAGE_FOLLOWUP)
        return None

    def record_last_message(self, virtual_user_id):
        self.state.set("last_msg_time:%s" % virtual_user_id, str(time.time()), ttl_seconds=86400)

    def get_timeout_message(self, virtual_user_id):
        raw = self.state.get("last_msg_time:%s" % virtual_user_id)
        if not raw:
            return None
        if time.time() - float(raw) >= TIMEOUT_MINUTES * 60:
            self.record_last_message(virtual_user_id)
            return random.choice(TIMEOUT_MESSAGES)
        return None

    def increment_unanswered(self, virtual_user_id):
        key   = "unanswered:%s" % virtual_user_id
        count = int(self.state.get(key) or 0) + 1
        self.state.set(key, str(count), ttl_seconds=3600)
        return count

    def reset_unanswered(self, virtual_user_id):
        self.state.delete("unanswered:%s" % virtual_user_id)

    def get_unanswered(self, virtual_user_id):
        return int(self.state.get("unanswered:%s" % virtual_user_id) or 0)
