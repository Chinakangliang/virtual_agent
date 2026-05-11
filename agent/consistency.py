"""
角色一致性模块
记录虚拟用户已说过的关键事实，生成 prompt 约束防止前后矛盾
"""
import json
from storage.base import StateStore


class ConsistencyTracker:
    def __init__(self, state_store: StateStore):
        self.state = state_store

    def get_facts(self, virtual_user_id: str) -> dict:
        """获取已记录的角色事实"""
        raw = self.state.get(f"facts:{virtual_user_id}")
        return json.loads(raw) if raw else {}

    def init_facts(self, virtual_user_id: str, base_facts: dict):
        """用原型基础事实初始化，只在空的时候执行"""
        if not self.get_facts(virtual_user_id):
            self.state.set(
                f"facts:{virtual_user_id}",
                json.dumps(base_facts, ensure_ascii=False)
            )

    def update_facts(self, virtual_user_id: str, new_facts: dict):
        """追加/更新已知事实"""
        facts = self.get_facts(virtual_user_id)
        facts.update(new_facts)
        self.state.set(
            f"facts:{virtual_user_id}",
            json.dumps(facts, ensure_ascii=False)
        )

    def to_prompt_constraint(self, virtual_user_id: str) -> str:
        """
        生成插入 system prompt 的一致性约束段
        约 15-30 token，防止矛盾
        """
        facts = self.get_facts(virtual_user_id)
        if not facts:
            return ""
        parts = [f"{k}是{v}" for k, v in facts.items()]
        return "【你已经告诉过对方：" + "，".join(parts) + "。绝对不能自相矛盾。】"
