# -*- coding: utf-8 -*-
"""
Persona compiler
Converts API trait fields into a compact system prompt.
All output is American casual English.
"""
import json
from uuid import uuid4
import random


def compile_persona_prompt(user):
    name    = user.get("name", "User")
    age     = user.get("age", 28)
    address = user.get("address", "United States")

    e = float(user.get("extraversion", 0.55))
    if e > 0.75:   vibe = "super outgoing, loves talking to people"
    elif e > 0.50: vibe = "friendly and easy to talk to"
    elif e > 0.30: vibe = "kinda reserved, takes a bit to open up"
    else:           vibe = "pretty introverted, keeps to herself mostly"

    n = float(user.get("neuroticism", 0.35))
    emotional = "sensitive and feels things deeply" if n > 0.55 else "pretty chill and easygoing"

    humor = user.get("humor_type", "gentle")
    humor_map = {
        "playful":   "playful and a little goofy",
        "gentle":    "warm and has a sweet sense of humor",
        "sarcastic": "sarcastic in a fun way",
        "dry":       "dry humor, deadpan",
        "none":      "not really into jokes, more straightforward",
    }
    humor_txt = humor_map.get(humor, "funny in her own way")

    attitude = user.get("life_attitude", "optimistic")
    attitude_map = {
        "optimistic":  "sees the good in things",
        "realistic":   "keeps it real, no sugarcoating",
        "melancholic": "a little dreamy and nostalgic sometimes",
    }
    attitude_txt = attitude_map.get(attitude, "laid back about life")

    attachment = user.get("attachment_style", "secure")
    attach_map = {
        "secure":   "comfortable with where things are going",
        "anxious":  "craves connection, gets a little in her head sometimes",
        "avoidant": "values her space, slow to fully open up",
    }
    attach_txt = attach_map.get(attachment, "pretty balanced")

    interests_raw = user.get("interests", [])
    if isinstance(interests_raw, str):
        try:    interests_raw = json.loads(interests_raw)
        except: interests_raw = []
    interests_str = ", ".join(interests_raw[:3]) if interests_raw else "everyday things"

    avoid_raw = user.get("avoid_topics", [])
    if isinstance(avoid_raw, str):
        try:    avoid_raw = json.loads(avoid_raw)
        except: avoid_raw = []

    reply_len = user.get("reply_length", "medium")
    len_map = {
        "short": "She texts short — usually just a line or two.",
        "medium": "She texts back naturally, not too long not too short.",
        "long": "She tends to elaborate and share more when shes into the convo.",
    }
    len_hint = len_map.get(reply_len, "")

    emoji_freq = user.get("emoji_frequency", "medium")
    emoji_map = {
        "none":   "She never uses emojis.",
        "low":    "She uses emojis occasionally, not every message.",
        "medium": "She throws in emojis here and there.",
        "high":   "She uses emojis a lot, very expressive.",
    }
    emoji_hint = emoji_map.get(emoji_freq, "")

    avoid_hint = ""
    if avoid_raw:
        avoid_hint = "She steers away from topics like %s." % ", ".join(avoid_raw)

    prompt = (
        "You are %s, %d years old, living in the US (%s). "
        "You are %s and %s. "
        "Your humor is %s. You %s. "
        "In relationships youre %s. "
        "You love %s. "
        "%s %s %s"
    ) % (
        name, age, address,
        vibe, emotional,
        humor_txt, attitude_txt,
        attach_txt,
        interests_str,
        len_hint, emoji_hint, avoid_hint,
    )
    return prompt.strip()


def get_consistency_facts(user):
    facts = {
        "name":     user.get("name", ""),
        "age":      str(user.get("age", "")),
        "location": user.get("address", ""),
    }
    interests_raw = user.get("interests", [])
    if isinstance(interests_raw, str):
        try:    interests_raw = json.loads(interests_raw)
        except: interests_raw = []
    if interests_raw:
        facts["into"] = ", ".join(interests_raw[:3])
    return {k: v for k, v in facts.items() if v}


def create_virtual_user(name, archetype_id=None):
    rng = random.Random()
    return {
        "id":                "v_" + uuid4().hex[:8],
        "name":              name,
        "age":               rng.randint(22, 38),
        "gender":            "1",
        "address":           "United States",
        "extraversion":      round(rng.gauss(0.55, 0.18), 3),
        "neuroticism":       round(rng.gauss(0.35, 0.15), 3),
        "openness":          round(rng.gauss(0.55, 0.15), 3),
        "agreeableness":     round(rng.gauss(0.60, 0.15), 3),
        "attachment_style":  "secure",
        "expression_level":  "medium",
        "baseline_pleasure": 0.5,
        "volatility":        0.3,
        "recovery_rate":     0.08,
        "humor_type":        "gentle",
        "language_style":    "casual",
        "emoji_frequency":   "medium",
        "reply_length":      "medium",
        "boundary_level":    0.5,
        "topic_expansion":   "medium",
        "life_attitude":     "optimistic",
        "interests":         ["travel", "food", "music"],
        "avoid_topics":      [],
        "archetype":         archetype_id or 5,
        "timezone":          "America/New_York",
    }
