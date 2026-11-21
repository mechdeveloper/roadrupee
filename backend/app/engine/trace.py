"""Deterministic core of Trace my complaint: matching, geocoding, trail. No LLM.

Data facts this relies on (checked against the dataset):
  * Resolved and "Closed - Duplicate" complaints are always linked to a work order; duplicates share the
    original's work order (so "duplicates" = the other complaint ids on that work order).
  * Open / In Progress / Forwarded / Rejected complaints are never linked to a work order.
  * locality_text matches the gazetteer exactly 94% of the time; the rest is truncated ("Vile", "Saki").
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

import pandas as pd

from . import evidence as ev
from .flags import Flag, inr
from .views import ward_slug

ID_RE = re.compile(r"\bBMC25-\d{6}\b", re.I)
CATEGORIES = [
    "Pothole", "Waterlogging", "Open or broken manhole", "Choked drain / nullah overflow",
    "Road cave-in", "Broken paver blocks",
]
VAGUE = {"Road related", "Other"}  # about 18% of reported categories are wrong or vague
TEXT_MATCH_MIN = 0.92  # near-exact: the user pasted (almost) the complaint text itself
CONFIDENT = 0.72
MARGIN = 0.08
DEVANAGARI = re.compile(r"[ऀ-ॿ]")

_WORD = re.compile(r"[^\wऀ-ॿ]+")


def norm(s: str) -> str:
    """NFC, case-folded, punctuation removed, whitespace collapsed (keeps Devanagari letters and marks)."""
    return _WORD.sub(" ", unicodedata.normalize("NFC", str(s)).casefold()).strip()


# ----------------------------------------------------------------------------- index
@dataclass
class Place:
    key: str  # normalised name or alias
    locality: str
    ward_code: str
    lat: float
    lon: float
    kind: str  # "exact" (official name) | "alias"


@dataclass
class TraceIndex:
    complaints: pd.DataFrame  # indexed by complaint_id, with norm_text
    wo_of: dict[str, str]  # complaint_id -> work_order_id
    places: list[Place]
    wards: dict[str, dict]  # ward_code -> ward dict (slug, name)


def build_index(pre) -> TraceIndex:
    c = pre.data.complaints.copy()
    c["norm_text"] = c["description"].map(norm)
    c = c.set_index("complaint_id", drop=False)
    wo_of: dict[str, str] = {}
    for r in pre.wo.itertuples():
        for cid in str(r.linked_complaint_ids).split("|"):
            if cid:
                wo_of[cid] = r.work_order_id
    places: list[Place] = []
    for r in pre.data.localities.itertuples():
        places.append(Place(norm(r.locality), r.locality, r.ward_code, float(r.lat), float(r.lon), "exact"))
        if isinstance(r.aliases, str):
            for a in r.aliases.split(";"):
                if a.strip():
                    places.append(Place(norm(a), r.locality, r.ward_code, float(r.lat), float(r.lon), "alias"))
    return TraceIndex(c, wo_of, places, {w["ward_code"]: w for w in pre.wards})


# ----------------------------------------------------------------------------- geocoding
def geocode(query: str | None, idx: TraceIndex) -> dict | None:
    """Locality text -> gazetteer entry. exact / alias / contained / prefix / fuzzy, best first."""
    q = norm(query or "")
    if not q:
        return None

    def out(p: Place, how: str) -> dict:
        w = idx.wards.get(p.ward_code, {})
        return dict(locality=p.locality, ward_code=p.ward_code, ward_slug=ward_slug(p.ward_code),
                    ward_name=w.get("ward_name", ""), lat=p.lat, lon=p.lon, match=how)

    for p in idx.places:
        if p.key == q:
            return out(p, p.kind)
    # a longer text that contains a known name ("andheri west station road")
    hits = [p for p in idx.places if len(p.key) >= 4 and re.search(rf"(?<!\w){re.escape(p.key)}(?!\w)", q)]
    if hits:
        return out(max(hits, key=lambda p: len(p.key)), "contained")
    if len(q) >= 3:  # truncated text ("vile" -> Vile Parle East)
        pref = sorted((p for p in idx.places if p.key.startswith(q)), key=lambda p: (len(p.key), p.locality))
        if pref:
            return out(pref[0], "prefix")
    keys = {p.key: p for p in idx.places}
    close = difflib.get_close_matches(q, list(keys), n=1, cutoff=0.8)
    return out(keys[close[0]], "fuzzy") if close else None


def geocode_tokens(text: str, idx: TraceIndex) -> dict | None:
    """Last resort for truncated or ambiguous names ("dahisar ke paas"): try each word of 5+ letters as an
    exact / alias / prefix locality (never fuzzy: short common words must not match places). Longest word wins."""
    seen: set[str] = set()
    best: tuple[int, dict] | None = None
    for tok in norm(text).split():
        if len(tok) < 5 or tok in seen:
            continue
        seen.add(tok)
        g = geocode(tok, idx)
        if g and g["match"] in ("exact", "alias", "prefix") and (best is None or len(tok) > best[0]):
            best = (len(tok), g)
    return best[1] if best else None


# ----------------------------------------------------------------------------- rule-based extraction
_MR = ["मध्ये", "आहे", "आहेत", "नाही", "झाले", "साचले", "खड्डा", "खड्डे", "पाठवा", "करा", "आला", "तुंबले"]
_HI = ["में", "है", "हैं", "नहीं", "भर गया", "गड्ढा", "गड्ढे", "कृपया", "जल्दी", "रहा", "रही", "पानी"]
_HINGLISH = {"hai", "hain", "mein", "pe", "par", "ki", "ka", "ke", "nahi", "nahin", "paani", "pani", "khadda", "kab", "bahut",
             "ko", "se", "bhar", "gaya", "gayi", "karo", "kripya", "jaldi", "gadda", "gaadi", "nikal", "rahi", "raha", "itna"}

_ISSUES: list[tuple[str, list[str]]] = [
    ("Open or broken manhole", ["manhole", "man hole", "chamber", "मॅनहोल", "मैनहोल", "झाकण", "ढक्कन", "गटाराचे झाकण"]),
    ("Road cave-in", ["cave in", "cavein", "sinkhole", "sunk", "collapsed", "धंस", "खचला", "खचले", "खचली", "धसला"]),
    ("Choked drain / nullah overflow", ["drain", "nullah", "nalla", "nala", "gutter", "choked", "नाला", "नाले", "गटार", "नाली", "तुंबले", "चोक"]),
    ("Broken paver blocks", ["paver", "footpath tiles", "पेव्हर", "फुटपाथ", "tiles"]),
    ("Pothole", ["pothole", "pot hole", "khadda", "khadde", "gadda", "gaddha", "गड्ढा", "गड्ढे", "खड्डा", "खड्डे", "खड्ड्यां"]),
    ("Waterlogging", ["waterlog", "water log", "flood", "paani", "pani", "water", "पाणी", "पानी", "साचले", "जलभराव", "तुंबले"]),
]


def rules_language(text: str) -> str:
    t = unicodedata.normalize("NFC", text)
    if DEVANAGARI.search(t):
        mr = sum(t.count(w) for w in _MR)
        hi = sum(t.count(w) for w in _HI)
        return "mr" if mr >= hi else "hi"
    words = set(norm(t).split())
    return "hi-en" if len(words & _HINGLISH) >= 2 else "en"


def rules_issue(text: str) -> str | None:
    t = norm(text)
    scored = []
    for order, (cat, kws) in enumerate(_ISSUES):
        n = sum(1 for k in kws if norm(k) in t)
        if n:
            scored.append((-n, order, cat))
    return sorted(scored)[0][2] if scored else None


def rules_locality(text: str, idx: TraceIndex) -> str | None:
    """Longest gazetteer name / alias appearing in the text (whole words)."""
    t = norm(text)
    hits = [p for p in idx.places if len(p.key) >= 4 and re.search(rf"(?<!\w){re.escape(p.key)}(?!\w)", t)]
    return max(hits, key=lambda p: len(p.key)).locality if hits else None


def rules_extract(text: str, idx: TraceIndex) -> dict:
    loc = rules_locality(text, idx)
    return dict(language=rules_language(text), locality=loc, issue_type=rules_issue(text) or "other",
                summary=text.strip()[:140], source="rules")


# ----------------------------------------------------------------------------- matching
def _lite(r: pd.Series, score: float | None = None) -> dict:
    return dict(
        complaint_id=r.complaint_id, received_at=str(r.received_at)[:16], channel=r.channel, language=r.language,
        text=str(r.description), locality_text=str(r.locality_text) if pd.notna(r.locality_text) else "",
        ward_code=None if pd.isna(r.ward_code) else r.ward_code, category_reported=r.category_reported,
        status=r.status, upvotes=int(r.upvotes) if pd.notna(r.upvotes) else 0,
        photo_description=str(r.photo_description) if pd.notna(r.photo_description) else "",
        resolved_at=None if pd.isna(r.resolved_at) else str(r.resolved_at)[:16],
        score=None if score is None else round(score, 3),
    )


def _sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sm.ratio() if sm.real_quick_ratio() > 0.4 and sm.quick_ratio() > 0.4 else 0.0


def find_by_id(text: str, idx: TraceIndex) -> tuple[str | None, bool]:
    """(complaint_id, id_was_in_text). The id is returned even if unknown so the caller can say 'not found'."""
    m = ID_RE.search(text)
    if not m:
        return None, False
    cid = m.group(0).upper()
    return cid, cid in idx.complaints.index


def near_exact(text: str, idx: TraceIndex) -> tuple[str | None, float]:
    """The user pasted (nearly) a complaint's own text: exact normalised match, else best similarity >= TEXT_MATCH_MIN."""
    q = norm(text)
    if len(q) < 12:
        return None, 0.0
    exact = idx.complaints[idx.complaints.norm_text == q]
    if len(exact):
        # prefer the original over a closed duplicate when several identical texts exist
        exact = exact.sort_values(by="status", key=lambda s: s.eq("Closed - Duplicate"))
        return exact.index[0], 1.0
    qt = set(q.split())
    cand = idx.complaints
    overlap = cand.norm_text.map(lambda s: len(qt & set(s.split())) / max(len(qt), 1))
    best_id, best = None, 0.0
    for cid in overlap.sort_values(ascending=False).index[:25]:
        s = _sim(q, cand.at[cid, "norm_text"])
        if s > best:
            best_id, best = cid, s
    return (best_id, best) if best >= TEXT_MATCH_MIN else (None, best)


