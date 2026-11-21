"""Precompute ai_summary {en, hi, mr} for every ward -> backend/data_cache/ward_summaries.json (committed).

    uv run python -m app.ai.precompute_ward_summaries [--force] [--retry-templates]
"""
from __future__ import annotations

import argparse
import asyncio
import random

import anthropic

from .. import cache
from . import client as ai_client
from .store import ward_summary_store
from .structured import Generated
from .ward_summary import facts, input_hash, make_summary, template_summary, to_entry


async def main_async(args) -> None:
    pre = cache.build()
    store = ward_summary_store()
    sem = asyncio.Semaphore(6)
    client, model = ai_client.get_client(), ai_client.model_live()
    todo = []
    for w in pre.wards:
        f = facts(pre, w, pre.flags)
        hit = store.get(w["slug"], input_hash(f))
        if hit and not args.force and not (args.retry_templates and hit["source"] == "template"):
            continue
        todo.append((w, f))
    print(f"{len(pre.wards)} wards, {len(todo)} to compute, model {model}")

    async def run(w, f):
        async with sem:
            for i in range(3):
                try:
                    g = await make_summary(client, model, f)
                    break
                except anthropic.APIError as e:
                    if i == 2:
                        print(f"  {w['slug']}: API error ({type(e).__name__}); template")
                        g = Generated(template_summary(f), "template", None, 0, [])
                    else:
                        await asyncio.sleep(2 ** i + random.random())
        store.put(w["slug"], to_entry(f, g))
        print(f"  {w['slug']}: {g.source}" + (f" (retry {g.guardrail_retries})" if g.guardrail_retries else ""))

    await asyncio.gather(*(run(w, f) for w, f in todo))
    store.save()
    srcs = [e["source"] for e in store.items.values()]
    print(f"\n{len(srcs)} summaries: {srcs.count('claude')} claude, {srcs.count('template')} template")
    sample = store.items.get("g-s") or next(iter(store.items.values()))
    for k in ("en", "hi", "mr"):
        print(f"[{k}] {sample[k]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retry-templates", action="store_true")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
