from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import BaseModel, HttpUrl

# Categories supported
Category = Literal["blog", "release", "event", "webinar", "news"]


class HTMLSelectors(BaseModel):
    item: str
    title: str
    link_attr: str = "href"
    date: Optional[str] = None


class Source(BaseModel):
    name: str
    kind: Literal["rss", "html"]
    category: Category
    url: HttpUrl
    selectors: Optional[HTMLSelectors] = None


class Item(BaseModel):
    source: str
    category: Category
    title: str
    url: str
    published_at: Optional[str] = None
    id_hint: Optional[str] = None  # used for hashing/dedup


class RunResult(BaseModel):
    new_items: List[Item]
    total_seen: int