def score_candidates(text: str, geo: dict | None, issue: str | None, idx: TraceIndex, limit: int = 5) -> list[dict]:
    """Rank complaints by locality (0.35), issue type (0.25) and text similarity (0.40)."""
    c = idx.complaints
    q = norm(text)
    if geo:
        loc_keys = {p.key for p in idx.places if p.locality == geo["locality"]}
        same_loc = c.locality_text.map(lambda x: norm(x) in loc_keys if pd.notna(x) else False)
        same_ward = c.ward_code.eq(geo["ward_code"])
        pool = c[same_loc | same_ward]
        loc_score = same_loc[pool.index].map({True: 1.0, False: 0.55})
    else:
        pool = c
        loc_score = pd.Series(0.0, index=pool.index)
    rows = []
    for cid, r in pool.iterrows():
        cat = 1.0 if issue and r.category_reported == issue else 0.4 if r.category_reported in VAGUE else 0.0
        t = _sim(q, r.norm_text)
        rows.append((0.35 * float(loc_score[cid]) + 0.25 * cat + 0.40 * t, cid))
    rows.sort(reverse=True)
    return [_lite(c.loc[cid], s) for s, cid in rows[:limit]]


def decide(cands: list[dict]) -> tuple[str | None, float]:
    """Accept the best candidate only when it is strong AND clearly ahead; otherwise ask the user to confirm."""
    if not cands:
        return None, 0.0
    best = cands[0]["score"]
    second = cands[1]["score"] if len(cands) > 1 else 0.0
    if best >= CONFIDENT and best - second >= MARGIN:
        return cands[0]["complaint_id"], best
    return None, best


