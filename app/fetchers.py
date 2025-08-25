from __future__ import annotations

import os
from typing import List
import feedparser, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_fixed
from datetime import datetime, timezone

from .models import Source, Item

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "12"))
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "5"))
MAX_ITEMS_PER_SOURCE = int(os.getenv("MAX_ITEMS_PER_SOURCE", "50"))
UA = os.getenv("HTTP_UA", ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0 Safari/537.36"))

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/rss+xml,application/xml,text/html;q=0.9,*/*;q=0.8",
}

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
def _get(url: str) -> requests.Response:
    r = requests.get(url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, HTTP_TIMEOUT))
    r.raise_for_status()
    return r

def _to_iso(dt_struct) -> str | None:
    if not dt_struct:
        return None
    try:
        return datetime(*dt_struct[:6], tzinfo=timezone.utc).isoformat()
    except Exception:
        return None

def fetch_rss(src: Source) -> List[Item]:
    url = str(src.url)
    print(f"[rss]  GET {url}")
    r = _get(url)
    parsed = feedparser.parse(r.text)
    items: List[Item] = []
    for e in parsed.entries[:MAX_ITEMS_PER_SOURCE]:
        title = (getattr(e, "title", "") or "").strip() or "(no title)"
        link = getattr(e, "link", None) or getattr(e, "id", None) or url
        pid  = getattr(e, "id", None) or link or title
        pub_iso = _to_iso(getattr(e, "published_parsed", None)) \
                  or _to_iso(getattr(e, "updated_parsed", None))
        items.append(Item(
            source=src.name,
            category=src.category,
            title=title,
            url=str(link),
            published_at=pub_iso,
            id_hint=str(pid),
        ))
    print(f"[rss]  {src.name}: {len(items)}")
    return items

def fetch_html(src: Source) -> List[Item]:
    assert src.selectors, f"HTML selectors required for {src.name}"
    base = str(src.url)
    print(f"[html] GET {base}")
    html = _get(base).text
    soup = BeautifulSoup(html, "html.parser")
    sel = src.selectors
    seen: List[Item] = []
    for node in soup.select(sel.item)[:MAX_ITEMS_PER_SOURCE]:
        a = node if node.name == "a" else node.select_one(sel.title)
        if not a:
            continue
        href = a.get(sel.link_attr) or a.get("href")
        if not href:
            continue
        full = urljoin(base, href)
        title = (a.get_text() or "").strip() or full
        seen.append(Item(
            source=src.name,
            category=src.category,
            title=title,
            url=str(full),
            published_at=None,
            id_hint=str(full),
        ))
    print(f"[html] {src.name}: {len(seen)}")
    return seen

def fetch_source(src: Source) -> List[Item]:
    return fetch_rss(src) if src.kind == "rss" else fetch_html(src)
