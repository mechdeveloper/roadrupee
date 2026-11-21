"""Precompute everything once at startup; routes only read from here."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .engine import evidence
from .engine import flags as F
from .engine import metrics
from .engine.expected import add_expected
from .loader import Data, load


@dataclass
class Precomputed:
    data: Data
    wo: pd.DataFrame
    flags: list[F.Flag]
    summary: dict
    wards: list[dict]
    contractors: list[dict]
    evidence_index: evidence.EvidenceIndex | None = None


def build() -> Precomputed:
    data = load()
    wo = F.add_expected_cost(data, data.wo)
    wo = add_expected(data, wo)
    flags = F.run_all(data, wo)
    contractors = metrics.contractors(data, wo)
    pre = Precomputed(
        data=data, wo=wo, flags=flags,
        summary=metrics.summary(data, wo, flags),
        wards=metrics.wards(data, wo, flags),
        contractors=contractors,
        evidence_index=evidence.build_index(data, wo, contractors),
    )
    _dump(pre)
    return pre


def _dump(pre: Precomputed) -> None:
    """Best-effort JSON snapshot for debugging / the team (not read back)."""
    try:
        d = Path(os.environ.get("CACHE_DIR", Path(__file__).resolve().parents[1] / ".cache"))
        d.mkdir(parents=True, exist_ok=True)
        (d / "summary.json").write_text(json.dumps(pre.summary, indent=2))
        (d / "wards.json").write_text(json.dumps(pre.wards, indent=2))
        (d / "flags.json").write_text(json.dumps([f.to_dict() for f in pre.flags]))
        (d / "contractors.json").write_text(json.dumps(pre.contractors, indent=2))
    except OSError:
        pass