# ----------------------------------------------------------------------------- trail
NO_WO_STATUS = {
    "Open": ("open", "No work order yet", "This complaint is still open in the records: no repair has been logged."),
    "In Progress": ("in_progress", "Being worked on", "The complaint is marked In Progress, but no work order has been logged yet."),
    "Forwarded to MMRDA/PWD": ("forwarded", "Forwarded to MMRDA / PWD", "It was forwarded because the road is not BMC's to repair, so BMC has no work order."),
    "Forwarded to SWM dept": ("forwarded", "Forwarded to Solid Waste Management", "It was forwarded to the Solid Waste Management department, so there is no road work order."),
    "Rejected - Not BMC road": ("rejected", "Rejected: not a BMC road", "The complaint was closed because the road does not belong to BMC."),
    "Rejected - Not road issue": ("rejected", "Rejected: not a road issue", "The complaint was closed because it was judged not to be a road issue."),
}


def _step(key, title, status, headline, detail, links=None) -> dict:
    return dict(key=key, title=title, status=status, headline=headline, detail=detail, links=links or [])


def trail(pre, idx: TraceIndex, cid: str) -> dict:
    """Everything deterministic about one complaint: outcome, duplicates, work order, flags, steps."""
    ix = pre.evidence_index
    r = idx.complaints.loc[cid]
    comp = _lite(r)
    geo = geocode(r.locality_text, idx) if pd.notna(r.locality_text) else None
    ward_code = comp["ward_code"] or (geo or {}).get("ward_code")
    ward = idx.wards.get(ward_code, {}) if ward_code else {}
    wo_id = idx.wo_of.get(cid)

    dups: list[dict] = []
    wo = flags = None
    links_wo: list[dict] = []
    outcome, no_wo_head, no_wo_detail = None, "", ""
    if wo_id:
        wrow = ix.wo.loc[wo_id]
        d = ev._wo_detail(ix, wrow)
        rc = ev._rate_check(ix, wrow)
        road = ev._road(ix, wrow.road_id)
        dups = [_lite(idx.complaints.loc[i]) for i in d["linked_complaint_ids"] if i != cid and i in idx.complaints.index]
        wo = dict(
            work_order_id=wo_id, work_type=d["work_type"], repair_method=d["repair_method"],
            contractor_id=d["contractor_id"], contractor_name=d["contractor_name"], assigned_at=d["assigned_at"] or "",
            completed_at=d["completed_at"], cost_inr=d["cost_inr"], expected_inr=rc["expected_inr"], cost_ratio=rc["ratio"],
            within_normal_range=rc["ratio"] <= 1.5, sla_hours=d["sla_hours"], actual_hours=d["actual_hours"],
            sla_met=d["sla_met"], reopened_within_30d=d["reopened_within_30d"], road_id=road["road_id"],
            road_name=road["road_name"], under_dlp=road["under_dlp"] == "Y",
        )
        outcome = "fixed_failed" if wo["reopened_within_30d"] else "fixed_held"
        fl: list[Flag] = [f for f in pre.flags if wo_id in f.work_order_ids]
        flags = [dict(flag_id=f.flag_id, rule=f.rule, tier=f.tier, severity=f.severity, reason=f.reason,
                      amount_inr=f.amount_inr) for f in fl]
    else:
        outcome, no_wo_head, no_wo_detail = NO_WO_STATUS.get(
            r.status, ("open", "No work order", "No work order is linked to this complaint."))
    flags = flags or []

    date = comp["received_at"][:10]
    is_dup = r.status == "Closed - Duplicate"
    s_complaint = _step(
        "complaint", "What did you report?", "done",
        f"Complaint {cid}, received {date} via {comp['channel']}",
        f"“{comp['text']}” Status: {comp['status']}.",
    )
    where = f"{comp['locality_text'] or (geo or {}).get('locality') or 'unknown locality'}" + (f", ward {ward_code}" if ward_code else "")
    s_issue = _step(
        "issue", "What issue is this?", "done",
        f"Reported as {comp['category_reported'].lower()} · {where}",
        ("Closed as a duplicate: the repair was done under the work order below, raised from "
         f"{len(dups) + 1} reports of the same problem." if is_dup and wo else
         f"{len(dups)} other report{'s' if len(dups) != 1 else ''} of the same problem were joined to the same repair."
         if dups else "No other reports were joined to this one."),
        [dict(label=f"Ward {ward_code} report", href=f"/ward/{ward['slug']}")] if ward else [],
    )
    if wo:
        s_wo = _step(
            "work_order", "Was it fixed?", "done",
            f"Yes: work order {wo_id}, {wo['repair_method']}, by {wo['contractor_name']}",
            f"Finished {str(wo['completed_at'] or '')[:10]}. Billed {inr(wo['cost_inr'])} against about "
            f"{inr(wo['expected_inr'])} expected from the rate card ({wo['cost_ratio']:.1f}×"
            f"{'' if wo['within_normal_range'] else ', above the normal range'}). Target time was {wo['sla_hours']:g} h"
            f"{'' if wo['actual_hours'] is None else f', it took {wo['actual_hours']:.0f} h'} "
            f"({'target met' if wo['sla_met'] == 'Y' else 'target missed'}).",
            [dict(label=f"Contractor {wo['contractor_name'].replace(' (synthetic)', '')}", href=f"/contractor/{wo['contractor_id']}")],
        )
        s_held = (_step("held", "Did the fix hold?", "failed", "No: it was reopened within 30 days",
                        "The same problem came back within a month of the repair.")
                  if wo["reopened_within_30d"] else
                  _step("held", "Did the fix hold?", "done", "Yes: it held for 30 days",
                        "No reopening was recorded in the 30 days after the repair."))
        if wo["under_dlp"]:
            s_warr = _step("warranty", "Was the road under warranty?", "failed",
                           f"Yes, and BMC paid {inr(wo['cost_inr'])}",
                           "The road was still under its original contractor's Defect Liability Period, when repairs are "
                           "normally free to the city. Worth checking.")
        else:
            s_warr = _step("warranty", "Was the road under warranty?", "done", "No",
                           "The road was not under its original contractor's warranty, so paying for the repair is normal.")
    else:
        s_wo = _step("work_order", "Was it fixed?", "pending" if outcome in ("open", "in_progress") else "skipped",
                     no_wo_head, no_wo_detail)
        s_held = _step("held", "Did the fix hold?", "skipped", "Not applicable", "There was no repair to check.")
        s_warr = _step("warranty", "Was the road under warranty?", "skipped", "Not applicable", "There was no repair to check.")
    act_links = [dict(label="See the evidence", href=f"/flag/{f['flag_id']}") for f in flags[:3]]
    s_act = _step(
        "action", "What can you do?", "pending",
        "Ask for the records" if flags or wo or outcome != "fixed_held" else "Nothing needed",
        ("This repair is flagged as worth checking; open the evidence, or send the RTI request below."
         if flags else "You can ask the ward office for the records with the RTI request below."),
        act_links,
    )
    return dict(outcome=outcome, complaint=comp, duplicates=dups, work_order=wo, flags=flags,
                steps=[s_complaint, s_issue, s_wo, s_held, s_warr, s_act], geocoded=geo,
                ward_code=ward_code, ward_slug=ward.get("slug"))


