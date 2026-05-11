# -*- coding: utf-8 -*-
import re
import os
import tempfile
from config import FLORENCE_MODEL_ID, FLORENCE_ENABLED

_IMAGE_REQUEST_PATTERNS = [
    r"send.{0,8}(pic|photo|picture|selfie|image)",
    r"show.{0,8}(pic|photo|picture|yourself|yourself)",
    r"(pic|photo|picture|selfie).{0,8}(please|pls|now|of you)",
    r"let me see (you|ur|your)",
    r"can i see (you|ur|your)",
]
_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}

_URL_RE = re.compile(
    r'(https?://[^\s]+\.(?:jpg|jpeg|png|bmp|webp|gif)(?:\?[^\s]*)?)(.*)',
    re.IGNORECASE | re.DOTALL
)

# Broader URL pattern for when backend explicitly sets type=image
_ANY_URL_RE = re.compile(r'https?://[^\s]+', re.IGNORECASE)


def is_local_image(text):
    _, ext = os.path.splitext(text.strip())
    return ext.lower() in _IMAGE_EXTS and os.path.exists(text.strip())


def is_image_request(text):
    # A URL is never an image request, only conversational sentences are
    if text.strip().startswith(("http://", "https://")):
        return False
    return any(re.search(p, text, re.IGNORECASE) for p in _IMAGE_REQUEST_PATTERNS)


def _download_image(url):
    """Download image URL to temp file. Returns path or None."""
    try:
        import urllib.request
        # Guess extension from URL
        base_url = url.split('?')[0]
        _, ext = os.path.splitext(base_url)
        suffix = ext.lower() if ext.lower() in _IMAGE_EXTS else '.jpg'

        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/124.0.0.0 Safari/537.36'),
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': url.split('/')[0] + '//' + url.split('/')[2] + '/',
        }
        try:
            import requests as req_lib
            resp = req_lib.get(url, headers=headers, timeout=12, stream=True)
            resp.raise_for_status()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            for chunk in resp.iter_content(65536):
                tmp.write(chunk)
            tmp.close()
            return tmp.name
        except Exception:
            pass
        # Fallback: urllib
        req2 = urllib.request.Request(url, headers=headers)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        with urllib.request.urlopen(req2, timeout=12) as r:
            tmp.write(r.read())
        tmp.close()
        return tmp.name
    except Exception:
        return None


def _analyze(path):
    if not FLORENCE_ENABLED:
        return None
    from input.image_analyzer import analyze_image
    result = analyze_image(path, FLORENCE_MODEL_ID)
    if result and not result.startswith(("(Florence", "(image")):
        return result
    return None


def normalize(message):
    """
    Returns (normalized_text, input_type)
    input_type: text / image_from_user / image_request / emoji
    """
    msg_type = message.get("type", "text")
    content  = message.get("content", "")

    # ── Explicit image type (backend sets type="image") ──────────
    if msg_type == "image":
        url_or_path = (message.get("path")
                       or message.get("url")
                       or content.strip())

        if is_local_image(url_or_path):
            desc = _analyze(url_or_path)
        else:
            tmp = _download_image(url_or_path)
            desc = None
            if tmp:
                try:
                    desc = _analyze(tmp)
                finally:
                    try: os.unlink(tmp)
                    except: pass

        if desc:
            return "[photo content: %s]" % desc, "image_from_user"
        else:
            return "[user sent a photo but it didnt load — show curiosity, ask them to describe it]", "image_from_user"

    # ── Image URL embedded in text ────────────────────────────────
    m = _URL_RE.search(content)
    if m:
        url       = m.group(1)
        extra_txt = m.group(2).strip()

        tmp_path = _download_image(url)
        desc = None
        if tmp_path:
            try:
                desc = _analyze(tmp_path)
            finally:
                try: os.unlink(tmp_path)
                except: pass

        if desc:
            combined = "[photo content: %s]" % desc
            if extra_txt:
                combined += " they said: %s" % extra_txt
            return combined, "image_from_user"
        else:
            if extra_txt:
                return (
                    "[user shared a photo but it didnt load. "
                    "they said it is: %s — show curiosity, ask to describe or resend]" % extra_txt
                ), "image_from_user"
            else:
                return "[user shared a photo but it didnt load — ask them what it is]", "image_from_user"

    # ── User requesting the virtual user to send a photo ─────────
    # Only check this for plain text messages, never when msg_type is "image"
    if msg_type == "text" and is_image_request(content):
        return content, "image_request"

    # ── Emoji ─────────────────────────────────────────────────────
    if msg_type == "emoji":
        emoji_map = {
            "❤️": "sent a heart",
            "😂": "finds it funny",
            "😢": "seems sad",
            "😍": "thinks its hot",
            "👍": "approves",
            "🔥": "thinks its fire",
        }
        label = emoji_map.get(content, "sent an emoji: %s" % content)
        return "[user %s]" % label, "emoji"

    return content, "text"
