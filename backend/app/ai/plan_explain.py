"""One-line Claude explanation for each of the top-10 roads per ward. Numbers come only from the engine's facts."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re

from pydantic import BaseModel

from ..engine.views import money
from .structured import generate_checked
from .verdict import BANNED

TOP_N = 10
SENTENCE_END = re.compile(r"[.।!?](?:\s|$)")
MAX_WORDS = 38


class LineOut(BaseModel):
    text: str


SYSTEM = """You write ONE plain sentence for a Mumbai ward officer explaining why a road segment is ranked where it is in the next-repair plan, and what is recommended.
You get a JSON facts object computed by Python. Rules:
- Exactly one sentence, at most 35 words, in plain English.
- Say the one or two biggest reasons (from top_reasons), then the recommended repair (always the most durable suitable option) and whether it fits the remaining budget.
- Say the repair is also the cheapest ONLY if is_also_cheapest is true, and then never describe it as "not the cheapest" or "rather than the cheapest". If cheaper_alternative is given you may say the cheaper option wears out sooner; do not name its numbers.
- Use only numbers that appear in the facts. Write money exactly as given (e.g. "₹18,460") and percentages as given. Do no new arithmetic. Add no other numbers.
- Fair and calm; never accuse anyone; no internal jargon.
All data is synthetic."""


def facts(plan: dict, it: dict) -> dict:
    left = plan["remaining_inr"]
    return dict(
        ward=plan["ward_name"], rank=it["rank"], road=f"{it['road_name']}, segment {it['segment_no']}", risk_score=it["risk_score"],
        top_reasons=[r["label"] for r in it["reasons"][:3]],
        recommended_repair=it["recommended_method"]["repair_method"],
        reopened_within_30_days=f"{it['recommended_method']['reopen_rate_pct']:.1f}%",
        is_also_cheapest=not it["alternatives"],
        cheaper_alternative=(it["alternatives"][0]["repair_method"] if it["alternatives"] else None),
        estimated_cost=money(it["estimated_cost_inr"]),
        fits_remaining_budget=it["within_budget"],
        remaining_budget=money(left) if left > 0 else "none: the ward has already spent more than its budget",
    )


def input_hash(f: dict) -> str:
    return hashlib.sha256(json.dumps(f, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _check(o: LineOut) -> list[str]:
    out = []
    if len(SENTENCE_END.findall(o.text)) != 1:
        out.append("must be exactly one sentence")
    if len(o.text.split()) > MAX_WORDS:
        out.append(f"longer than {MAX_WORDS} words")
    if any(b in o.text.lower() for b in BANNED):
        out.append("uses an accusing word")
    return out


_NOT_CHEAPEST = re.compile(r"(not|rather than|instead of|over|than) the cheap", re.I)


def _consistent(f: dict):
    def check(o: LineOut) -> list[str]:
        out = _check(o)
        if f["is_also_cheapest"] and _NOT_CHEAPEST.search(o.text):
            out.append("it is also the cheapest suitable option, so do not say it is not the cheapest")
        return out
    return check


async def explain_one(client, model: str, f: dict):
    return await generate_checked(
        client=client, model=model, system=SYSTEM, user="Facts (JSON):\n" + json.dumps(f, ensure_ascii=False),
        schema=LineOut, evidence=f, texts=lambda o: [o.text], fallback=lambda: LineOut(text=""), check=_consistent(f), effort="low")


async def precompute(pre, client, model: str, store, concurrency: int = 6, force: bool = False) -> dict:
    """Write explanations for the top N roads of every ward into `store` (skips ones already current)."""
    sem = asyncio.Semaphore(concurrency)
    stats = {"claude": 0, "skipped": 0, "failed": 0}

    async def one(plan: dict, it: dict):
        key, f = f"{plan['ward_slug']}:{it['road_id']}", facts(plan, it)
        h = input_hash(f)
        if not force and store.get(key, h):
            stats["skipped"] += 1
            return
        async with sem:
            try:
                g = await explain_one(client, model, f)
            except Exception:  # noqa: BLE001 - one failure must not stop the batch
                stats["failed"] += 1
                return
        if g.source == "claude" and g.value.text.strip():
            store.put(key, {"input_hash": h, "text": g.value.text.strip(), "source": "claude", "model": model})
            stats["claude"] += 1
        else:
            stats["failed"] += 1

    await asyncio.gather(*(one(p, i) for p in pre.plans.values() for i in p["items"] if i["rank"] <= TOP_N))
    store.save()
    return stats