def facts(tr: dict) -> dict:
    """The only things Claude may use when writing the answer."""
    wo, c = tr["work_order"], tr["complaint"]
    out = dict(outcome=tr["outcome"], complaint_id=c["complaint_id"], received_on=c["received_at"][:10],
               status=c["status"], issue=c["category_reported"], locality=c["locality_text"],
               ward=tr.get("ward_code"), duplicate_reports_joined=len(tr["duplicates"]))
    if wo:
        out["work_order"] = dict(
            id=wo["work_order_id"], repair_method=wo["repair_method"], contractor=wo["contractor_name"],
            finished_on=str(wo["completed_at"] or "")[:10], billed=inr(wo["cost_inr"]), expected=inr(wo["expected_inr"]),
            billed_vs_expected=f"{wo['cost_ratio']:.1f}×", within_normal_range=wo["within_normal_range"],
            target_hours=round(wo["sla_hours"]), took_hours=None if wo["actual_hours"] is None else round(wo["actual_hours"]),
            target_met=wo["sla_met"] == "Y", reopened_within_30_days=wo["reopened_within_30d"],
            road_under_warranty=wo["under_dlp"])
    if tr["flags"]:
        out["worth_checking"] = [dict(what=f["rule"], reason=f["reason"]) for f in tr["flags"][:3]]
    return out
