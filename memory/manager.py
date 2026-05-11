import json, time
from storage.base import StateStore
from config import SHORT_SESSION_THRESHOLD

try:
    from config import MEM0_ENABLED
except ImportError:
    MEM0_ENABLED = False

SHORT_MEM_LIMIT = 30


class MemoryManager:
    def __init__(self, state_store):
        self.state = state_store
        self._mem0 = None

    def _get_mem0(self):
        if not MEM0_ENABLED:
            return None
        if self._mem0 is None:
            try:
                from mem0 import Memory
                from config import MEM0_CONFIG
                self._mem0 = Memory.from_config(MEM0_CONFIG)
            except Exception as e:
                print("  [Memory] mem0 unavailable: %s" % e)
                self._mem0 = False
        return self._mem0 if self._mem0 else None

    # ── 会话时长 ──────────────────────────────────
    def start_session(self, user_id):
        key = "session_start:%s" % user_id
        if not self.state.get(key):
            self.state.set(key, str(time.time()), ttl_seconds=7200)

    def is_valuable_user(self, user_id):
        start = self.state.get("session_start:%s" % user_id)
        if not start:
            return False
        return (time.time() - float(start)) >= SHORT_SESSION_THRESHOLD

    # ── 写对话历史 ────────────────────────────────
    def add_turn(self, user_id, user_text, assistant_text):
        """每轮对话存为 {user, assistant} 结构"""
        key   = "history:%s" % user_id
        raw   = self.state.get(key)
        turns = json.loads(raw) if raw else []
        turns.append({
            "user":      user_text[:300],
            "assistant": assistant_text[:300],
        })
        turns = turns[-SHORT_MEM_LIMIT:]
        self.state.set(key, json.dumps(turns, ensure_ascii=False), ttl_seconds=86400)

        # 可选：价值用户额外写 mem0
        if MEM0_ENABLED and self.is_valuable_user(user_id):
            m = self._get_mem0()
            if m:
                try:
                    m.add("user said: %s | replied: %s" % (user_text[:100], assistant_text[:100]),
                          user_id=user_id)
                except Exception:
                    pass

    # ── 读对话历史（返回 messages 格式）─────────────
    def get_history_messages(self, user_id, n=15):
        """
        直接返回 OpenAI messages 格式，传入 LLM 作为对话历史
        这是短期记忆的核心——LLM 能"看到"之前聊了什么
        """
        key   = "history:%s" % user_id
        raw   = self.state.get(key)
        turns = json.loads(raw) if raw else []
        msgs  = []
        for t in turns[-n:]:
            msgs.append({"role": "user",      "content": t["user"]})
            msgs.append({"role": "assistant",  "content": t["assistant"]})
        return msgs

    def turn_count(self, user_id):
        """当前已存的对话轮数"""
        raw = self.state.get("history:%s" % user_id)
        return len(json.loads(raw)) if raw else 0

    def search(self, user_id, query, limit=4):
        """Search mem0 for semantically relevant past memories."""
        if not MEM0_ENABLED:
            return []
        m = self._get_mem0()
        if not m:
            return []
        try:
            results = m.search(query, user_id=user_id, limit=limit)
            return [r["memory"] for r in results if r.get("memory")]
        except Exception:
            return []

    def get_user_type_label(self, user_id):
        return "valuable user" if self.is_valuable_user(user_id) else "regular user"

    def get_user_said_summary(self, user_id, n=4):
        """
        提取用户在本次对话中说过的内容，
        显式注入 system prompt，防止 LLM 忘记用户已告知的信息
        """
        key   = "history:%s" % user_id
        raw   = self.state.get(key)
        turns = json.loads(raw) if raw else []
        if not turns:
            return ""
        # 只取用户说的话，过滤掉太短的（hi/嗯/好）
        user_msgs = [t["user"] for t in turns[-n:] if len(t["user"]) > 3]
        if not user_msgs:
            return ""
        lines = ["- " + m[:80] for m in user_msgs]
        return "【用户在本次对话中告诉你的信息，务必记住不要再问】\n" + "\n".join(lines)
