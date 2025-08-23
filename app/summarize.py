import os
from typing import List
from openai import OpenAI
from .models import Item

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

client = None
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI()

def summarize_items(items: List[Item]) -> List[str]:
    # Fallback: no summaries -> clickable titles
    if not client:
        return [f'<a href="{it.url}">{it.title}</a>' for it in items]

    prompt = (
        "Summarize each line to <=20 words, keep one bullet per line. "
        "Preserve links in [title](url) Markdown.\n\n"
        + "\n".join(f"- {it.title} — {it.url}" for it in items)
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    text = resp.choices[0].message.content.strip()
    return [ln.strip("- ").strip() for ln in text.splitlines() if ln.strip()]