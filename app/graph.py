from __future__ import annotations
import os, yaml
from typing import Dict, List
from datetime import datetime, timezone, timedelta

from .models import Source, Item
from .fetchers import fetch_source
from .storage import is_new, db_is_empty, record_seen
from .summarize import summarize_items

class State(dict):
    sources: List[Source]
    fetched: List[Item]
    new_items: List[Item]

def load_sources(_: State) -> State:
    with open("sources.yaml", "r") as f:
        data = yaml.safe_load(f)
    sources = [Source(**s) for s in data["sources"]]
    print(f"[sources] loaded: {len(sources)}")
    return State(sources=sources, fetched=[], new_items=[])

def fetch_all(state: State) -> State:
    items: List[Item] = []
    for src in state["sources"]:
        try:
            got = fetch_source(src)
            items.extend(got)
        except Exception as e:
            print(f"[WARN] {src.name}: {e}")
    state["fetched"] = items
    print(f"[fetch] total fetched: {len(items)}")
    return state

def detect_new(state: State) -> State:
    # Optional recency filter
    since_hours = int(os.getenv("SINCE_HOURS", "0"))
    cutoff = None
    if since_hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        print(f"[new] time filter: last {since_hours}h (cutoff {cutoff.isoformat()})")

    # Force include latest N per source (manual runs)
    force_seed = int(os.getenv("FORCE_SEED_PER_SOURCE", "0"))
    # Seed only when DB empty (first-time run)
    seed_n = int(os.getenv("SEED_LATEST_PER_SOURCE", "0"))

    def _is_recent(it: Item) -> bool:
        if not cutoff:
            return True
        try:
            return it.published_at and datetime.fromisoformat(it.published_at) >= cutoff
        except Exception:
            return True  # keep items without dates

    items = state["fetched"]
    new_items: List[Item] = []

    if force_seed > 0:
        # Always take the latest N per source, and mark them seen
        by_src: Dict[str, List[Item]] = {}
        for it in items:
            by_src.setdefault(it.source, []).append(it)
        for _, arr in by_src.items():
            kept = [it for it in arr][:force_seed]  # feeds are typically newest-first
            for it in kept:
                record_seen(it)  # so scheduled runs won’t resend
                new_items.append(it)
        print(f"[new] force-seeded: {len(new_items)}")
    elif seed_n > 0 and db_is_empty():
        print(f"[new] seeding first {seed_n} per source (DB is empty)")
        by_src: Dict[str, List[Item]] = {}
        for it in items:
            if _is_recent(it):
                by_src.setdefault(it.source, []).append(it)
        for _, arr in by_src.items():
            for it in arr[:seed_n]:
                if is_new(it):
                    new_items.append(it)
    else:
        for it in items:
            if _is_recent(it) and is_new(it):
                new_items.append(it)

    state["new_items"] = new_items
    print(f"[new] new items: {len(new_items)}")
    return state

def build_email(state: State) -> State:
    items = state["new_items"]
    if not items:
        sh = os.getenv("SINCE_HOURS", "0")
        msg = f"<p>No new updates in the last {sh} hours.</p>" if sh != "0" else "<p>No new updates today.</p>"
        return State(**state, email_html=msg, subject="Competitor Watcher: No new updates")

    groups: Dict[str, List[Item]] = {}
    for it in items:
        key = f"{it.source} · {it.category}"
        groups.setdefault(key, []).append(it)

    parts = []
    for key, group in sorted(groups.items()):
        bullets = summarize_items(group)  # clickable titles if no OpenAI key
        lis = "\n".join(f"<li>{b}</li>" for b in bullets)
        parts.append(f"<h3>{key} ({len(group)})</h3><ul>{lis}</ul>")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"Competitor Watcher · {today} · {len(items)} update(s)"
    html = (
        "<div style='font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;'>"
        f"<h2>{title}</h2>{''.join(parts)}<hr/>"
        "<p style='color:#666'>Edit <code>sources.yaml</code> to add/remove sites.</p></div>"
    )
    return State(**state, email_html=html, subject=title)
