"""
API-backed PersonaStore
Fetches user info + traits from remote API, caches locally in SQLite.
Replaces hardcoded archetype data.
"""
import json
import time
import sqlite3
import os
import requests

from storage.base import PersonaStore

GET_USERS_URL  = "https://api.covlly.com/api/getUsers?is_ai=1"
GET_TRAITS_URL = "https://api.covlly.com/api/getUserTraits"
HEADERS        = {"Content-Type": "application/json", "Accept": "application/json"}
CACHE_TTL      = 3600   # re-fetch from API after 1 hour


class APIPersonaStore(PersonaStore):
    """
    get(user_id)     → check SQLite cache → miss: fetch API → combine → cache → return
    list_all_ids()   → fetch all AI users from API, cache ids
    """

    def __init__(self, db_path="./data/personas.db"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS persona_cache (
                user_id TEXT PRIMARY KEY,
                data    TEXT NOT NULL,
                fetched_at REAL NOT NULL
            )
        """)
        self.conn.commit()

    # ── Public interface ──────────────────────────────────
    def get(self, user_id):
        user_id = str(user_id)
        cached = self._get_cache(user_id)
        if cached:
            return cached
        persona = self._fetch_and_build(user_id)
        if persona:
            self._set_cache(user_id, persona)
        return persona

    def save(self, user):
        """Allow manual override / local-only users."""
        self._set_cache(str(user["id"]), user)

    def list_all_ids(self, limit=None):
        """
        limit=None  -> return all users
        limit=5     -> return 5 random users (for testing)
        """
        import random
        try:
            resp  = requests.get(GET_USERS_URL, headers=HEADERS, timeout=15)
            body  = resp.json()
            users = body.get("data", body) if isinstance(body, dict) else body
            ids   = [str(u["id"]) for u in users if isinstance(u, dict)]
            if limit and len(ids) > limit:
                ids = random.sample(ids, limit)
            return ids
        except Exception as e:
            print("  [APIStore] list_all_ids error:", e)
            rows = self.conn.execute("SELECT user_id FROM persona_cache").fetchall()
            return [r[0] for r in rows]

    # ── Fetch + merge ─────────────────────────────────────
    def _fetch_and_build(self, user_id):
        user_data  = self._fetch_user(user_id)
        trait_data = self._fetch_traits(user_id)
        if not user_data:
            return None
        return self._merge(user_data, trait_data)

    def _fetch_user(self, user_id):
        """Fetch single user record from getUsers list."""
        try:
            resp  = requests.get(GET_USERS_URL, headers=HEADERS, timeout=15)
            body  = resp.json()
            users = body.get("data", body) if isinstance(body, dict) else body
            for u in users:
                if str(u.get("id")) == str(user_id):
                    return u
        except Exception as e:
            print("  [APIStore] fetch_user error:", e)
        return None

    def _fetch_traits(self, user_id):
        """Fetch trait record from getUserTraits."""
        try:
            resp = requests.get(GET_TRAITS_URL,
                                params={"user_id": user_id},
                                headers=HEADERS, timeout=10)
            body = resp.json()
            if not body.get("status"):
                return {}
            data = body.get("data")
            if not data:
                return {}
            # data can be a list [{...}] or a dict {...}
            if isinstance(data, list):
                return data[0] if data else {}
            return data
        except Exception as e:
            print("  [APIStore] fetch_traits error:", e)
        return {}

    def _merge(self, user, traits):
        """Combine user fields + trait fields into persona dict."""
        # Parse JSON string arrays if needed
        interests = traits.get("interests", "[]")
        if isinstance(interests, str):
            try: interests = json.loads(interests)
            except: interests = []

        avoid = traits.get("avoid_topics", "[]")
        if isinstance(avoid, str):
            try: avoid = json.loads(avoid)
            except: avoid = []

        age = 30
        try: age = int(user.get("age", 30))
        except: pass

        return {
            # Identity
            "id":       str(user.get("id")),
            "name":     user.get("nickname") or user.get("name") or "User",
            "age":      age,
            "gender":   str(user.get("gender", "1")),
            "address":  user.get("address") or "United States",

            # Big Four (with fallbacks)
            "extraversion":  float(traits.get("extraversion",  0.55)),
            "neuroticism":   float(traits.get("neuroticism",   0.35)),
            "openness":      float(traits.get("openness",      0.55)),
            "agreeableness": float(traits.get("agreeableness", 0.60)),

            # Emotional
            "attachment_style":  traits.get("attachment_style",  "secure"),
            "expression_level":  traits.get("expression_level",  "medium"),
            "baseline_pleasure": float(traits.get("baseline_pleasure", 0.50)),
            "volatility":        float(traits.get("volatility",  0.30)),
            "recovery_rate":     float(traits.get("recovery_rate", 0.08)),

            # Style
            "humor_type":      traits.get("humor_type",      "gentle"),
            "language_style":  traits.get("language_style",  "casual"),
            "emoji_frequency": traits.get("emoji_frequency", "medium"),
            "reply_length":    traits.get("reply_length",    "medium"),

            # Character
            "boundary_level":  float(traits.get("boundary_level", 0.50)),
            "topic_expansion": traits.get("topic_expansion", "medium"),
            "life_attitude":   traits.get("life_attitude",   "optimistic"),

            # Preferences
            "interests":    interests,
            "avoid_topics": avoid,

            # System
            "archetype":    traits.get("archetype_id", 5),
            "timezone":     traits.get("timezone") or user.get("timezone") or "America/New_York",
        }

    # ── SQLite cache helpers ──────────────────────────────
    def _get_cache(self, user_id):
        row = self.conn.execute(
            "SELECT data, fetched_at FROM persona_cache WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        if time.time() - row[1] > CACHE_TTL:
            return None   # expired, re-fetch
        return json.loads(row[0])

    def _set_cache(self, user_id, data):
        self.conn.execute(
            "INSERT OR REPLACE INTO persona_cache VALUES (?,?,?)",
            (user_id, json.dumps(data, ensure_ascii=False), time.time())
        )
        self.conn.commit()
