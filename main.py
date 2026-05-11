import patches  # 必须第一行，flash_attn mock
"""
本地测试入口
运行: python main.py
在 VS Code 终端输入消息，虚拟用户回复你
"""
import os
import sys
import time

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.api_store import APIPersonaStore
from storage.local import SQLiteStateStore
from persona.compiler import create_virtual_user
from agent.engine import VirtualAgentEngine
from agent.scheduler import ProactiveScheduler


# ── 初始化 ─────────────────────────────────────────────
persona_store = APIPersonaStore()   # fetches from API, caches locally
state_store   = SQLiteStateStore()   # persists across restarts
engine        = VirtualAgentEngine(persona_store, state_store)
scheduler     = ProactiveScheduler(state_store)

# ── 后台预加载 Florence-2（启动时就开始，不等用户发图）──
def _preload_florence():
    from config import FLORENCE_ENABLED, FLORENCE_MODEL_ID
    if not FLORENCE_ENABLED:
        return
    try:
        from input.image_analyzer import _load_model, _loaded
        if not _loaded:
            print("  [Florence-2] 后台预加载中，首次需要约1分钟...")
            _load_model(FLORENCE_MODEL_ID)
    except Exception as e:
        print("  [Florence-2] 预加载失败: %s" % e)

import threading
threading.Thread(target=_preload_florence, daemon=True).start()


def _seed_users():
    """如果数据库是空的，自动创建几个示例角色"""
    if persona_store.list_all_ids():
        return
    print("  首次运行，自动创建示例角色...")
    samples = [
        ("小雨", 0),   # 外向话痨大学生
        ("老陈", 1),   # 成熟职场人
        ("阿宅", 2),   # 内向宅系
        ("暖暖", 3),   # 温柔治愈
        ("刀子", 4),   # 毒舌型
    ]
    for name, arc in samples:
        user = create_virtual_user(name, archetype_id=arc)
        persona_store.save(user)
        print(f"    创建: {user['id']} — {name} (原型{arc})")
    print()


def _show_users():
    ids = persona_store.list_all_ids(limit=5)  # limit for testing, set None for all
    print("\n可用虚拟用户：")
    for uid in ids:
        u = persona_store.get(uid)
        print(f"  [{uid}] {u['name']}")
    print()


def _select_user() -> tuple[str, str]:
    """让用户选择对话对象，返回 (id, name)"""
    ids = persona_store.list_all_ids()
    if not ids:
        print("没有角色，请先创建")
        sys.exit(1)
    if len(ids) == 1:
        uid = ids[0]
        u   = persona_store.get(uid)
        print(f"自动选择: {u['name']} ({uid})\n")
        return uid, u["name"]

    _show_users()
    while True:
        choice = input("输入角色 ID（或直接回车选第一个）: ").strip()
        if not choice:
            uid = ids[0]
            break
        if choice in ids:
            uid = choice
            break
        print("  ID 不存在，重试")

    u = persona_store.get(uid)
    return uid, u["name"]


def _parse_input(raw: str) -> dict:
    """
    解析用户输入：
    - 普通文字 → text
    - 文件路径（.jpg/.png 等）→ image
    """
    raw = raw.strip()
    _, ext = os.path.splitext(raw)
    if ext.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.webp'} and os.path.exists(raw):
        return {"type": "image", "path": raw, "content": raw}
    return {"type": "text", "content": raw}


def _print_response(name: str, result: dict):
    """格式化打印回复"""
    print(f"\n  {name}: {result['text']}")
    if result.get("image_path"):
        print(f"  {name} 发了图片 → {result['image_path']}")
    if result.get("followup"):
        time.sleep(1)
        print(f"  {name}: {result['followup']}")

    debug = result.get("debug", {})
    if debug:
        tags = [
            f"情绪:{debug.get('mood','-')}",
            f"{debug.get('user_type','')}",
            f"记忆:{debug.get('memories',0)}条",
        ]
        print(f"  \033[2m[{' | '.join(t for t in tags if t)}]\033[0m")
    print()


def main():
    print("=" * 50)
    print("  Virtual Agent — 本地测试")
    print("  输入消息开始聊天，输入 'q' 退出")
    print("  可直接输入图片路径（如 /path/to/img.jpg）")
    print("=" * 50 + "\n")

    _seed_users()
    virtual_user_id, name = _select_user()

    # 检查是否需要主动打招呼（用 LLM 生成，每次不同）
    if scheduler.can_greet(virtual_user_id):
        persona       = persona_store.get(virtual_user_id)
        from persona.compiler import compile_persona_prompt
        persona_text  = compile_persona_prompt(persona) if persona else ""
        greeting = scheduler.generate_greeting(
            virtual_user_id, name,
            persona_prompt=persona_text,
            llm=engine.llm
        )
        if greeting:
            print("  %s: %s\n" % (name, greeting))

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if user_input.lower() in ("q", "quit", "exit"):
            print("退出")
            break
        if not user_input:
            # 空输入：检查超时
            timeout_msg = scheduler.get_timeout_message(virtual_user_id)
            if timeout_msg:
                print(f"\n  {name}: {timeout_msg}\n")
            continue

        msg = _parse_input(user_input)

        # 图片消息：两段式处理
        from input.normalizer import _URL_RE, is_image_request
        has_url = bool(_URL_RE.search(user_input)) and not is_image_request(user_input)

        if has_url:
            phase1, get_phase2 = engine.respond_image_twophase(virtual_user_id, msg)
            print("\n  %s: %s" % (name, phase1))
            print("  [分析图片中...]")
            phase2 = get_phase2(timeout=90)
            print("  %s: %s\n" % (name, phase2))
        else:
            result = engine.respond(virtual_user_id, msg)
            _print_response(name, result)


if __name__ == "__main__":
    main()
