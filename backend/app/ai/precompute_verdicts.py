"""Precompute Claude verdicts for flags and cache them in backend/data_cache/verdicts.json (committed).

    uv run python -m app.ai.precompute_verdicts [--tier audit] [--limit N] [--force] [--retry-templates]
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import random

import anthropic

from .. import cache
from ..engine import evidence
from . import client as ai_client
from .store import verdict_store
from .structured import Generated
from .verdict import make_verdict, template_verdict, to_entry

CONCURRENCY = 8
ATTEMPTS = 3


async def one(sem, ev, client, model) -> Generated:
    async with sem:
        for i in range(ATTEMPTS):
            try:
                return await make_verdict(client, model, ev)
            except anthropic.APIError as e:
                if i == ATTEMPTS - 1:
                    print(f"  {ev['flag_id']}: API error after {ATTEMPTS} tries ({type(e).__name__}); using template")
                    return Generated(template_verdict(ev), "template", None, 0, [str(e)[:120]])
                await asyncio.sleep(2 ** i + random.random())
    raise AssertionError


def report(store, flags) -> None:
    by = collections.defaultdict(collections.Counter)
    samples: dict[str, tuple[str, dict]] = {}
    for f in flags:
        e = store.items.get(f.flag_id)
        if not e:
            continue
        key = "template" if e["source"] == "template" else e["verdict"]
        by[f.rule][key] += 1
        if e["source"] == "claude":
            samples.setdefault(e["verdict"], (f.flag_id + " " + f.rule, e))
    cols = ["worth_checking", "likely_justified", "needs_more_info", "template"]
    print(f"\n{'rule':<16}" + "".join(f"{c:>18}" for c in cols))
    for rule, c in sorted(by.items()):
        print(f"{rule:<16}" + "".join(f"{c[k]:>18}" for k in cols))
    for v in ("worth_checking", "likely_justified", "needs_more_info"):
        if v in samples:
            who, e = samples[v]
            print(f"\n--- sample: {v} ({who}) ---\n{e['headline']}\n{e['reasoning']}\n"
                  f"considered: {'; '.join(e['context_considered'])}\nrefs: {', '.join(e['evidence_refs'])}")


async def main_async(args) -> None:
    pre = cache.build()
    store = pre.verdicts or verdict_store()
    flags = [f for f in pre.flags if args.tier == "all" or f.tier == args.tier][: args.limit or None]
    todo = []
    for f in flags:
        ev = evidence.build(pre.evidence_index, f)
        h = evidence.evidence_hash(ev)
        hit = store.get(f.flag_id, h)
        if hit and not args.force and not (args.retry_templates and hit["source"] == "template"):
            continue
        todo.append((f, ev))
    print(f"{len(flags)} flags in scope, {len(todo)} to compute, model {ai_client.model_live()}")
    sem, client, model = asyncio.Semaphore(CONCURRENCY), ai_client.get_client(), ai_client.model_live()
    done = 0

    async def run(f, ev):
        nonlocal done
        g = await one(sem, ev, client, model)
        store.put(f.flag_id, to_entry(ev, g))
        done += 1
        if done % 20 == 0:
            store.save()
            print(f"  {done}/{len(todo)}")

    await asyncio.gather(*(run(f, ev) for f, ev in todo))
    store.save()
    report(store, flags)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="audit", choices=["audit", "review", "all"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retry-templates", action="store_true")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
