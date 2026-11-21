"""Aggregates behind the home dashboard and the /audit list. Additive; kept out of main.py on purpose."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from ..contracts.pages import WardTimeline
from ..engine import views

router = APIRouter(prefix="/api")

VERDICTS = ("worth_checking", "likely_justified", "needs_more_info")


def _flag_row(f, ward_by_code: dict, contractor_names: dict, method_by_wo: dict) -> dict:
    w = ward_by_code.get(f.ward_code, {})
    r = f.review or {}
    return {
        "flag_id": f.flag_id, "rule": f.rule, "tier": f.tier, "severity": f.severity,
        "reason": f.reason, "work_order_ids": f.work_order_ids,
        "ward_code": f.ward_code, "ward_slug": w.get("slug", ""), "ward_name": w.get("ward_name", ""),
        "road_id": f.road_id, "contractor_id": f.contractor_id,
        "contractor_name": contractor_names.get(f.contractor_id, f.contractor_id),
        "repair_method": method_by_wo.get(f.work_order_ids[0], ""),
        "amount_inr": f.amount_inr, "cost_inr": f.cost_inr,
        "verdict": r.get("verdict"), "headline": r.get("headline"), "review": f.review,
    }


def _lookups(request: Request):
    p = request.app.state.pre
    wards = {w["ward_code"]: w for w in p.wards}
    names = {c["contractor_id"]: c["contractor_name"] for c in p.contractors}
    methods = p.wo.set_index("work_order_id")["repair_method"].to_dict()
    return p, wards, names, methods


@router.get("/home/top-flags")
def top_flags(request: Request, limit: int = Query(6, ge=1, le=24)) -> dict:
    """Top audit-tier flags by money involved, one per ward."""
    p, wards, names, methods = _lookups(request)
    seen: set[str] = set()
    out = []
    def worth(f) -> bool:
        return f.review is not None and f.review.get("verdict") == "worth_checking"

    for f in sorted((f for f in p.flags if f.tier == "audit" and worth(f)), key=lambda f: -f.amount_inr):
        if f.ward_code in seen:
            continue
        seen.add(f.ward_code)
        out.append(_flag_row(f, wards, names, methods))
        if len(out) == limit:
            break
    total = sum(1 for f in p.flags if f.tier == "audit")
    return {"total_audit": total, "items": out}


@router.get("/home/audit-strip")
def audit_strip(request: Request) -> dict:
    """The 'How we audited' numbers: repairs checked, audit-tier flags, Claude's verdict split, and one likely-justified example."""
    p, wards, names, methods = _lookups(request)
    audit = [f for f in p.flags if f.tier == "audit"]
    split = {v: 0 for v in VERDICTS}
    for f in audit:
        v = (f.review or {}).get("verdict")
        if v in split:
            split[v] += 1
    # a verdict whose own headline still says "worth a look" would contradict the card, so it is not used as the example
    just = [f for f in audit if (f.review or {}).get("verdict") == "likely_justified"
            and "worth a look" not in (f.review or {}).get("headline", "").lower()
            and "worth check" not in (f.review or {}).get("headline", "").lower()]
    ex = max(just, key=lambda f: f.amount_inr, default=None)
    return {
        "repairs_checked": int(len(p.wo)), "flagged": len(audit),
        "reviewed": sum(split.values()), **split,
        "example": _flag_row(ex, wards, names, methods) if ex else None,
    }


@router.get("/home/contractors")
def home_contractors(request: Request) -> list[dict]:
    """All contractors with their four plain grades, compact, for the home cards."""
    p = request.app.state.pre
    out = []
    for c in p.contractors:
        card = views.contractor_card(p.data, p.wo, p.flags, p.contractors, p.wards, c["contractor_id"])
        out.append({
            "contractor_id": card["contractor_id"], "contractor_name": card["contractor_name"],
            "work_orders": card["work_orders"], "spend_inr": card["spend_inr"],
            "wards_active": card["wards_active"], "small_sample": card["small_sample"],
            "over_rate_count": card["over_rate_count"],
            "grades": [{"key": g["key"], "band": g["band"], "headline": g["headline"]} for g in card["grades"]],
        })
    return out


