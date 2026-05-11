import sqlite3, json, time, os
from .base import PersonaStore, StateStore
from config import DB_PATH


class SQLitePersonaStore(PersonaStore):
    def __init__(self, path=DB_PATH):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS virtual_users "
            "(id TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        self.conn.commit()

    def get(self, user_id):
        row = self.conn.execute(
            "SELECT data FROM virtual_users WHERE id=?", (user_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, user):
        self.conn.execute(
            "INSERT OR REPLACE INTO virtual_users VALUES (?,?)",
            (user["id"], json.dumps(user, ensure_ascii=False))
        )
        self.conn.commit()

    def list_all_ids(self):
        return [r[0] for r in self.conn.execute(
            "SELECT id FROM virtual_users"
        ).fetchall()]


class InMemoryStateStore(StateStore):
    """本地模拟 Redis（重启数据丢失，开发阶段够用）"""
    def __init__(self):
        self._store  = {}   # key -> (value, expire_at or None)
        self._counts = {}   # key -> int

    def get(self, key):
        if key not in self._store:
            return None
        value, exp = self._store[key]
        if exp and time.time() > exp:
            del self._store[key]
            return None
        return value

    def set(self, key, value, ttl_seconds=None):
        exp = time.time() + ttl_seconds if ttl_seconds else None
        self._store[key] = (value, exp)

    def delete(self, key):
        self._store.pop(key, None)
        self._counts.pop(key, None)

    def incr(self, key):
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def get_int(self, key):
        return self._counts.get(key, 0)


class SQLiteStateStore(StateStore):
    """
    Persistent state store using SQLite.
    Replaces InMemoryStateStore for production — survives restarts.
    """
    def __init__(self, path=None):
        from config import DB_PATH
        db_path = path or DB_PATH.replace("personas.db", "state.db")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key       TEXT PRIMARY KEY,
                value     TEXT,
                expire_at REAL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS counters (
                key   TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def get(self, key):
        row = self.conn.execute(
            "SELECT value, expire_at FROM kv_store WHERE key=?", (key,)
        ).fetchone()
        if not row:
            return None
        value, exp = row
        if exp and time.time() > exp:
            self.conn.execute("DELETE FROM kv_store WHERE key=?", (key,))
            self.conn.commit()
            return None
        return value

    def set(self, key, value, ttl_seconds=None):
        exp = time.time() + ttl_seconds if ttl_seconds else None
        self.conn.execute(
            "INSERT OR REPLACE INTO kv_store VALUES (?,?,?)",
            (key, value, exp)
        )
        self.conn.commit()

    def delete(self, key):
        self.conn.execute("DELETE FROM kv_store WHERE key=?", (key,))
        self.conn.execute("DELETE FROM counters WHERE key=?", (key,))
        self.conn.commit()

    def incr(self, key):
        self.conn.execute(
            "INSERT INTO counters(key,value) VALUES(?,1) "
            "ON CONFLICT(key) DO UPDATE SET value=value+1",
            (key,)
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT value FROM counters WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else 1

    def get_int(self, key):
        row = self.conn.execute(
            "SELECT value FROM counters WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else 0
