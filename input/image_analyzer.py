"""
Florence-2 图片描述模块
mock + from transformers import 必须在模块顶层紧挨着执行
"""
import sys
import types
import importlib.machinery
import os

# ── Step 1: mock flash_attn ───────────────────────────────
def _make_mock(name):
    if name in sys.modules:
        return
    mod = types.ModuleType(name)
    # importlib.machinery.ModuleSpec 保证不返回 None
    # find_spec() 靠 __spec__ != None 判断包是否存在
    mod.__spec__ = importlib.machinery.ModuleSpec(name, None)
    for attr in ['flash_attn_func', 'flash_attn_varlen_func',
                 'flash_attn_with_kvcache', 'index_first_axis',
                 'pad_input', 'unpad_input']:
        setattr(mod, attr, None)
    mod.__version__ = '2.0.0'
    if '.' in name:
        parent = sys.modules.get(name.rsplit('.', 1)[0])
        if parent:
            setattr(parent, name.rsplit('.', 1)[1], mod)
    sys.modules[name] = mod

_make_mock('flash_attn')
_make_mock('flash_attn.flash_attn_interface')
_make_mock('flash_attn.bert_padding')

# ── Step 2: 环境变量 ─────────────────────────────────────
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

# ── Step 3: 顶层 import（紧跟 mock，和 check_image.py 一致）
_torch_ok = False
_tf_ok    = False

try:
    import torch
    _torch_ok = True
except ImportError:
    print("  [Florence-2] torch 未安装")

try:
    from transformers import AutoProcessor, AutoModelForCausalLM
    _tf_ok = True
except Exception as e:
    print("  [Florence-2] transformers 导入失败: %s" % e)

# ── 懒加载模型实例 ────────────────────────────────────────
_model     = None
_processor = None
_device    = None
_dtype     = None
_loaded    = False


def _load_model(model_id):
    global _model, _processor, _device, _dtype, _loaded
    if not _torch_ok or not _tf_ok:
        raise RuntimeError("torch 或 transformers 未成功导入")

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _dtype  = torch.float16 if torch.cuda.is_available() else torch.float32

    print("  [Florence-2] 加载模型 (%s)，首次约 800MB..." % _device)
    _processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    _model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        torch_dtype=_dtype,
        attn_implementation="eager",
    ).to(_device)
    _model.eval()
    _loaded = True
    print("  [Florence-2] 模型加载完成")


def analyze_image(img_path, model_id, task="<MORE_DETAILED_CAPTION>"):
    global _loaded
    if not _loaded:
        try:
            _load_model(model_id)
        except Exception as e:
            return "（Florence-2 加载失败：%s）" % e
    try:
        from PIL import Image
        image  = Image.open(img_path).convert("RGB")
        inputs = _processor(
            text=task, images=image, return_tensors="pt"
        ).to(_device, _dtype)
        with torch.no_grad():
            generated_ids = _model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=512,
                num_beams=3,
                do_sample=False,
            )
        generated_text = _processor.batch_decode(
            generated_ids, skip_special_tokens=False
        )[0]
        result = _processor.post_process_generation(
            generated_text, task=task,
            image_size=(image.width, image.height)
        )
        return result.get(task, "（无结果）")
    except Exception as e:
        return "（图片识别出错：%s）" % e
