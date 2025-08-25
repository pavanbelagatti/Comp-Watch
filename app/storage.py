import os, sqlite3, hashlib, time
from typing import Optional
from .models import Item

DB_PATH = os.getenv("DB_PATH", "watcher.db")

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if "/" in DB_PATH else None
    cx = sqlite3.connect(DB_PATH)
    cx.execute("""CREATE TABLE IF NOT EXISTS seen (
        id TEXT PRIMARY KEY,
        source TEXT,
        url TEXT,
        title TEXT,
        published_at TEXT,
        first_seen_ts REAL
    )""")
    return cx

def reset_db_if_requested():
    if os.getenv("RESET_DB_ON_RUN", "false").lower() == "true":
        try:
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
                print(f"[db] removed {DB_PATH}")
        except Exception as e:
            print(f"[db] reset error: {e}")

def _key_for(it: Item) -> str:
    base = (it.source or "") + "|" + (it.url or "") + "|" + (it.id_hint or "")
    return hashlib.sha256(base.encode("utf-8", errors="ignore")).hexdigest()

def db_is_empty() -> bool:
    cx = _conn()
    try:
        cur = cx.execute("SELECT COUNT(1) FROM seen")
        n = cur.fetchone()[0]
        return n == 0
    finally:
        cx.close()

def record_seen(it: Item):
    cx = _conn()
    try:
        cx.execute(
            "INSERT OR IGNORE INTO seen (id, source, url, title, published_at, first_seen_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (_key_for(it), it.source, it.url, it.title, it.published_at, time.time()),
        )
        cx.commit()
    finally:
        cx.close()

def is_new(it: Item) -> bool:
    """Return True if not seen; also mark as seen."""
    cx = _conn()
    k = _key_for(it)
    try:
        cur = cx.execute("SELECT 1 FROM seen WHERE id=?", (k,))
        row = cur.fetchone()
        if row:
            return False
        cx.execute(
            "INSERT INTO seen (id, source, url, title, published_at, first_seen_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (k, it.source, it.url, it.title, it.published_at, time.time()),
        )
        cx.commit()
        return True
    finally:
        cx.close()
