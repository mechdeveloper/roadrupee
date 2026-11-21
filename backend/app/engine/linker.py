"""Connect the trail: complaint -> issue type -> ward -> road segment.

Deterministic. Issue type is read in order of reliability, measured against the
complaints a work order later fixed (ground truth):
  photo description  -> 100% when it names an issue
  helpline operator note ("Caller reports <category> at ...") -> 100%
  category the citizen picked -> ~88%
  keywords in the free text (EN / Hinglish / Hindi / Marathi) -> ~80%
Combined: ~95% vs 83.5% for the citizen-picked category alone (see accuracy()).
"""
from __future__ import annotations

import math
import re

import pandas as pd

from ..loader import Data

ISSUE_TYPES = [
    "Road cave-in", "Open or broken manhole", "Choked drain / nullah overflow",
    "Broken paver blocks", "Waterlogging", "Pothole",
]
# checked in this order; first match wins
KEYWORDS: list[tuple[str, str]] = [
    ("Road cave-in", r"cave|caved|sinkhole|collapsed|dhans|dhas|धंस|धस|खचल"),
    ("Open or broken manhole", r"manhole|dhakkan|dhakan|ढक्कन|झाकण|मैनहोल|chamber"),
    ("Choked drain / nullah overflow", r"nullah|nala|nalla|drain|gutter|नाला|नाले|गटार|overflow"),
    ("Broken paver blocks", r"paver|block|पेव्हर|पेवर"),
    ("Waterlogging", r"waterlog|water ?logged|flood|knee|ghutne|paani|pani|पानी|पाणी|submerged|pump"),
    ("Pothole", r"pothole|pot hole|gadda|gaddha|khadda|crater|खड्ड|गड्ढ|गड्डा|uneven"),
]
HELPLINE_RE = re.compile(r"(?:reports|states|informs|caller)\s+(.+?)\s+at\s", re.I)
URGENT_RE = re.compile(r"hospital|school|ambulance|accident|fell|girne|gir gaya|gir jayega|dangerous|khatarnak|"
                       r"खतरनाक|धोकादायक|injur|kids|bachche|urgent|knee|ghutne", re.I)
OPEN_STATUSES = ("Open", "In Progress")


def keyword_type(text) -> str | None:
    t = str(text).lower()
    if t in ("", "nan", "none"):
        return None
    for issue, rx in KEYWORDS:
        if re.search(rx, t):
            return issue
    return None


def classify(description, photo_description=None, channel=None, category=None) -> tuple[str, str]:
    """Return (issue_type, source). source says which signal decided it."""
    p = keyword_type(photo_description)
    if p:
        return p, "photo"
    if channel == "1916 Helpline":
        m = HELPLINE_RE.search(str(description))
        if m:
            cand = next((k for k in ISSUE_TYPES if k.lower() == m.group(1).strip().lower()), None)
            if cand:
                return cand, "helpline note"
    if category in ISSUE_TYPES:
        return category, "category"
    d = keyword_type(description)
    return (d, "text") if d else ("Unclear", "none")


def detect_language(text: str) -> str:
    t = str(text)
    if re.search(r"[ऀ-ॿ]", t):
        return "mr" if re.search(r"आहे|वर |खड्डे|झाकण|रस्त्यावर|पाणी|दुरुस्त करा|उघडे", t) else "hi"
    if re.search(r"\b(ke|ka|ki|hai|pe|mein|paas|nahi|bahut|kab|karo|gadda|khadda|paani)\b", t.lower()):
        return "hi-en"
    return "en"


class Gazetteer:
    """Locality names + aliases (incl. Devanagari) -> (lat, lon, ward)."""

    def __init__(self, localities: pd.DataFrame):
        self.alias: dict[str, tuple[float, float, str, str]] = {}
        for r in localities.itertuples():
            names = [r.locality] + (str(r.aliases).split(";") if pd.notna(r.aliases) else [])
            for a in names:
                a = a.strip().lower()
                if a:
                    self.alias[a] = (float(r.lat), float(r.lon), r.ward_code, r.locality)
        self._keys = sorted(self.alias, key=len, reverse=True)

    def find(self, *texts) -> tuple[float, float, str, str] | None:
        for s in texts:
            s = str(s).lower().strip()
            if not s or s == "nan":
                continue
            if s in self.alias:
                return self.alias[s]
            for k in self._keys:
                if len(k) > 3 and k in s:
                    return self.alias[k]
        return None


