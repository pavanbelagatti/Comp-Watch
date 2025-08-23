import hashlib
from datetime import datetime
import os
from zoneinfo import ZoneInfo

def make_id(*parts) -> str:
    """Create a stable hash ID from arbitrary parts (handles non-strings)."""
    cleaned = []
    for p in parts:
        if p is None:
            continue
        s = str(p).strip()
        if s:
            cleaned.append(s)
    norm = "\u0001".join(cleaned)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

def localize(ts: datetime) -> str:
    """Convert a UTC datetime to the timezone in .env (default Asia/Kolkata)."""
    tz = os.getenv("TZ", "Asia/Kolkata")
    return ts.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")