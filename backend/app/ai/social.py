"""Claude classifies social posts: is it a road/drain problem, is it a RECURRENCE, language, locality, issue type.

The matching to work orders is deterministic (engine/silent.py); Claude only reads the messy text.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel

BATCH = 25


class PostOut(BaseModel):
    post_id: str
    is_road_issue: bool
    is_recurrence: bool
    language: Literal["en", "hi", "mr", "hi-en"]
    locality: str | None
    issue_type: Literal[
        "Pothole", "Waterlogging", "Open or broken manhole", "Choked drain / nullah overflow",
        "Road cave-in", "Broken paver blocks", "other",
    ]


class BatchOut(BaseModel):
    posts: list[PostOut]


SYSTEM = """You read short social-media posts (X, WhatsApp groups, Instagram comments) from Mumbai citizens, written in English, Hindi, Marathi or Hinglish (Hindi in Roman letters), with emoji and hashtags.
For EACH post return:
- is_road_issue: true only if the post reports a road, pothole, manhole, drain or waterlogging problem at a place. False for thank-yous, greetings, jokes, general weather chat, school-closure questions and unrelated posts.
- is_recurrence: true only if the post says the SAME problem has come back or keeps happening: "again", "phir se", "parat", "punha", "fir se", "same story", "har saal", "every year", "is BACK", "fixed last week and it's back", "yet again". A fresh report with no sign it happened before is false. A thank-you for a fix is false. A forwarded message ("Fwd as received", "unverified") is false.
- language: "mr" Marathi, "hi" Hindi in Devanagari, "hi-en" Hinglish, "en" English.
- locality: the place named in the post, normalised to EXACTLY one name from the gazetteer list you are given (match Devanagari and spelling variants to the English name). If the post names a place that is not in the list, or none, return null. Never invent a name.
- issue_type: one of the six categories, or "other". Water standing on the road is "Waterlogging"; missing or broken manhole cover is "Open or broken manhole"; blocked drain or overflowing nullah is "Choked drain / nullah overflow"; sunk or collapsed road is "Road cave-in"; loose or broken footpath tiles are "Broken paver blocks"; holes in the road surface are "Pothole".
Return one entry per post, using the post_id you were given. All data is synthetic."""


async def classify_batch(client, model: str, posts: list[dict], localities: list[str]) -> BatchOut:
    body = json.dumps([{"post_id": p["post_id"], "text": p["text"]} for p in posts], ensure_ascii=False)
    r = await client.messages.parse(
        model=model, max_tokens=8000, system=SYSTEM,
        messages=[{"role": "user", "content": f"Gazetteer: {json.dumps(localities, ensure_ascii=False)}\n\nPosts:\n{body}"}],
        output_format=BatchOut, output_config={"effort": "low"},
    )
    if r.parsed_output is None:
        raise ValueError(f"unusable response (stop_reason={r.stop_reason})")
    return r.parsed_output


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
