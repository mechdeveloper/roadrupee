"""python -m app.ai.precompute_social: classify every post in data/social_posts.csv into data_cache/social_posts.json."""
from __future__ import annotations

import asyncio

import pandas as pd

from .. import cache
from . import client as ai_client
from . import social
from .store import social_store


def chunks(xs: list, n: int):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


async def run(pre, client, model: str, store, concurrency: int = 4) -> dict:
    posts = pd.read_csv(pre.data.dir / "social_posts.csv").to_dict("records")
    names = {r.locality for r in pre.data.localities.itertuples()}
    todo = [p for p in posts if not store.get(p["post_id"], social.text_hash(p["text"]))]
    stats = {"posts": len(posts), "classified": 0, "skipped": len(posts) - len(todo), "failed": 0}
    sem = asyncio.Semaphore(concurrency)

    async def one(batch: list[dict]):
        async with sem:
            try:
                out = await social.classify_batch(client, model, batch, sorted(names))
            except Exception:  # noqa: BLE001 - a failed batch is retried on the next run
                stats["failed"] += len(batch)
                return
        by_id = {p["post_id"]: p for p in batch}
        for o in out.posts:
            p = by_id.get(o.post_id)
            if p is None:
                continue
            loc = o.locality if o.locality in names else None  # an unknown place name is never trusted
            store.put(o.post_id, {"input_hash": social.text_hash(p["text"]), "is_road_issue": o.is_road_issue,
                                  "is_recurrence": o.is_recurrence, "language": o.language, "locality": loc,
                                  "issue_type": o.issue_type, "source": "claude", "model": model})
            stats["classified"] += 1

    await asyncio.gather(*(one(b) for b in chunks(todo, social.BATCH)))
    store.save()
    return stats


async def main() -> None:
    if not ai_client.have_key():
        raise SystemExit("ANTHROPIC_API_KEY is not set")
    pre = cache.build()
    store = social_store()
    print(await run(pre, ai_client.get_client(), ai_client.model_live(), store), "->", store.path)


if __name__ == "__main__":
    asyncio.run(main())
