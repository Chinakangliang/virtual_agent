# -*- coding: utf-8 -*-
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── AI API ────────────────────────────────────────────────────────
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY_HERE")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL    = "deepseek-chat"

# ── Your Backend API ──────────────────────────────────────────────
# Replace with your actual API base URL
API_BASE_URL   = os.getenv("API_BASE_URL", "https://your-api-domain.com/api")
GET_USERS_URL  = API_BASE_URL + "/getUsers?is_ai=1"
GET_TRAITS_URL = API_BASE_URL + "/getUserTraits"
SET_TRAITS_URL = API_BASE_URL + "/setUserTraits"

# ── mem0 local vector store ───────────────────────────────────────
MEM0_ENABLED = False  # Set True in production (requires HuggingFace access)
MEM0_CONFIG  = {
    "vector_store": {
        "provider": "chroma",
        "config":   {"path": "./data/chroma_db"}
    },
    "embedder": {
        "provider": "huggingface",
        "config":   {"model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
    },
    "llm": {
        "provider": "openai",
        "config": {
            "api_key":          os.getenv("DEEPSEEK_API_KEY", ""),
            "openai_base_url":  "https://api.deepseek.com",
            "model":            "deepseek-chat",
            "max_tokens":       500,
        }
    }
}

# ── Paths ─────────────────────────────────────────────────────────
DATA_DIR   = "./data"
IMAGES_DIR = "./data/images"
DB_PATH    = "./data/personas.db"

# ── HuggingFace cache (set writable path on server) ──────────────
HF_CACHE_DIR = os.getenv("HF_CACHE_DIR", "./data/hf_cache")
os.environ.setdefault("TRANSFORMERS_CACHE", HF_CACHE_DIR)
os.environ.setdefault("HF_HOME",            HF_CACHE_DIR)
os.environ.setdefault("HF_ENDPOINT",        "https://hf-mirror.com")

# ── Behavior ──────────────────────────────────────────────────────
MAX_PROACTIVE_GREETINGS = 3
SHORT_SESSION_THRESHOLD = 120   # seconds before user is considered "valuable"
TIMEOUT_MINUTES         = 8
UNANSWERED_THRESHOLD    = 2
HISTORY_TURNS           = 12
USER_FACTS_N            = 6

# ── Image recognition ─────────────────────────────────────────────
FLORENCE_ENABLED  = True   # Set False to skip (saves memory, skips 800MB download)
FLORENCE_MODEL_ID = "microsoft/Florence-2-base"

# ── Test mode (local debug only) ─────────────────────────────────
TEST_USER_IDS = []  # e.g. ["2", "31", "63"] — empty = fetch from API
