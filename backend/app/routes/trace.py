"""POST /api/trace: Trace my complaint. Orchestrates the deterministic engine and the Claude steps."""
from __future__ import annotations

import asyncio
import hashlib
import logging

from fastapi import APIRouter, HTTPException, Request

from .. import ratelimit
from ..ai import client as ai_client
from ..ai import trace as ai_trace
from ..ai.store import trace_store
from ..contracts.trace import TraceRequest, TraceResponse
from ..engine import rti
from ..engine import trace as T

log = logging.getLogger("roadrupee.trace")
router = APIRouter(prefix="/api")

VERSION = "1"  # bump to invalidate cached traces
DEADLINE = 30.0  # seconds for the whole request
EXTRACT_TIMEOUT = 14.0
ANSWER_TIMEOUT = 14.0

MESSAGES = {
    "not_found": {
        "en": "I couldn't find a complaint that matches this. Try the complaint ID (like BMC25-000123), or add the locality and what the problem was.",
        "hi": "इससे मेल खाती कोई शिकायत नहीं मिली। शिकायत नंबर (जैसे BMC25-000123) डालें, या इलाका और समस्या लिखें।",
        "mr": "यांच्याशी जुळणारी तक्रार सापडली नाही. तक्रार क्रमांक (उदा. BMC25-000123) टाका, किंवा परिसर आणि समस्या लिहा.",
        "hi-en": "Isse match karti koi shikayat nahi mili. Complaint ID (jaise BMC25-000123) daalein, ya ilaka aur samasya likhein.",
    },
    "needs_confirmation": {
        "en": "I found a few complaints that could be yours, but none clearly stands out. Pick the one that matches, and I'll show what happened to it.",
        "hi": "कुछ शिकायतें आपकी हो सकती हैं, पर कोई साफ़ तौर पर अलग नहीं दिखती। जो मेल खाती हो उसे चुनें, मैं दिखाऊँगा कि उसका क्या हुआ।",
        "mr": "काही तक्रारी तुमच्या असू शकतात, पण कोणतीही ठळकपणे वेगळी दिसत नाही. जी जुळते ती निवडा, तिचे काय झाले ते मी दाखवतो.",
        "hi-en": "Kuch shikayatein aapki ho sakti hain, par koi saaf alag nahi dikhti. Jo match kare use chunein, main dikhaunga uska kya hua.",
    },
}


def _state(request: Request):
    st = request.app.state
    if getattr(st, "trace_index", None) is None:
        st.trace_index = T.build_index(st.pre)
    if getattr(st, "trace_store", None) is None:
        st.trace_store = trace_store()
    return st.pre, st.trace_index, st.trace_store


def _from_complaint(comp: dict, idx: T.TraceIndex, source: str) -> dict:
    geo = T.geocode(comp["locality_text"], idx) if comp["locality_text"] else None
    return dict(language=comp["language"], locality=(geo or {}).get("locality"), geocoded=geo,
                issue_type=comp["category_reported"], summary=comp["text"][:140], source=source)


def _bare(kind: str, outcome: str, ext: dict, basis: str, conf: float, alts: list[dict] | None = None) -> dict:
    lang = ext["language"]
    return dict(outcome=outcome, input_kind=kind, complaint=None, duplicates=[], extraction=ext,
                match=dict(confidence=conf, basis=basis, alternatives=alts or []), work_order=None, flags=[], steps=[],
                answer=dict(text=MESSAGES[outcome][lang], language=lang, source="template"), rti=None)


async def _run(pre, idx: T.TraceIndex, text: str, use_ai: bool) -> dict:
    ai = use_ai and ai_client.have_key()
    client = ai_client.get_client() if ai else None
    cid, id_known = T.find_by_id(text, idx)
    kind = "id" if cid else "text"
    conf, basis = 1.0, "id"

    if cid and not id_known:
        return _bare("id", "not_found", dict(language=T.rules_language(text), locality=None, geocoded=None,
                                            issue_type="other", summary=text[:140], source="rules"), "none", 0.0)
    ext: dict | None = None
    if not cid:
        near, sim = T.near_exact(text, idx)
        if near:
            cid, conf, basis = near, sim, "text-match"
        else:
            if client:
                try:
                    out = await asyncio.wait_for(
                        ai_trace.extract(client, ai_client.model_extract(), text, sorted({p.locality for p in idx.places})),
                        EXTRACT_TIMEOUT)
                    ext = dict(out.model_dump(), source="claude")
                except Exception as e:  # noqa: BLE001 - any failure falls back to rules
                    log.warning("extraction fell back to rules: %r", e)
            ext = ext or T.rules_extract(text, idx)
            geo = T.geocode(ext["locality"], idx)
            if not geo:  # no locality from extraction: try the gazetteer on the raw text, then its words
                geo = T.geocode(T.rules_locality(text, idx), idx) or T.geocode_tokens(text, idx)
            ext["geocoded"] = geo
            if geo:
                ext["locality"] = geo["locality"]
            issue = None if ext["issue_type"] == "other" else ext["issue_type"]
            if not geo and not issue:
                return _bare("text", "not_found", ext, "none", 0.0)
            cands = T.score_candidates(text, geo, issue, idx)
            cid, conf = T.decide(cands)
            basis = "locality+issue+text"
            if not cid:
                return _bare("text", "needs_confirmation", ext, basis, conf, cands)

    tr = T.trail(pre, idx, cid)
    ext = ext or _from_complaint(tr["complaint"], idx, "id" if basis == "id" else "text-match")
    lang = ext["language"]
    facts = T.facts(tr)
    ans = ai_trace.template_answer(facts)
    src = "template"
    if client:
        try:
            g = await asyncio.wait_for(ai_trace.answer(client, ai_client.model_live(), facts, lang), ANSWER_TIMEOUT)
            ans, src = g.value, g.source
        except Exception as e:  # noqa: BLE001
            log.warning("answer fell back to template: %r", e)
    return dict(
        outcome=tr["outcome"], input_kind=kind, complaint=tr["complaint"], duplicates=tr["duplicates"], extraction=ext,
        match=dict(confidence=round(conf, 3), basis=basis, alternatives=[]), work_order=tr["work_order"],
        flags=tr["flags"], steps=tr["steps"], answer=dict(text=ans.text, language=lang, source=src), rti=rti.build(tr),
    )


@router.post("/trace", response_model=TraceResponse)
async def trace(request: Request, req: TraceRequest):
    text = (req.complaint_id or req.text or "").strip()
    if not text:
        raise HTTPException(422, "Send `text` or `complaint_id`.")
    pre, idx, store = _state(request)
    key = "t:" + T.norm(text)[:200]
    h = hashlib.sha256(f"{VERSION}|{T.norm(text)}".encode()).hexdigest()[:16]
    hit = store.get(key, h)
    if hit:
        return {**hit["response"], "cached": True}
    ok, wait = ratelimit.live.check(ratelimit.client_ip(request))  # cache hits above are free
    if not ok:
        return ratelimit.too_many(wait)
    try:
        res = await asyncio.wait_for(_run(pre, idx, text, use_ai=True), DEADLINE)
    except asyncio.TimeoutError:
        log.warning("trace deadline hit, answering from the deterministic trail")
        res = await _run(pre, idx, text, use_ai=False)
    if res["answer"]["source"] == "claude":  # never cache the offline template fallback
        store.put(key, {"input_hash": h, "response": res})
        store.save()
    return res