@router.get("/home/monsoon", response_model=WardTimeline)
def home_monsoon(request: Request) -> dict:
    p = request.app.state.pre
    return views.ward_timeline(p.data, p.wo, None)


@router.get("/home/methods")
def home_methods(request: Request) -> list[dict]:
    """Spend by repair method: held vs didn't hold, ranked by spend."""
    wo = request.app.state.pre.wo
    out = []
    for m, g in wo.groupby("repair_method"):
        failed = float(g.loc[g.reopened, "cost_inr"].sum())
        spend = float(g.cost_inr.sum())
        out.append({"repair_method": m, "spend_inr": spend, "held_inr": spend - failed, "failed_inr": failed,
                    "failed_pct": failed / spend * 100 if spend else 0.0, "work_orders": int(len(g))})
    return sorted(out, key=lambda r: -r["spend_inr"])


def _audit_rows(request: Request, rule, tier, ward, contractor, verdict, method):
    p, wards, names, methods = _lookups(request)
    rows = [_flag_row(f, wards, names, methods) for f in p.flags]
    for r in rows:
        r["_verdict"] = r["verdict"] or "none"
    flt = {
        "rule": rule.upper() if rule else None,
        "tier": None if tier == "all" else tier,
        "ward": ward.lower() if ward else None,
        "contractor": contractor.upper() if contractor else None,
        "verdict": verdict,
        "method": method,
    }
    field = {"rule": "rule", "tier": "tier", "ward": "ward_slug", "contractor": "contractor_id",
             "verdict": "_verdict", "method": "repair_method"}

    def apply(skip: str | None = None):
        return [r for r in rows if all(v is None or k == skip or r[field[k]] == v for k, v in flt.items())]

    matched = apply()
    matched.sort(key=lambda r: (r["tier"] != "audit", -r["amount_inr"]))
    return p, names, matched, apply, field


@router.get("/audit")
def audit(
    request: Request,
    rule: str | None = None, tier: str = "audit", ward: str | None = None,
    contractor: str | None = None, verdict: str | None = None, method: str | None = None,
    limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
) -> dict:
    """Filterable list of flags with facet counts (each facet is counted with the OTHER filters applied)."""
    p, names, matched, apply, field = _audit_rows(request, rule, tier, ward, contractor, verdict, method)
    facets = {}
    for k in ("rule", "ward", "contractor", "verdict", "method"):
        counts: dict[str, int] = {}
        for r in apply(skip=k):
            counts[r[field[k]]] = counts.get(r[field[k]], 0) + 1
        facets[k] = counts
    items = [{k: v for k, v in r.items() if k not in ("_verdict", "review")} for r in matched[offset:offset + limit]]
    return {"total": len(matched), "limit": limit, "offset": offset, "facets": facets, "items": items,
            "contractors": names, "wards": {w["slug"]: w["ward_name"] for w in p.wards}}


@router.get("/audit.csv")
def audit_csv(
    request: Request,
    rule: str | None = None, tier: str = "audit", ward: str | None = None,
    contractor: str | None = None, verdict: str | None = None, method: str | None = None,
) -> Response:
    """The same filters as /api/audit, as a CSV (work_order_id first)."""
    _, _, matched, _, _ = _audit_rows(request, rule, tier, ward, contractor, verdict, method)
    cols = ["work_order_id", "rule", "tier", "severity", "reason", "ward_code", "road_id", "contractor_id",
            "contractor_name", "repair_method", "amount_inr", "claude_verdict", "claude_headline"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in matched:
        w.writerow({"work_order_id": r["work_order_ids"][0], **{c: r.get(c) for c in cols[1:10]},
                    "claude_verdict": r["verdict"] or "", "claude_headline": r["headline"] or ""})
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="roadrupee_audit.csv"'})
