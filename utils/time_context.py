# -*- coding: utf-8 -*-
import pytz
from datetime import datetime


def get_time_context(timezone_str="America/New_York"):
    try:
        tz  = pytz.timezone(timezone_str)
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()

    hour    = now.hour
    weekday = now.weekday()

    if   6  <= hour < 11: period = "morning"
    elif 11 <= hour < 14: period = "noon"
    elif 14 <= hour < 18: period = "afternoon"
    elif 18 <= hour < 22: period = "evening"
    else:                  period = "late_night"

    return {
        "hour":       hour,
        "period":     period,
        "is_weekend": weekday >= 5,
        "weekday":    weekday,
        "timezone":   timezone_str,
    }


def time_aware_hint(time_ctx):
    p          = time_ctx["period"]
    is_weekend = time_ctx["is_weekend"]

    hints = {
        "morning":    "its morning for them, keep it light",
        "noon":       "its around lunch, natural to mention food",
        "afternoon":  "its afternoon, chill vibe",
        "evening":    "its evening, good for deeper convos",
        "late_night": "its late night, match that sleepy energy",
    }

    hint = hints.get(p, "")
    if is_weekend:
        hint += ", its the weekend so more relaxed"
    return hint