def seg_dist_m(lat: float, lon: float, r) -> float:
    """Distance in metres from a point to a road segment (equirectangular, fine at city scale)."""
    k = 111320.0
    c = math.cos(math.radians(lat))
    ax, ay = (r.start_lon - lon) * k * c, (r.start_lat - lat) * k
    bx, by = (r.end_lon - lon) * k * c, (r.end_lat - lat) * k
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy + 1e-9)))
    return math.hypot(ax + t * dx, ay + t * dy)


def match_road(roads: pd.DataFrame, text, ward, lat, lon) -> tuple[str | None, str]:
    """Road named in the text (within the ward) beats nearest segment. Returns (road_id, how)."""
    t = str(text).lower()
    cand = roads[roads.ward_code == ward] if isinstance(ward, str) and ward else roads
    named = cand[cand.road_name.str.lower().map(lambda n: n in t)]
    has_xy = lat is not None and not pd.isna(lat)
    if len(named) and has_xy:
        return min(named.itertuples(), key=lambda r: seg_dist_m(lat, lon, r)).road_id, "road name + location"
    if len(named):
        return named.iloc[0].road_id, "road name"
    if has_xy and len(cand):
        return min(cand.itertuples(), key=lambda r: seg_dist_m(lat, lon, r)).road_id, "nearest road"
    return None, "none"


def complaint_to_wo(wo: pd.DataFrame) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in wo.loc[wo.linked_complaint_ids.ne(""), ["work_order_id", "linked_complaint_ids"]].itertuples():
        for cid in r.linked_complaint_ids.split("|"):
            out[cid] = r.work_order_id
    return out


def enrich_complaints(data: Data) -> pd.DataFrame:
    """Every complaint with issue_type, type_source, geocoded ward/lat/lon and work_order_id."""
    c = data.complaints.copy()
    typed = [classify(r.description, r.photo_description, r.channel, r.category_reported) for r in c.itertuples()]
    c["issue_type"] = [t for t, _ in typed]
    c["type_source"] = [s for _, s in typed]
    gaz = Gazetteer(data.localities)
    lat, lon, ward, how = [], [], [], []
    for r in c.itertuples():
        if pd.notna(r.lat):
            lat.append(r.lat); lon.append(r.lon); ward.append(r.ward_code); how.append("gps")
            continue
        g = gaz.find(r.locality_text, r.description)
        if g:
            lat.append(g[0]); lon.append(g[1]); ward.append(r.ward_code if pd.notna(r.ward_code) else g[2]); how.append("locality")
        else:
            lat.append(None); lon.append(None); ward.append(r.ward_code if pd.notna(r.ward_code) else None); how.append("none")
    c["g_lat"], c["g_lon"], c["g_ward"], c["geo_source"] = lat, lon, ward, how
    c["work_order_id"] = c.complaint_id.map(complaint_to_wo(data.wo))
    c["urgent"] = c.description.fillna("").str.contains(URGENT_RE)
    return c


def link_open(data: Data, comp: pd.DataFrame) -> pd.DataFrame:
    """Open / in-progress complaints matched to a road segment."""
    o = comp[comp.status.isin(OPEN_STATUSES)].copy()
    res = [match_road(data.roads, r.description, r.g_ward, r.g_lat, r.g_lon) for r in o.itertuples()]
    o["road_id"] = [r for r, _ in res]
    o["road_match"] = [h for _, h in res]
    return o


def accuracy(data: Data, comp: pd.DataFrame, sample: int = 1500) -> dict:
    """Score the linker on complaints a work order fixed (their WO gives true type, ward and road)."""
    wo = data.wo.set_index("work_order_id")
    t = comp[comp.work_order_id.notna()].copy()
    t["t_type"] = t.work_order_id.map(wo.work_type)
    t["t_ward"] = t.work_order_id.map(wo.ward_code)
    t["t_road"] = t.work_order_id.map(wo.road_id)
    s = t.sample(min(sample, len(t)), random_state=0)
    pred = [match_road(data.roads, r.description, r.g_ward, r.g_lat, r.g_lon)[0] for r in s.itertuples()]
    return {
        "checked": int(len(t)),
        "issue_type_pct": round(float((t.issue_type == t.t_type).mean() * 100), 1),
        "citizen_category_pct": round(float((t.category_reported == t.t_type).mean() * 100), 1),
        "ward_pct": round(float((t.g_ward == t.t_ward).mean() * 100), 1),
        "road_segment_pct": round(float((pd.Series(pred, index=s.index) == s.t_road).mean() * 100), 1),
        "road_sample": int(len(s)),
    }
