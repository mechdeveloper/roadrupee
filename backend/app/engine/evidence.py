"""Deterministic evidence pack for a flag. No LLM, no guesses: every number comes from the data."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import pandas as pd

from ..contracts.evidence import FlagEvidence
from ..loader import Data
from .flags import DLP_REVIEW_REASON, OVER_RATE_X, UTILITY_RE, Flag, dlp_tier, inr

HOTSPOT_KM = 1.5
SYNTHETIC = "All data is synthetic and all contractors are fictional."

RULE_STEPS = {
    "OVER_RATE": [
        "Looked up the standard rate for the repair method in the rate card.",
        "Expected cost = rate x area (per sqm) or the flat rate (per job).",
        "Compared the billed amount with the expected cost; normal variation is about ±20–30%.",
        "Flagged only because the bill is more than 1.5x the expected cost.",
    ],
    "DOUBLE_BILL": [
        "Looked for another work order on the same road with the same repair method.",
        "Checked that the two were assigned within 7 days of each other.",
        "Checked whether the later work order has any complaint linked to it (it has none).",
    ],
    "DLP_PAID": [
        "Checked whether the road is still under its Defect Liability Period (DLP).",
        "Checked whether the work is a surface repair the original road contractor is liable for.",
        "Checked the engineer's remark for a utility trench (MTNL / MGL), which would not be the contractor's liability.",
    ],
    "SLA_BREACH": [
        "Measured hours from the first linked complaint (or assignment if none) to completion.",
        "Compared with the target hours for this job.",
        "Flagged only when it took more than twice the target; plain misses are a scorecard metric.",
    ],
    "SILENT_FAILURE": [
        "Read the social-media posts with Claude: is it about a road or drain problem, and does it say the problem is back?",
        "Placed each post in a ward from the locality it names.",
        "Looked for a repair in that ward, of the same kind, finished in the 45 days before the post and not recorded as reopened.",
        "Flagged it for review only: same ward and issue type is not proof of the same road, and posts can be wrong or forwarded.",
    ],
    "REPEAT_FAILURE": [
        "Grouped reopened jobs by road, contractor and repair method.",
        "Linked jobs whose completion dates chain within 60 days of each other.",
        "Flagged chains of two or more reopened jobs; a single reopen is only a scorecard metric.",
    ],
}


@dataclass
class EvidenceIndex:
    wo: pd.DataFrame  # by work_order_id
    complaints: pd.DataFrame  # by complaint_id
    roads: pd.DataFrame  # by road_id
    traffic: pd.DataFrame  # by road_id
    wards: pd.DataFrame  # by ward_code
    rain: pd.DataFrame
    tides: pd.DataFrame  # by date
    hotspots: pd.DataFrame
    rate_card: pd.DataFrame  # by repair_method
    contractors: dict[str, dict]
    rain_end: pd.Timestamp


def build_index(data: Data, wo: pd.DataFrame, contractors: list[dict]) -> EvidenceIndex:
    tides = pd.read_csv(data.dir / "tides.csv")
    tides["date"] = pd.to_datetime(tides["date"])
    return EvidenceIndex(
        wo=wo.set_index("work_order_id", drop=False),
        complaints=data.complaints.set_index("complaint_id", drop=False),
        roads=data.roads.set_index("road_id", drop=False),
        traffic=data.traffic.set_index("road_id"),
        wards=data.wards.set_index("ward_code"),
        rain=data.rain,
        tides=tides,
        hotspots=data.hotspots,
        rate_card=data.rate_card.set_index("repair_method"),
        contractors={c["contractor_id"]: c for c in contractors},
        rain_end=data.rain["date"].max().normalize(),
    )


# ---------------------------------------------------------------- helpers
def _s(v, default: str = "") -> str:
    return default if v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v) else str(v)


def _f(v) -> float | None:
    return None if pd.isna(v) else float(v)


def _ts(v) -> str | None:
    return None if pd.isna(v) else pd.Timestamp(v).strftime("%Y-%m-%d %H:%M")


def _km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))


def _plain_n(x: float) -> str:
    return f"{x:,.1f}".rstrip("0").rstrip(".") if x % 1 else f"{int(x):,}"


# ---------------------------------------------------------------- pieces
def _wo_detail(ix: EvidenceIndex, r: pd.Series) -> dict:
    ids = [i for i in str(r.linked_complaint_ids).split("|") if i]
    starts = [ix.complaints.at[i, "received_at"] for i in ids if i in ix.complaints.index]
    start = min(starts) if starts else r.assigned_at
    hours = (r.completed_at - start).total_seconds() / 3600 if pd.notna(r.completed_at) else None
    return dict(
        work_order_id=r.work_order_id, ward_code=r.ward_code, road_id=r.road_id, work_type=r.work_type,
        repair_method=r.repair_method, contractor_id=r.contractor_id, contractor_name=r.contractor_name,
        assigned_at=_ts(r.assigned_at), work_started_at=_ts(r.work_started_at), completed_at=_ts(r.completed_at),
        area_sqm=_f(r.area_sqm), cost_inr=float(r.cost_inr), sla_hours=float(r.sla_hours),
        actual_hours=None if hours is None else round(hours, 1),
        sla_ratio=None if hours is None else round(hours / float(r.sla_hours), 2),
        sla_met=_s(r.sla_met), reopened_within_30d=bool(r.reopened),
        engineer_remark=_s(r.engineer_remark), linked_complaint_ids=ids,
    )


def _rate_check(ix: EvidenceIndex, r: pd.Series) -> dict:
    rc = ix.rate_card.loc[r.repair_method]
    rate = float(rc.standard_rate_inr)
    per_sqm = rc.unit == "per sqm"
    expected = float(r.expected_cost_inr)
    ratio = float(r.cost_inr) / expected
    if per_sqm:
        calc = f"{inr(rate)} per sqm x {_plain_n(float(r.area_sqm))} sqm = {inr(expected)} expected"
    else:
        calc = f"{inr(rate)} per job (flat rate) = {inr(expected)} expected"
    return dict(
        work_order_id=r.work_order_id, repair_method=r.repair_method, unit=str(rc.unit), standard_rate_inr=rate,
        area_sqm=_f(r.area_sqm), expected_inr=round(expected, 2), billed_inr=float(r.cost_inr),
        ratio=round(ratio, 2), normal_range_pct=[20, 30], threshold_x=OVER_RATE_X,
        steps=[calc, f"Billed {inr(r.cost_inr)} / {inr(expected)} expected = {ratio:.2f}x",
               "Normal variation is about ±20–30%; flagged above 1.5x."],
    )


def _road(ix: EvidenceIndex, road_id: str) -> dict:
    r = ix.roads.loc[road_id]
    t = ix.traffic.loc[road_id] if road_id in ix.traffic.index else None
    return dict(
        road_id=road_id, road_name=r.road_name, segment_no=int(r.segment_no), road_type=r.road_type,
        surface=r.surface, last_resurfaced=_s(r.last_resurfaced) or None, under_dlp=r.under_dlp,
        bus_route=r.bus_route,
        congestion_index_0_10=None if t is None else float(t.congestion_index_0_10),
        bus_routes_count=None if t is None else int(t.bus_routes_count),
        peak_hour_vehicles=None if t is None else int(t.peak_hour_vehicles),
    )


def _rain(ix: EvidenceIndex, done) -> tuple[dict | None, list[str]]:
    if pd.isna(done):
        return None, []
    d0 = pd.Timestamp(done).normalize()
    rn = ix.rain
    win = rn[(rn.date >= d0 - pd.Timedelta(days=7)) & (rn.date <= d0 + pd.Timedelta(days=7))]
    days = []
    for d in pd.date_range(d0 - pd.Timedelta(days=7), d0 + pd.Timedelta(days=7)):
        g = win[win.date == d]
        if g.empty:
            days.append(dict(date=d.strftime("%Y-%m-%d"), santacruz_mm=None, colaba_mm=None, imd_alert=None))
            continue
        by = g.set_index("station").rainfall_mm
        order = {"Green": 0, "Yellow": 1, "Orange": 2, "Red": 3}
        al = max(g.imd_alert, key=order.get)
        days.append(dict(date=d.strftime("%Y-%m-%d"), santacruz_mm=_f(by.get("Santacruz")),
                         colaba_mm=_f(by.get("Colaba")), imd_alert=al))

    def tot(lo, hi) -> dict[str, float]:
        g = rn[(rn.date >= lo) & (rn.date <= hi)]
        return {k: round(float(v), 1) for k, v in g.groupby("station").rainfall_mm.sum().items()}

    before = tot(d0 - pd.Timedelta(days=7), d0 - pd.Timedelta(days=1))
    after = tot(d0, d0 + pd.Timedelta(days=6))
    alerts = [d["imd_alert"] for d in days if d["imd_alert"]]
    order = {"Green": 0, "Yellow": 1, "Orange": 2, "Red": 3}
    note = None
    notes = []
    if d0 + pd.Timedelta(days=6) > ix.rain_end:
        note = (f"Rain data ends on {ix.rain_end:%d %b %Y}; the week after completion is only partly covered, "
                "so rain may be under-counted.")
        notes.append(note)
    return dict(window=days, week_before_mm=before, week_after_mm=after,
                max_imd_alert=max(alerts, key=order.get) if alerts else None,
                covered_until=ix.rain_end.strftime("%Y-%m-%d"), note=note), notes


def _hotspots(ix: EvidenceIndex, road: pd.Series, ward: str) -> list[dict]:
    lat, lon = (road.start_lat + road.end_lat) / 2, (road.start_lon + road.end_lon) / 2
    out = []
    for h in ix.hotspots.itertuples():
        km = _km(lat, lon, h.lat, h.lon)
        if km <= HOTSPOT_KM or h.ward_code == ward and km <= 3:
            out.append(dict(hotspot_id=h.hotspot_id, name=h.name, distance_m=int(round(km * 1000)),
                            same_ward=h.ward_code == ward, flood_threshold_mm_per_day=float(h.flood_threshold_mm_per_day),
                            tide_sensitive=h.tide_sensitive, years_flagged_last_5=int(h.years_flagged_last_5)))
    return sorted(out, key=lambda x: x["distance_m"])


def _related(ix: EvidenceIndex, f: Flag, p: pd.Series) -> list[dict]:
    seen = {p.work_order_id}
    out: list[dict] = []

    def add(wid: str, relation: str):
        if wid in seen or wid not in ix.wo.index:
            return
        seen.add(wid)
        r = ix.wo.loc[wid]
        out.append(dict(work_order_id=wid, relation=relation, repair_method=r.repair_method,
                        contractor_id=r.contractor_id, completed_at=_ts(r.completed_at),
                        cost_inr=float(r.cost_inr), reopened_within_30d=bool(r.reopened)))

    if f.rule == "DOUBLE_BILL":
        for w in f.work_order_ids[1:]:
            add(w, "Earlier job on the same road with the same method (the possible double bill)")
    if f.rule == "REPEAT_FAILURE":
        for w in f.work_order_ids[1:]:
            add(w, "Another reopened job in the same repeat chain")
    same = ix.wo[(ix.wo.road_id == p.road_id) & (ix.wo.contractor_id == p.contractor_id)
                 & (ix.wo.repair_method == p.repair_method) & ix.wo.reopened
                 & (ix.wo.completed_at < p.completed_at)].sort_values("completed_at", ascending=False)
    for w in same.work_order_id.head(5):
        add(w, "Earlier repair on the same road by the same contractor and method that reopened within 30 days")
    return out


def _contractor(ix: EvidenceIndex, cid: str) -> dict:
    c = ix.contractors[cid]
    out = {k: c[k] for k in ("contractor_id", "contractor_name", "work_orders")}
    out |= {k: round(float(c[k]), 1) for k in ("reopen_observed_pct", "reopen_expected_pct", "reopen_ci_low_pct",
                                              "reopen_ci_high_pct", "sla_met_pct")}
    out["median_cost_vs_rate"] = round(float(c["median_cost_vs_rate"]), 2)
    out["small_sample"] = c["work_orders"] < 30
    return out


# ---------------------------------------------------------------- entry points
def build(ix: EvidenceIndex, f: Flag) -> dict:
    p = ix.wo.loc[f.work_order_ids[0]]
    wos = [ix.wo.loc[w] for w in f.work_order_ids]
    road = ix.roads.loc[p.road_id]

    comps = []
    for r in wos:
        for i in (x for x in str(r.linked_complaint_ids).split("|") if x):
            if i in ix.complaints.index:
                c = ix.complaints.loc[i]
                comps.append(dict(complaint_id=i, work_order_id=r.work_order_id, received_at=_ts(c.received_at),
                                  text=_s(c.description), language=_s(c.language), channel=_s(c.channel),
                                  photo_description=_s(c.photo_description), upvotes=int(c.upvotes),
                                  status=_s(c.status)))
    primary_has = any(c["work_order_id"] == p.work_order_id for c in comps)

    rain, rain_notes = _rain(ix, p.completed_at)
    tides = ix.tides
    d0 = pd.Timestamp(p.completed_at).normalize()
    big = tides[(tides.date >= d0 - pd.Timedelta(days=7)) & (tides.date <= d0 + pd.Timedelta(days=7))
                & tides.big_tide_flag.eq("Y")]

    remark = _s(p.engineer_remark)
    utility = bool(UTILITY_RE.search(remark))
    if road.under_dlp == "Y":
        tier = dlp_tier(p)
        why = ("A surface repair the original road contractor is liable for, with no utility-trench remark."
               if tier == "audit" else DLP_REVIEW_REASON + ".")
    else:
        why = "Road is not under a Defect Liability Period."
    warranty = dict(under_dlp=road.under_dlp, last_resurfaced=_s(road.last_resurfaced) or None,
                    utility_trench_in_remark=utility, explanation=why)

    ev = dict(
        flag_id=f.flag_id, rule=f.rule, tier=f.tier, severity=f.severity, claim=f.reason,
        how_we_checked=RULE_STEPS[f.rule], work_order_ids=list(f.work_order_ids),
        work_orders=[_wo_detail(ix, r) for r in wos],
        rate_checks=[_rate_check(ix, r) for r in wos],
        road=_road(ix, p.road_id),
        complaints=comps,
        complaints_note=None if primary_has else "No complaint linked",
        context=dict(
            rain=rain,
            big_tides=[dict(date=r.date.strftime("%Y-%m-%d"), height_m=float(r.height_m)) for r in big.itertuples()],
            low_lying_index=float(ix.wards.at[p.ward_code, "low_lying_index"]),
            flood_hotspots=_hotspots(ix, road, p.ward_code),
            warranty=warranty, engineer_remark=remark,
            complaints=dict(count=len(comps), total_upvotes=int(sum(c["upvotes"] for c in comps))),
        ),
        related_work_orders=_related(ix, f, p),
        contractor=_contractor(ix, p.contractor_id),
        social_posts=list((f.extra or {}).get("posts", [])),
        data_notes=[SYNTHETIC, f"Rainfall data covers 1 Jun to {ix.rain_end:%d %b %Y} only."] + rain_notes,
    )
    ev["rate_check"] = ev["rate_checks"][0]
    # validate shape (raises if the builder drifts from the contract)
    return FlagEvidence.model_validate(ev).model_dump(mode="json")


def evidence_hash(ev: dict) -> str:
    # social_posts is left out when empty so adding the field did not change any existing hash (cached verdicts stay valid)
    body = {k: v for k, v in ev.items() if k != "claude_review" and not (k == "social_posts" and not v)}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
