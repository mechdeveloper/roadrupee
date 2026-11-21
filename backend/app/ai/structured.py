"""generate_checked: structured Claude output + guardrail + one retry + deterministic fallback."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel

from .guardrail import unverified_numbers

log = logging.getLogger("roadrupee.ai")
T = TypeVar("T", bound=BaseModel)


@dataclass
class Generated(Generic[T]):
    value: T
    source: str  # "claude" | "template"
    model: str | None
    guardrail_retries: int
    problems: list[str]


async def _call(client, model: str, system: str, user: str, schema: type[T], effort: str):
    r = await client.messages.parse(
        model=model, max_tokens=8000, system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema, output_config={"effort": effort},
    )
    if r.stop_reason in ("refusal", "max_tokens") or r.parsed_output is None:
        raise ValueError(f"unusable response (stop_reason={r.stop_reason})")
    return r.parsed_output


async def generate_checked(
    *, client, model: str, system: str, user: str, schema: type[T], evidence: Any,
    texts: Callable[[T], list[str]], fallback: Callable[[], T],
    check: Callable[[T], list[str]] | None = None, effort: str = "medium",
) -> Generated[T]:
    """Call Claude; reject output with numbers not in `evidence` (or failing `check`); retry once; else template.

    API/transport errors propagate (callers decide); refusals and truncation count as a failed attempt.
    """
    problems: list[str] = []
    prompt = user
    for attempt in range(2):
        try:
            out = await _call(client, model, system, prompt, schema, effort)
        except ValueError as e:
            problems = [str(e)]
        else:
            bad = unverified_numbers(texts(out), evidence)
            problems = [f"number not in evidence: {b}" for b in bad] + (check(out) if check else [])
            if not problems:
                return Generated(out, "claude", model, attempt, [])
        log.warning("guardrail attempt %d failed: %s", attempt + 1, problems)
        prompt = (user + "\n\nYour previous answer was rejected: " + "; ".join(problems)
                  + ". Rewrite it using only numbers that appear in the evidence above (or none), "
                    "and follow every rule in the system prompt.")
    return Generated(fallback(), "template", None, 1, problems)
