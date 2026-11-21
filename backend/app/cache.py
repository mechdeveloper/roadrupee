"""Precompute everything once at startup; routes only read from here."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .ai import ward_summary
from .ai.store import JsonStore, plan_store, verdict_store, ward_summary_store
from .ai.verdict import to_review
from .engine import evidence, planner
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
    verdicts: JsonStore | None = None
    ward_summaries: JsonStore | None = None
    plans: dict | None = None  # ward slug -> PlanResponse dict (engine/planner.py)


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
    pre.verdicts = verdict_store()
    attach_verdicts(pre)
    pre.ward_summaries = ward_summary_store()
    attach_ward_summaries(pre)
    pre.plans = planner.build_all(pre)
    attach_plan_explanations(pre)
    _dump(pre)
    return pre


def attach_verdicts(pre: Precomputed) -> int:
    """Attach stored Claude verdicts whose evidence hash still matches. Rule fields are never touched."""
    n = 0
    for f in pre.flags:
        e = pre.verdicts.items.get(f.flag_id)
        if e and e["input_hash"] == evidence.evidence_hash(evidence.build(pre.evidence_index, f)):
            f.review = to_review(e)
            n += 1
    return n

def attach_plan_explanations(pre: Precomputed) -> int:
    """Attach Claude's stored one-liners (top 10 per ward) when the facts they were written from are unchanged."""
    from .ai import plan_explain

    store, n = plan_store(), 0
    for plan in pre.plans.values():
        for it in plan["items"]:
            if it["rank"] > plan_explain.TOP_N:
                continue
            e = store.get(f"{plan['ward_slug']}:{it['road_id']}", plan_explain.input_hash(plan_explain.facts(plan, it)))
            if e:
                it["explanation"] = e["text"]
                n += 1
    return n


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


def attach_ward_summaries(pre: Precomputed) -> int:
    """Expose Claude's ward summary as ward.ai_summary {en, hi, mr}. Template fallbacks are not shown
    (they are English-only), so the UI card stays hidden for those wards."""
    n = 0
    for w in pre.wards:
        e = pre.ward_summaries.items.get(w["slug"])
        if e and e["source"] == "claude" and e["input_hash"] == ward_summary.input_hash(ward_summary.facts(pre, w, pre.flags)):
            w["ai_summary"] = {k: e[k] for k in ("en", "hi", "mr")}
            n += 1
    return n
