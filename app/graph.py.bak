from __future__ import annotations
import os
from langgraph.graph import StateGraph, START, END
from typing import Dict, List
import yaml
from datetime import datetime, timezone
from .models import Source, Item
from .fetchers import fetch_source
from .storage import is_new, db_is_empty
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
    seed_n = int(os.getenv("SEED_LATEST_PER_SOURCE", "0"))
    new_items: List[Item] = []

    if seed_n > 0 and db_is_empty():
        print(f"[new] seeding first {seed_n} per source (DB is empty)")
        by_src: Dict[str, List[Item]] = {}
        for it in state["fetched"]:
            by_src.setdefault(it.source, []).append(it)
        for src, arr in by_src.items():
            for it in arr[:seed_n]:
                if is_new(it):
                    new_items.append(it)
    else:
        for it in state["fetched"]:
            if is_new(it):
                new_items.append(it)

    state["new_items"] = new_items
    print(f"[new] new items: {len(new_items)}")
    return state

def build_email(state: State) -> State:
    items = state["new_items"]
    if not items:
        state["email_html"] = "<p>No new updates today.</p>"
        state["subject"] = "Competitor Watcher: No new updates"
        return state

    groups: Dict[str, List[Item]] = {}
    for it in items:
        key = f"{it.source} · {it.category}"
        groups.setdefault(key, []).append(it)

    body_parts = []
    for key, group in sorted(groups.items()):
        bullets = summarize_items(group)
        lis = "\n".join(f"<li>{b}</li>" for b in bullets)
        body_parts.append(f"<h3>{key}</h3><ul>{lis}</ul>")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"Competitor Watcher · {now} · {len(items)} update(s)"
    html = f"""
    <div style='font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;'>
      <h2>{title}</h2>
      {''.join(body_parts)}
      <hr/>
      <p style='color:#666'>Edit sources.yaml to add/remove sites.</p>
    </div>
    """
    state["email_html"] = html
    state["subject"] = title
    return state