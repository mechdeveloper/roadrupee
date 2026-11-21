"""Numbers guardrail: every rupee amount, percentage and multiplier Claude writes must appear in the evidence.

Reusable for any Claude text (flag verdicts, ward summaries). Claude never invents numbers.
"""
from __future__ import annotations

import re
from typing import Any

NUM = r"\d[\d,]*(?:\.\d+)?"
RUPEE_RE = re.compile(rf"₹\s*({NUM})\s*(Cr|crore|L|lakh|lakhs|k)?\b", re.I)
PCT_RE = re.compile(rf"({NUM})\s*%")
MULT_RE = re.compile(rf"({NUM})\s*[×x](?![a-z])")
ANY_NUM_RE = re.compile(NUM)
UNIT = {"cr": 1e7, "crore": 1e7, "l": 1e5, "lakh": 1e5, "lakhs": 1e5, "k": 1e3}


def _parse(s: str) -> float:
    return float(s.replace(",", ""))


def _decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def evidence_numbers(obj: Any) -> list[float]:
    """Every numeric leaf plus every number written inside string leaves (e.g. the claim text)."""
    out: list[float] = []

    def walk(o: Any) -> None:
        if isinstance(o, bool):
            return
        if isinstance(o, (int, float)):
            out.append(float(o))
        elif isinstance(o, str):
            out.extend(_parse(m) for m in ANY_NUM_RE.findall(o) if m.replace(",", "").replace(".", "").isdigit())
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                walk(v)

    walk(obj)
    return out


def _supported(value: float, written: str, scale: float, nums: list[float]) -> bool:
    tol = 0.5 * 10 ** -_decimals(written) * scale + 1e-6
    return any(abs(n - value * scale) <= tol for n in nums)


def unverified_numbers(texts: list[str], evidence: Any) -> list[str]:
    """Return the ₹ amounts / percentages / multipliers in `texts` that are not in `evidence`."""
    nums = evidence_numbers(evidence)
    bad: list[str] = []
    for t in texts:
        for m in RUPEE_RE.finditer(t):
            unit = (m.group(2) or "").lower()
            if not _supported(_parse(m.group(1)), m.group(1), UNIT.get(unit, 1.0), nums):
                bad.append(m.group(0).strip())
        for m in PCT_RE.finditer(t):
            if not _supported(_parse(m.group(1)), m.group(1), 1.0, nums):
                bad.append(m.group(0).strip())
        for m in MULT_RE.finditer(t):
            if not _supported(_parse(m.group(1)), m.group(1), 1.0, nums):
                bad.append(m.group(0).strip())
    return bad
