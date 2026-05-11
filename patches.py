"""
必须在所有其他 import 之前执行
在 main.py 第一行 import patches 即可
"""
import sys
import types
import importlib.util


def apply_all():
    _mock_flash_attn()


def _mock_flash_attn():
    """
    Florence-2 / transformers 会检查 flash_attn，
    没装时需要提前塞入 mock，否则抛 KeyError / ImportError
    """
    MOCKS = {
        'flash_attn': {
            'flash_attn_func': None,
            'flash_attn_varlen_func': None,
            'flash_attn_with_kvcache': None,
            '__version__': '2.0.0',
        },
        'flash_attn.flash_attn_interface': {
            'flash_attn_func': None,
            'flash_attn_varlen_func': None,
            'flash_attn_with_kvcache': None,
        },
        'flash_attn.bert_padding': {
            'index_first_axis': None,
            'pad_input': None,
            'unpad_input': None,
        },
    }

    for mod_name, attrs in MOCKS.items():
        if mod_name in sys.modules:
            continue   # 已安装真实包，不覆盖
        mod = types.ModuleType(mod_name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        try:
            mod.__spec__ = importlib.util.spec_from_loader(mod_name, loader=None)
        except Exception:
            mod.__spec__ = None
        # 挂载到父模块
        if '.' in mod_name:
            parent_name, child = mod_name.rsplit('.', 1)
            parent = sys.modules.get(parent_name)
            if parent:
                setattr(parent, child, mod)
        sys.modules[mod_name] = mod


apply_all()
