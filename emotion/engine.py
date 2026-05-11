import json
from storage.base import StateStore

EVENT_IMPACT = {
    "received_like":     {"pleasure": +0.15, "arousal": +0.05},
    "received_comment":  {"pleasure": +0.12, "arousal": +0.08},
    "new_follower":      {"pleasure": +0.20, "arousal": +0.10},
    "ignored":           {"pleasure": -0.08, "arousal": -0.05},
    "argument":          {"pleasure": -0.25, "arousal": +0.25},
    "user_left":         {"pleasure": -0.10, "arousal": -0.10},
    "image_compliment":  {"pleasure": +0.18, "arousal": +0.08},
    "rude_message":      {"pleasure": -0.20, "arousal": +0.15},
    "long_chat":         {"pleasure": +0.10, "arousal": +0.05},
}


class EmotionEngine:
    def __init__(self, state_store: StateStore):
        self.store = state_store

    def get_mood(self, user_id: str, baseline_pleasure: float = 0.3) -> dict:
        raw = self.store.get(f"mood:{user_id}")
        if raw:
            return json.loads(raw)
        return {
            "pleasure": baseline_pleasure,
            "arousal":  0.0,
            "level":    self._classify(baseline_pleasure)
        }

    def apply_event(self, user_id: str, event: str, baseline: float = 0.3):
        mood   = self.get_mood(user_id, baseline)
        impact = EVENT_IMPACT.get(event, {})
        for k, v in impact.items():
            mood[k] = max(-1.0, min(1.0, mood.get(k, 0.0) + v))
        mood["level"] = self._classify(mood["pleasure"])
        self.store.set(f"mood:{user_id}", json.dumps(mood), ttl_seconds=21600)

    def decay(self, user_id: str, baseline_pleasure: float = 0.3):
        """向基线自然衰减，每次对话后调用"""
        mood = self.get_mood(user_id, baseline_pleasure)
        rate = 0.08
        mood["pleasure"] += (baseline_pleasure - mood["pleasure"]) * rate
        mood["arousal"]  += (0.0 - mood["arousal"]) * rate
        mood["level"]     = self._classify(mood["pleasure"])
        self.store.set(f"mood:{user_id}", json.dumps(mood), ttl_seconds=21600)

    def to_text(self, mood: dict) -> str:
        level = mood.get("level", "neutral")
        arousal = mood.get("arousal", 0.0)
        texts = {
            "happy":   "心情很好，有点兴奋，说话比较活泼",
            "good":    "今天状态不错，比较放松",
            "neutral": "心情平平，正常状态",
            "low":     "有点低落，不太想多说话，回复可以简短一些",
            "bad":     "很郁闷，能少说就少说，不想聊太多",
        }
        base = texts.get(level, "正常状态")
        if arousal > 0.5:
            base += "，情绪比较激动"
        return base

    @staticmethod
    def _classify(pleasure: float) -> str:
        if pleasure > 0.55:  return "happy"
        if pleasure > 0.25:  return "good"
        if pleasure > -0.1:  return "neutral"
        if pleasure > -0.4:  return "low"
        return "bad"
