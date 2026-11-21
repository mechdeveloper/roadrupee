"""Next-rupee engine: rank road segments by risk, pick the most durable suitable repair, fit the ward's budget.

Deterministic Python only; Claude never computes anything here (it only writes a one-line explanation later).

Risk score (0-100) is the SUM of five parts, shown to the user as a transparent formula:
  complaints 30  open + in-progress complaints matched to the nearest road segment in their ward (GPS if present, else
                 the locality centroid). Each counts its derived severity, up to double when it has many "me too" votes.
                 Normalised against the city's 95th-percentile road.
  flood      25  nearest chronic flood spot within 1.5 km: years flagged in the last 5, +50% if tide-sensitive, nearer is
                 worse. Normalised against the worst possible spot.
  traffic    15  congestion index (70%) and bus routes (30%).
  accidents  15  pothole / waterlogged-road / open-chamber accidents on the road: fatal 3, grievous 2, minor 1.
                 Normalised against the city's 95th-percentile road.
  facilities 15  hospital with emergency services on the road as ambulance entry = 1.0, municipal school = 0.6 (capped at 1).

Severity is derived from the SLA ladder in the data (the more urgent the target repair time, the higher the severity):
road cave-in 5, open manhole 5, waterlogging 4, choked drain 3, pothole 3, broken paver blocks 2, vague categories 2.

Method: infer the road's main issue, then choose, among the repair methods actually used for that kind of work, the one with the
LOWEST 30-day reopen rate (not the cheapest). Cost = rate card x typical area for that method in this ward (per sqm) or the flat rate.
Budget: fund items in rank order against budget - spend; an item that does not fit is skipped so a smaller one below can still be
funded. Overspent wards (spend above budget) fund nothing.
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd

from . import trace as T
from .evidence import HOTSPOT_KM, _km
from .flags import inr
from .views import ward_slug

WEIGHTS = {"complaints": 30.0, "flood": 25.0, "traffic": 15.0, "accidents": 15.0, "facilities": 15.0}
SEVERITY = {
    "Road cave-in": 5, "Open or broken manhole": 5, "Waterlogging": 4, "Choked drain / nullah overflow": 3,
    "Pothole": 3, "Broken paver blocks": 2, "Road related": 2, "Other": 2,
}
ACCIDENT_WEIGHT = {"Fatal": 3, "Grievous": 2, "Minor": 1}
ACCIDENT_ISSUE = {"Pothole": "Pothole", "Waterlogged road": "Waterlogging", "Uneven road / open chamber": "Open or broken manhole"}
OPEN_STATUS = ("Open", "In Progress")
MAX_ITEMS = 12
MIN_JOBS_FOR_RATE = 30  # a method needs this many past jobs for its reopen rate to be trusted
LABELS = {
    "complaints": ("Open complaints", "More unresolved complaints, weighted by severity and 'me too' votes, add more points."),
    "flood": ("Flooding", "Roads near a chronic flood spot score higher; tide-sensitive spots score highest."),
    "traffic": ("Traffic", "Busier roads and bus routes score higher."),
    "accidents": ("Accidents", "Pothole, waterlogging and open-chamber accidents on the road add points."),
    "facilities": ("Schools and hospitals", "Roads that are a hospital's ambulance entry or serve a school score higher."),
}
NOTE = "Items are funded in rank order; one that does not fit is skipped so a smaller one below can still be funded."


def _xy(lat: float, lon: float, lat0: float) -> tuple[float, float]:
    return lon * 111.32 * math.cos(math.radians(lat0)), lat * 110.57


def _dist_to_segment_km(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float], lat0: float) -> float:
    px, py = _xy(p[0], p[1], lat0)
    ax, ay = _xy(a[0], a[1], lat0)
    bx, by = _xy(b[0], b[1], lat0)
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def formula() -> dict:
    return {
        "weights": [dict(key=k, label=LABELS[k][0], weight=w, description=LABELS[k][1]) for k, w in WEIGHTS.items()],
        "note": NOTE,
    }


def _method_table(wo: pd.DataFrame, rate_card: pd.DataFrame) -> dict[str, list[dict]]:
    """work_type -> methods used for it with reopen rate, rate, unit (only methods with enough history)."""
    out: dict[str, list[dict]] = {}
    for (wt, m), g in wo.groupby(["work_type", "repair_method"]):
        if len(g) < MIN_JOBS_FOR_RATE:
            continue
        rc = rate_card.loc[m]
        out.setdefault(wt, []).append(dict(
            repair_method=m, reopen_rate_pct=float(g.reopened.mean() * 100), rate_inr=float(rc.standard_rate_inr),
            unit=str(rc.unit), city_area=float(g.area_sqm.median()), jobs=int(len(g))))
    return out


def _complaint_points(pre, idx: T.TraceIndex) -> pd.DataFrame:
    """Open / in-progress complaints with a position and ward."""
    c = pre.data.complaints
    c = c[c.status.isin(OPEN_STATUS)].copy()
    lat, lon, ward = [], [], []
    for r in c.itertuples():
        g = T.geocode(r.locality_text, idx) if isinstance(r.locality_text, str) else None
        has_gps = pd.notna(r.lat) and pd.notna(r.lon)
        lat.append(float(r.lat) if has_gps else (g["lat"] if g else np.nan))
        lon.append(float(r.lon) if has_gps else (g["lon"] if g else np.nan))
        ward.append(r.ward_code if isinstance(r.ward_code, str) else (g["ward_code"] if g else None))
    c["p_lat"], c["p_lon"], c["p_ward"] = lat, lon, ward
    return c.dropna(subset=["p_lat", "p_lon", "p_ward"])


def build_all(pre) -> dict[str, dict]:
    """slug -> PlanResponse dict for every ward. Pure function of the data."""
    data, wo = pre.data, pre.wo
    idx = T.build_index(pre)
    roads = data.roads.copy()
    roads["mid_lat"] = (roads.start_lat + roads.end_lat) / 2
    roads["mid_lon"] = (roads.start_lon + roads.end_lon) / 2
    traffic = data.traffic.set_index("road_id")
    methods = _method_table(wo, data.rate_card.set_index("repair_method"))
    rate_card = data.rate_card.set_index("repair_method")

    # ---- complaints -> nearest road segment in their own ward
    comp = _complaint_points(pre, idx)
    by_ward = {w: g for w, g in roads.groupby("ward_code")}
    road_complaints: dict[str, list] = defaultdict(list)
    for r in comp.itertuples():
        cand = by_ward.get(r.p_ward)
        if cand is None or cand.empty:
            continue
        lat0 = float(r.p_lat)
        best = min(cand.itertuples(), key=lambda rd: _dist_to_segment_km(
            (r.p_lat, r.p_lon), (rd.start_lat, rd.start_lon), (rd.end_lat, rd.end_lon), lat0))
        road_complaints[best.road_id].append(r)

    def c_score(rows: list) -> float:
        return sum(SEVERITY.get(x.category_reported, 2) * (1 + min(int(x.upvotes or 0), 20) / 20) for x in rows)

    s_vals = [c_score(v) for v in road_complaints.values()]
    S_REF = float(np.percentile(s_vals, 95)) if s_vals else 1.0

    # ---- accidents (road defects only)
    acc = data.accidents[data.accidents.probable_cause.isin(ACCIDENT_ISSUE)]
    road_acc = {rid: g for rid, g in acc.groupby("road_id")}
    a_vals = [sum(ACCIDENT_WEIGHT[s] for s in g.severity) for g in road_acc.values()]
    A_REF = float(np.percentile(a_vals, 95)) if a_vals else 1.0

    fac = data.facilities.dropna(subset=["ambulance_entry_road"])
    road_fac = {rid: g for rid, g in fac.groupby("ambulance_entry_road")}

    # ---- per-ward budget
    spend = wo.groupby("ward_code").cost_inr.sum()
    wards = {w["ward_code"]: w for w in pre.wards}
    ward_area = wo.groupby(["ward_code", "work_type", "repair_method"]).area_sqm.agg(["median", "size"])

    plans: dict[str, dict] = {}
    for code, w in wards.items():
        items: list[dict] = []
        for rd in roads[roads.ward_code == code].itertuples():
            comps = road_complaints.get(rd.road_id, [])
            # --- flood
            hs = []
            for h in data.hotspots.itertuples():
                km = _km(rd.mid_lat, rd.mid_lon, h.lat, h.lon)
                if km <= HOTSPOT_KM:
                    f = (h.years_flagged_last_5 / 5) * (1.5 if h.tide_sensitive == "Y" else 1.0) * (1 - 0.5 * km / HOTSPOT_KM)
                    hs.append((f, km, h))
            hs.sort(key=lambda x: -x[0])
            flood = hs[0][0] / 1.5 if hs else 0.0
            # --- traffic
            tr = traffic.loc[rd.road_id] if rd.road_id in traffic.index else None
            congestion = float(tr.congestion_index_0_10) if tr is not None else 0.0
            buses = int(tr.bus_routes_count) if tr is not None else 0
            traffic_n = 0.7 * congestion / 10 + 0.3 * min(buses / 30, 1.0)
            # --- accidents
            ag = road_acc.get(rd.road_id)
            a_raw = sum(ACCIDENT_WEIGHT[s] for s in ag.severity) if ag is not None else 0
            # --- facilities
            fg = road_fac.get(rd.road_id)
            f_raw = 0.0
            if fg is not None:
                f_raw = sum(1.0 if (r.type == "Hospital" and r.emergency_services == "Y") else 0.6 for r in fg.itertuples())
            parts = {
                "complaints": WEIGHTS["complaints"] * min(1.0, c_score(comps) / S_REF) if comps else 0.0,
                "flood": WEIGHTS["flood"] * min(1.0, flood),
                "traffic": WEIGHTS["traffic"] * min(1.0, traffic_n),
                "accidents": WEIGHTS["accidents"] * min(1.0, a_raw / A_REF) if a_raw else 0.0,
                "facilities": WEIGHTS["facilities"] * min(1.0, f_raw),
            }
            parts = {k: round(v, 1) for k, v in parts.items()}
            risk = round(sum(parts.values()), 1)

            # --- reasons (icon chips) and evidence
            reasons: list[dict] = []
            if fg is not None:
                hosp = [r for r in fg.itertuples() if r.type == "Hospital"]
                sch = [r for r in fg.itertuples() if r.type == "School"]
                if hosp:
                    reasons.append(dict(kind="ambulance_route", label=f"Ambulance entry road for {hosp[0].name}",
                                        detail="Serves an emergency department", count=len(hosp)))
                if sch:
                    reasons.append(dict(kind="school_route", label=f"Leads to {sch[0].name}" if len(sch) == 1 else f"Leads to {len(sch)} municipal schools",
                                        detail=f"{int(sch[0].beds_or_students)} students" if len(sch) == 1 else "Municipal schools", count=len(sch)))
            if hs:
                f, km, h = hs[0]
                reasons.append(dict(kind="flood_hotspot", label=f"Floods when rain passes {h.flood_threshold_mm_per_day:.0f} mm a day",
                                    detail=f"{h.name}, {int(round(km * 1000))} m away; flagged in {int(h.years_flagged_last_5)} of the last 5 years", count=None))
                if h.tide_sensitive == "Y":
                    reasons.append(dict(kind="tide", label="Gets worse on big-tide days", detail=h.name, count=None))
            if ag is not None:
                nf = int((ag.severity == "Fatal").sum())
                ng = int((ag.severity == "Grievous").sum())
                reasons.append(dict(kind="accidents", label=f"{len(ag)} accident{'s' if len(ag) != 1 else ''} blamed on road defects",
                                    detail=f"{nf} fatal, {ng} grievous", count=len(ag)))
            if comps:
                votes = sum(int(x.upvotes or 0) for x in comps)
                latest = max(str(x.received_at)[:10] for x in comps)
                reasons.append(dict(kind="open_complaints", label=f"{len(comps)} complaint{'s' if len(comps) != 1 else ''} still open",
                                    detail=f"Most recent {latest}; {votes} “me too” votes", count=len(comps)))
            if congestion >= 6.5:
                reasons.append(dict(kind="traffic", label=f"Heavy traffic (congestion {congestion:.1f} out of 10)", detail=f"{int(tr.peak_hour_vehicles):,} vehicles at peak", count=None))
            if buses >= 1:
                reasons.append(dict(kind="bus_route", label=f"{buses} bus route{'s' if buses != 1 else ''} use this road", detail="BEST buses", count=buses))
            evidence = dict(
                complaint_ids=sorted(x.complaint_id for x in comps),
                accident_ids=sorted(ag.accident_id) if ag is not None else [],
                hotspot_ids=[h.hotspot_id for _, _, h in hs[:3]],
                facility_ids=sorted(fg.facility_id) if fg is not None else [],
            )

            # --- main issue -> most durable suitable method
            issue_w: dict[str, float] = defaultdict(float)
            for x in comps:
                if x.category_reported in SEVERITY and x.category_reported not in ("Road related", "Other"):
                    issue_w[x.category_reported] += SEVERITY[x.category_reported]
            if ag is not None:
                for cause, n in ag.probable_cause.value_counts().items():
                    issue_w[ACCIDENT_ISSUE[cause]] += n * 2
            issue_w["Waterlogging"] += parts["flood"] / WEIGHTS["flood"] * 6
            issue = max(issue_w, key=issue_w.get) if issue_w and max(issue_w.values()) > 0 else "Pothole"
            options = methods.get(issue) or methods["Pothole"]

            def area_for(m: dict) -> float | None:
                if m["unit"] != "per sqm":
                    return None
                key = (code, issue, m["repair_method"])
                if key in ward_area.index and ward_area.loc[key, "size"] >= 5:
                    return float(ward_area.loc[key, "median"])
                return m["city_area"]

            def cost_for(m: dict) -> float:
                a = area_for(m)
                return m["rate_inr"] * a if a is not None else m["rate_inr"]

            best = min(options, key=lambda m: (m["reopen_rate_pct"], cost_for(m)))
            cheap = min(options, key=lambda m: (cost_for(m), m["reopen_rate_pct"]))
            area = area_for(best)
            cost = round(cost_for(best), 2)
            if len(options) == 1:
                why = f"{best['repair_method']} is the standard repair for this kind of problem ({best['reopen_rate_pct']:.1f}% reopened within 30 days)."
            elif cheap["repair_method"] == best["repair_method"]:
                why = f"{best['repair_method']} is both the most durable ({best['reopen_rate_pct']:.1f}% reopened within 30 days) and the cheapest suitable option."
            else:
                why = (f"{best['repair_method']} reopened less often ({best['reopen_rate_pct']:.1f}%) than {cheap['repair_method']} "
                       f"({cheap['reopen_rate_pct']:.1f}%), so the dearer repair wastes less money.")
            alts = [] if cheap["repair_method"] == best["repair_method"] else [dict(
                repair_method=cheap["repair_method"], reopen_rate_pct=round(cheap["reopen_rate_pct"], 1),
                estimated_cost_inr=round(cost_for(cheap), 2))]
            basis = (f"{inr(best['rate_inr'])} per sqm × {area:g} sqm (typical {issue.lower()} repair here)"
                     if area is not None else f"{inr(best['rate_inr'])} per job (flat rate)")
            items.append(dict(
                rank=0, road_id=rd.road_id, road_name=rd.road_name, segment_no=int(rd.segment_no), road_type=rd.road_type,
                length_m=float(rd.length_m), lat=round(float(rd.mid_lat), 6), lon=round(float(rd.mid_lon), 6),
                risk_score=risk,
                score_parts=[dict(key=k, label=LABELS[k][0], points=parts[k], max_points=WEIGHTS[k]) for k in WEIGHTS],
                reasons=reasons,
                recommended_method=dict(repair_method=best["repair_method"], reopen_rate_pct=round(best["reopen_rate_pct"], 1),
                                        rate_inr=best["rate_inr"], unit=best["unit"], why=why),
                alternatives=alts, area_sqm_estimate=None if area is None else round(area, 1),
                estimated_cost_inr=cost, cost_basis=basis, within_budget=False, evidence=evidence, explanation=None,
                _issue=issue))

        items.sort(key=lambda i: (-i["risk_score"], i["road_id"]))
        items = [i for i in items if i["risk_score"] > 0][:MAX_ITEMS]
        remaining = float(w["budget_inr"] - spend.get(code, 0.0))
        left = max(remaining, 0.0)
        for n, it in enumerate(items, 1):
            it["rank"] = n
            if it["estimated_cost_inr"] <= left:  # fund it; otherwise skip so a smaller item below can still fit
                it["within_budget"] = True
                left -= it["estimated_cost_inr"]
        plans[w["slug"]] = dict(
            ward_slug=w["slug"], ward_code=code, ward_name=w["ward_name"], budget_inr=float(w["budget_inr"]),
            spent_inr=float(spend.get(code, 0.0)), remaining_inr=remaining, formula=formula(), items=items)
    return plans


def public(item: dict) -> dict:
    """Drop engine-internal fields before sending to clients."""
    return {k: v for k, v in item.items() if not k.startswith("_")}


def city_top(plans: dict[str, dict], limit: int) -> list[dict]:
    rows = [dict(ward_slug=p["ward_slug"], ward_code=p["ward_code"], ward_name=p["ward_name"], item=public(i))
            for p in plans.values() for i in p["items"]]
    rows.sort(key=lambda r: (-r["item"]["risk_score"], r["ward_code"], r["item"]["road_id"]))
    return rows[:limit]
