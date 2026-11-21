"""python -m app.ai.precompute_plan [--force]: write Claude one-liners for the top 10 roads per ward to data_cache/."""
from __future__ import annotations

import asyncio
import sys

from .. import cache
from . import client as ai_client
from . import plan_explain
from .store import plan_store


async def main(force: bool) -> None:
    if not ai_client.have_key():
        raise SystemExit("ANTHROPIC_API_KEY is not set")
    pre = cache.build()
    store = plan_store()
    stats = await plan_explain.precompute(pre, ai_client.get_client(), ai_client.model_live(), store, force=force)
    print(stats, "->", store.path)


if __name__ == "__main__":
    asyncio.run(main("--force" in sys.argv))
