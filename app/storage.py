import sqlite3, os
from contextlib import closing
from .models import Item
from .utils import make_id

DB_PATH = os.getenv("DB_PATH", "./watcher.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_items (
  id TEXT PRIMARY KEY,
  source TEXT,
  title TEXT,
  url TEXT,
  category TEXT,
  first_seen_ts DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def _conn():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute(SCHEMA)
    return con

def db_is_empty() -> bool:
    with closing(_conn()) as con:
        cur = con.execute("SELECT COUNT(*) FROM seen_items")
        return (cur.fetchone() or [0])[0] == 0

def is_new(item: Item) -> bool:
    """True if unseen; inserts when not DRY_RUN."""
    dry_run = (os.getenv("DRY_RUN", "false").lower() == "true")
    with closing(_conn()) as con:
        iid = make_id(item.source, item.id_hint or item.url or item.title)
        cur = con.execute("SELECT 1 FROM seen_items WHERE id=?", (iid,))
        if cur.fetchone():
            return False
        if not dry_run:
            con.execute(
                "INSERT INTO seen_items (id, source, title, url, category) VALUES (?, ?, ?, ?, ?)",
                (iid, item.source, item.title, item.url, item.category),
            )
            con.commit()
        return True