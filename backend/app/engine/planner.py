"""Next-rupee planner -> contracts.plan.PlanResponse (one per ward, precomputed at startup).

Deterministic pandas; Claude never computes numbers (`explanation` stays null here).

1. Open / in-progress complaints are matched to a road segment (engine/linker.py) and grouped
   into issues: one per (road segment, problem type).
2. Each road segment with open issues gets a risk score out of 100 = sum of five parts:
   complaints 30 · flood 25 · traffic 15 · accidents 15 · schools & hospitals 15.
   Flood uses this season's rain: days the nearest station crossed the hotspot's flooding level,
   how many fell on big tides (tide-sensitive spots), its 5-year record and whether a pump is near.
3. Method = lowest 30-day reopen rate among methods used for that problem (durable, not cheapest).
4. within_budget: fund items in rank order against budget - spend. A surface defect on a road still
   under the original contractor's Defect Liability Period costs the city nothing (same liability
   rule as flags.DLP_PAID audit tier), so it is marked within budget without using any of it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..loader import Data
from .flags import DLP_AUDIT_WORK_TYPES, Flag, inr
from .linker import seg_dist_m
from .views import ward_slug

SEVERITY = {24: 5, 48: 4, 72: 3, 120: 2, 168: 1}
ROAD_CAUSES = {"Pothole", "Waterlogged road", "Uneven road / open chamber"}
SEV_W = {"Fatal": 3, "Grievous": 2, "Minor": 1}
HOTSPOT_RADIUS_M = 500
MAX_ITEMS = 15

FORMULA = {
    "weights": [
        {"key": "complaints", "label": "Open complaints", "weight": 30,
         "description": "Unresolved complaints on this road, weighted by how serious the problem is and by 'me too' votes."},
        {"key": "flood", "label": "Flooding", "weight": 25,
         "description": "Near a chronic flood spot: more points the more days this monsoon's rain crossed its flooding level, more if big tides hit on those days, if it floods most years and if no pump is nearby."},
        {"key": "traffic", "label": "Traffic", "weight": 15,
         "description": "Busier roads at peak hour and BEST bus routes score higher."},
        {"key": "accidents", "label": "Accidents", "weight": 15,
         "description": "Pothole, waterlogging and open-chamber accidents on the road, fatal ones counting most."},
        {"key": "facilities", "label": "Schools and hospitals", "weight": 15,
         "description": "The ambulance entry road of a hospital with an emergency department scores highest; school roads also add points."},
    ],
    "note": ("Items are funded in rank order until the remaining budget runs out. A road still under the original "
             "contractor's warranty (Defect Liability Period) should be repaired by that contractor at no cost to the city, "
             "so it does not use the budget."),
}
WEIGHT = {w["key"]: w["weight"] for w in FORMULA["weights"]}
LABEL = {w["key"]: w["label"] for w in FORMULA["weights"]}


def _norm(s: pd.Series, cap: float | None = None) -> pd.Series:
    s = s.astype(float)
    top = cap if cap is not None else (s.max() or 1.0)
    return (s / top).clip(0, 1)


def method_stats(data: Data, wo: pd.DataFrame) -> pd.DataFrame:
    rc = data.rate_card.set_index("repair_method")
    m = (wo.groupby(["work_type", "repair_method"])
           .agg(reopen=("reopened", "mean"), jobs=("reopened", "size"), area=("area_sqm", "median")).reset_index())
    m["unit"] = m.repair_method.map(rc.unit)
    m["rate"] = m.repair_method.map(rc.standard_rate_inr).astype(float)
    m["area"] = np.where(m.unit == "per sqm", m.area.round(0).clip(lower=1), np.nan)
    m["cost"] = np.where(m.unit == "per sqm", m.rate * m.area, m.rate)
    return m.sort_values(["work_type", "reopen", "cost"])


def _hotspots(data: Data) -> pd.DataFrame:
    h = data.hotspots.copy()
    tides = pd.read_csv(data.dir / "tides.csv")
    big = set(pd.to_datetime(tides.loc[tides.big_tide_flag == "Y", "date"]))
    days, tide_days = [], []
    for r in h.itertuples():
        st = data.rain[data.rain.station == ("Colaba" if r.lat < 19.0 else "Santacruz")]
        hit = st.loc[st.rainfall_mm >= r.flood_threshold_mm_per_day, "date"]
        days.append(len(hit))
        tide_days.append(len(set(hit) & big) if r.tide_sensitive == "Y" else 0)
    h["flood_days"], h["flood_tide_days"] = days, tide_days
    h["flood_score"] = (0.4 * (h.flood_days / 20).clip(upper=1) + 0.25 * h.years_flagged_last_5 / 5
                        + 0.2 * (h.flood_tide_days / 6).clip(upper=1) + 0.15 * h.pumping_station_nearby.eq("N")).clip(upper=1)
    return h


def build_plan(data: Data, wo: pd.DataFrame, flags: list[Flag], open_linked: pd.DataFrame) -> dict:
    """Returns {"by_ward": {slug: PlanResponse dict}, "issues": [...] (for trace), "methods": [...]}."""
    roads = data.roads.set_index("road_id")
    wards = data.wards.set_index("ward_code")
    o = open_linked[open_linked.road_id.notna() & (open_linked.issue_type != "Unclear")].copy()
    sev_by_type = wo.assign(sev=wo.sla_hours.map(SEVERITY)).groupby("work_type").sev.mean()
    o["severity"] = (o.issue_type.map(sev_by_type) + o.urgent * 0.75).clip(upper=5)

    issues = (o.groupby(["road_id", "issue_type"])
                .agg(complaints=("complaint_id", "size"), upvotes=("upvotes", "sum"), severity=("severity", "max"),
                     last=("received_at", "max"), complaint_ids=("complaint_id", list)).reset_index())
    issues["ward_code"] = issues.road_id.map(roads.ward_code)

    # ---- road-level inputs
    o["weighted"] = o.severity * (1 + np.log1p(o.upvotes) / 2)
    rd = o.groupby("road_id").agg(c_raw=("weighted", "sum"), n_open=("complaint_id", "size"), last=("received_at", "max"))
    rd["ward_code"] = rd.index.map(roads.ward_code)
    tr = data.traffic.set_index("road_id")
    acc = data.accidents[data.accidents.probable_cause.isin(ROAD_CAUSES)].assign(w=lambda a: a.severity.map(SEV_W))
    acc_by = acc.groupby("road_id")
    fac = data.facilities
    hot = _hotspots(data)
    ll = wards.low_lying_index

    def nearest_hotspot(rid):
        r = roads.loc[rid]
        d = hot.apply(lambda h: seg_dist_m(h.lat, h.lon, r), axis=1)
        i = d.idxmin()
        return hot.loc[i] if d[i] <= HOTSPOT_RADIUS_M else None

    near = {rid: nearest_hotspot(rid) for rid in rd.index}
    acc_w = acc_by.w.sum().reindex(rd.index).fillna(0)
    parts = pd.DataFrame(index=rd.index)
    parts["complaints"] = WEIGHT["complaints"] * _norm(rd.c_raw, cap=float(rd.c_raw.quantile(0.95)))
    parts["flood"] = WEIGHT["flood"] * pd.Series(
        {rid: (near[rid].flood_score if near[rid] is not None else 0.35 * ll[rd.ward_code[rid]]) for rid in rd.index})
    cong = tr.congestion_index_0_10.reindex(rd.index).fillna(0)
    bus = roads.bus_route.reindex(rd.index).eq("Y")
    parts["traffic"] = WEIGHT["traffic"] * (0.7 * cong / 10 + 0.3 * bus)
    parts["accidents"] = WEIGHT["accidents"] * _norm(acc_w, cap=8)
    er = fac[(fac.type == "Hospital") & (fac.emergency_services == "Y")].groupby("ambulance_entry_road").facility_id.apply(list)
    hosp = fac[fac.type == "Hospital"].groupby("ambulance_entry_road").facility_id.apply(list)
    sch = fac[fac.type == "School"].groupby("ambulance_entry_road").facility_id.apply(list)
    has = lambda s: pd.Series(rd.index.isin(s.index), index=rd.index)  # noqa: E731
    parts["facilities"] = WEIGHT["facilities"] * (0.65 * has(er) + 0.1 * has(hosp) + 0.25 * has(sch)).clip(upper=1)
    parts = parts.round(1)
    rd["risk"] = parts.sum(axis=1).round(1)

    ms = method_stats(data, wo)
    best = ms.groupby("work_type").first()
    failed = wo[wo.reopened].groupby("road_id").work_order_id.apply(list)
    spend = wo.groupby("ward_code").cost_inr.sum()

    by_ward: dict[str, dict] = {}
    issue_rows: list[dict] = []
    for wc, w in wards.iterrows():
        budget, spent = float(w.monsoon_repair_budget_inr_2025), float(spend.get(wc, 0.0))
        remaining = budget - spent
        left = remaining
        ranked = rd[rd.ward_code == wc].sort_values(["risk", "c_raw"], ascending=False)
        items = []
        for rank, (rid, r) in enumerate(ranked.iterrows(), 1):
            road = roads.loc[rid]
            iss = (issues[issues.road_id == rid].assign(weight=lambda x: x.severity * x.complaints)
                   .sort_values(["weight", "severity"], ascending=False))  # main problem = most serious complaints in total
            top = iss.iloc[0]
            m = best.loc[top.issue_type]
            alts = ms[(ms.work_type == top.issue_type) & (ms.repair_method != m.repair_method)]
            per_sqm = m.unit == "per sqm"
            cost = float(m.cost)
            basis = f"{inr(m.rate)} per sqm × {int(m.area)} sqm (typical area for this repair)" if per_sqm else f"{inr(m.rate)} per job (rate card)"
            dlp = road.under_dlp == "Y" and top.issue_type in DLP_AUDIT_WORK_TYPES
            if dlp:
                within, basis = True, basis + ". Under the original contractor's warranty: should cost the city ₹0"
            elif cost <= left:
                within, left = True, left - cost
            else:
                within = False
            n_failed = len(failed.get(rid, []))
            why = (f"{m.repair_method} failed within 30 days {m.reopen * 100:.1f}% of the time on {top.issue_type.lower()} jobs"
                   + (f", less often than {alts.iloc[0].repair_method.lower()} ({alts.iloc[0].reopen * 100:.1f}%)" if len(alts) else "")
                   + ", so it wastes less money even if it costs more."
                   + (f" {n_failed} earlier fix{'es' if n_failed > 1 else ''} on this road already failed." if n_failed else "")
                   + (" Ask the original contractor to do it under warranty." if dlp else ""))

            reasons = []
            h = near[rid]
            if h is not None:
                reasons.append({"kind": "flood_hotspot", "label": f"Floods when rain passes {int(h.flood_threshold_mm_per_day)} mm a day",
                                "detail": f"{h['name']}: rain crossed that level on {int(h.flood_days)} days this monsoon; flagged in {int(h.years_flagged_last_5)} of the last 5 years",
                                "count": int(h.flood_days)})
                if h.tide_sensitive == "Y":
                    reasons.append({"kind": "tide", "label": "Big tides make the flooding worse",
                                    "detail": f"{int(h.flood_tide_days)} of those heavy-rain days fell on big-tide days (4.5 m or more)",
                                    "count": int(h.flood_tide_days)})
            if rid in er.index or rid in hosp.index:
                reasons.append({"kind": "ambulance_route", "label": "Ambulance entry road for a hospital",
                                "detail": "Serves an emergency department" if rid in er.index else "Hospital access road",
                                "count": len(hosp.get(rid, []))})
            if rid in sch.index:
                reasons.append({"kind": "school_route", "label": "Road outside a municipal school", "detail": "Children walk here every day",
                                "count": len(sch[rid])})
            if rid in acc_by.groups:
                a = acc_by.get_group(rid)
                reasons.append({"kind": "accidents", "label": f"{len(a)} accident{'s' if len(a) > 1 else ''} blamed on road defects",
                                "detail": f"{int((a.severity == 'Fatal').sum())} fatal, {int((a.severity == 'Grievous').sum())} grievous", "count": int(len(a))})
            others = [t.lower() for t in iss.issue_type[1:]]
            reasons.append({"kind": "open_complaints", "label": f"{int(r.n_open)} complaint{'s' if r.n_open > 1 else ''} still open",
                            "detail": f"Most recent {pd.Timestamp(r['last']).strftime('%d %b %Y')}" + (f"; also {', '.join(others)}" if others else ""),
                            "count": int(r.n_open)})
            if cong[rid] >= 7:
                reasons.append({"kind": "traffic", "label": "Heavy peak-hour traffic",
                                "detail": f"Congestion {cong[rid]:.1f} out of 10, {int(tr.peak_hour_vehicles.get(rid, 0)):,} vehicles an hour", "count": None})
            if bus[rid]:
                reasons.append({"kind": "bus_route", "label": "BEST bus route", "detail": "Buses use this road", "count": None})

            item = {
                "rank": rank, "road_id": rid, "road_name": road.road_name, "segment_no": int(road.segment_no),
                "road_type": road.road_type, "length_m": float(road.length_m),
                "lat": round((road.start_lat + road.end_lat) / 2, 6), "lon": round((road.start_lon + road.end_lon) / 2, 6),
                "risk_score": float(r.risk),
                "score_parts": [{"key": k, "label": LABEL[k], "points": float(parts.loc[rid, k]), "max_points": float(WEIGHT[k])} for k in WEIGHT],
                "reasons": reasons,
                "recommended_method": {"repair_method": m.repair_method, "reopen_rate_pct": round(float(m.reopen) * 100, 1),
                                       "rate_inr": float(m.rate), "unit": m.unit, "why": why},
                "alternatives": [{"repair_method": a.repair_method, "reopen_rate_pct": round(float(a.reopen) * 100, 1),
                                  "estimated_cost_inr": float(a.cost)} for a in alts.itertuples()],
                "area_sqm_estimate": float(m.area) if per_sqm else None,
                "estimated_cost_inr": cost, "cost_basis": basis, "within_budget": bool(within),
                "evidence": {
                    "complaint_ids": [c for lst in iss.complaint_ids for c in lst],
                    "accident_ids": list(acc_by.get_group(rid).accident_id) if rid in acc_by.groups else [],
                    "hotspot_ids": [h.hotspot_id] if h is not None else [],
                    "facility_ids": sorted(set(hosp.get(rid, []) + sch.get(rid, []))),
                },
                "explanation": None,
            }
            items.append(item)
            for t in iss.itertuples():  # each complaint gets the method for its own problem
                t_dlp = road.under_dlp == "Y" and t.issue_type in DLP_AUDIT_WORK_TYPES
                issue_rows.append({"ward_code": wc, "ward_rank": rank, "road_id": rid, "road_name": road.road_name,
                                   "issue_type": t.issue_type, "risk_score": float(r.risk),
                                   "action": ("Ask the original contractor to repair under warranty (no cost to the city)" if t_dlp
                                              else f"Repair with {best.loc[t.issue_type].repair_method.lower()}"),
                                   "funding": ("Under warranty, no cost" if t_dlp else "Within the remaining budget" if within
                                               else "Beyond the remaining budget"),
                                   "complaint_ids": list(t.complaint_ids)})
        by_ward[ward_slug(wc)] = {"ward_slug": ward_slug(wc), "ward_code": wc, "ward_name": w.ward_name, "budget_inr": budget,
                             "spent_inr": spent, "remaining_inr": remaining, "formula": FORMULA, "items": items[:MAX_ITEMS]}
    return {"by_ward": by_ward, "issues": issue_rows,
            "methods": ms[["work_type", "repair_method", "reopen", "jobs", "cost"]].to_dict("records")}
