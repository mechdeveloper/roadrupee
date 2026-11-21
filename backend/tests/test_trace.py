"""Trace my complaint: deterministic engine, route behaviour, Claude paths mocked (no live calls)."""
import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai import client as ai_client
from app.ai import trace as ai_trace
from app.ai.guardrail import unverified_numbers
from app.ai.store import JsonStore
from app.ai.structured import Generated
from app.engine import trace as T
from app.main import app
from app.routes import trace as route


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def offline(monkeypatch, client, tmp_path):
    """Default: no Claude, and a throwaway cache so tests never touch data_cache/trace.json."""
    monkeypatch.setattr(ai_client, "have_key", lambda: False)
    app.state.trace_index = None  # rebuilt lazily
    app.state.trace_store = JsonStore(tmp_path / "trace_default.json")
    yield
    app.state.trace_index = None
    app.state.trace_store = None


@pytest.fixture(scope="module")
def idx(client):
    return T.build_index(app.state.pre)


def post(client, **body):
    r = client.post("/api/trace", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def first(idx, status, linked):
    c = idx.complaints
    rows = c[c.status == status]
    rows = rows[rows.complaint_id.map(lambda i: (i in idx.wo_of) == linked)]
    return rows.index[0]


# ------------------------------------------------------------------ outcomes by complaint id
def test_resolved_complaint_trail(client, idx):
    cid = first(idx, "Resolved", True)
    d = post(client, complaint_id=cid)
    wo = app.state.pre.wo.set_index("work_order_id").loc[idx.wo_of[cid]]
    assert d["input_kind"] == "id" and d["match"]["basis"] == "id" and d["match"]["confidence"] == 1.0
    assert d["outcome"] == ("fixed_failed" if wo.reopened else "fixed_held")
    assert d["work_order"]["work_order_id"] == wo.name
    assert d["work_order"]["contractor_id"] == wo.contractor_id
    assert abs(d["work_order"]["cost_inr"] - wo.cost_inr) < 0.01
    assert [s["key"] for s in d["steps"]] == ["complaint", "issue", "work_order", "held", "warranty", "action"]
    assert d["rti"]["en"].count(wo.name) >= 1 and any("ऀ" <= ch <= "ॿ" for ch in d["rti"]["mr"])


def test_duplicates_share_the_original_work_order(client, idx):
    cid = first(idx, "Closed - Duplicate", True)
    d = post(client, complaint_id=cid)
    assert d["outcome"] in ("fixed_held", "fixed_failed")
    assert d["duplicates"] and all(x["complaint_id"] != cid for x in d["duplicates"])
    assert "duplicate" in d["steps"][1]["detail"].lower()


@pytest.mark.parametrize("status,outcome", [
    ("Open", "open"), ("In Progress", "in_progress"), ("Forwarded to MMRDA/PWD", "forwarded"),
    ("Forwarded to SWM dept", "forwarded"), ("Rejected - Not BMC road", "rejected"), ("Rejected - Not road issue", "rejected"),
])
def test_no_work_order_outcomes(client, idx, status, outcome):
    d = post(client, complaint_id=first(idx, status, False))
    assert d["outcome"] == outcome and d["work_order"] is None
    assert d["steps"][3]["status"] == "skipped"
    assert d["rti"]["en"] and d["answer"]["source"] == "template"


def test_unknown_id_is_not_found(client):
    d = post(client, complaint_id="BMC25-999999")
    assert d["outcome"] == "not_found" and d["complaint"] is None


def test_empty_request_rejected(client):
    assert client.post("/api/trace", json={}).status_code == 422


# ------------------------------------------------------------------ text matching
def test_pasted_complaint_text_matches_exactly(client, idx):
    c = idx.complaints
    unique = c[~c.norm_text.duplicated(keep=False) & (c.status == "Resolved")].iloc[0]
    d = post(client, text=unique.description)
    assert d["match"]["basis"] == "text-match" and d["complaint"]["complaint_id"] == unique.complaint_id


def test_id_inside_a_sentence(client, idx):
    cid = first(idx, "Open", False)
    d = post(client, text=f"please tell me what happened to {cid.lower()} thanks")
    assert d["complaint"]["complaint_id"] == cid


def test_paraphrase_never_guesses_wildly(client, idx):
    d = post(client, text="Madanpura mein paani bhara hai")
    assert d["extraction"]["source"] == "rules" and d["extraction"]["language"] == "hi-en"
    assert d["extraction"]["geocoded"]["locality"] == "Madanpura"
    assert d["outcome"] in ("needs_confirmation", "open", "in_progress", "forwarded", "rejected", "fixed_held", "fixed_failed")
    if d["outcome"] == "needs_confirmation":
        alts = d["match"]["alternatives"]
        assert 1 <= len(alts) <= 5 and all(a["score"] is not None for a in alts)
        assert [a["score"] for a in alts] == sorted((a["score"] for a in alts), reverse=True)


def test_text_with_nothing_findable(client):
    d = post(client, text="hello there")
    assert d["outcome"] == "not_found"


# ------------------------------------------------------------------ geocoding
@pytest.mark.parametrize("q,locality,how", [
    ("Byculla", "Byculla", "exact"),
    ("भायखळा", "Byculla", "alias"),
    ("Andheri West station road", "Andheri West", "contained"),
    ("Vile", None, "prefix"),
])
def test_geocode(idx, q, locality, how):
    g = T.geocode(q, idx)
    assert g and g["match"] == how
    assert (g["locality"] == locality) if locality else g["locality"].startswith("Vile")


def test_geocode_tokens_for_truncated_names(idx):
    g = T.geocode_tokens("dahisar ke paas road pe khadda hai bahut bada", idx)
    assert g and g["locality"].startswith("Dahisar")
    # short common words must never turn into places
    assert T.geocode_tokens("road pe khadda hai bus band", idx) is None


def test_geocode_fuzzy_and_miss(idx):
    assert T.geocode("Byculaa", idx)["locality"] == "Byculla"
    assert T.geocode("Atlantis", idx) is None
    assert T.geocode("", idx) is None


# ------------------------------------------------------------------ rule-based extraction
@pytest.mark.parametrize("text,lang", [
    ("Madanpura मध्ये पाणी साचले आहे, गाड्या अडकल्या आहेत. पंप पाठवा.", "mr"),
    ("Elphinstone में पानी भर गया है, एम्बुलेंस नहीं निकल पा रही.", "hi"),
    ("Mulund West station road pe itna paani hai ki bus band hai. BMC kab aayegi?", "hi-en"),
    ("Paver blocks uprooted on footpath near signal, Bandra East.", "en"),
])
def test_rules_language(text, lang):
    assert T.rules_language(text) == lang


@pytest.mark.parametrize("text,issue", [
    ("paani bhar gaya hai road pe", "Waterlogging"), ("bada khadda hai", "Pothole"), ("खड्डा पडला आहे", "Pothole"),
    ("manhole cover missing", "Open or broken manhole"), ("nullah overflow near market", "Choked drain / nullah overflow"),
    ("road has caved in", None), ("pavers broken on the footpath", "Broken paver blocks"),
])
def test_rules_issue(text, issue):
    assert T.rules_issue(text) == issue


# ------------------------------------------------------------------ Claude paths (mocked)
def _fake_claude(monkeypatch, tmp_path: Path, answer_text: str):
    monkeypatch.setattr(ai_client, "have_key", lambda: True)
    monkeypatch.setattr(ai_client, "get_client", lambda: object())

    async def extract(client, model, text, localities):
        return ai_trace.ExtractOut(language="mr", locality="Madanpura", issue_type="Waterlogging", summary="water on road")

    async def answer(client, model, facts, lang):
        return Generated(ai_trace.AnswerOut(text=answer_text), "claude", model, 0, [])

    monkeypatch.setattr(ai_trace, "extract", extract)
    monkeypatch.setattr(ai_trace, "answer", answer)
    app.state.trace_store = JsonStore(tmp_path / "trace.json")


def test_claude_answer_is_used_and_cached(client, idx, monkeypatch, tmp_path):
    _fake_claude(monkeypatch, tmp_path, "Your complaint was fixed. You can send the RTI request below.")
    cid = first(idx, "Resolved", True)
    d1 = post(client, complaint_id=cid)
    assert d1["answer"]["source"] == "claude" and d1["cached"] is False
    d2 = post(client, complaint_id=cid)
    assert d2["cached"] is True and d2["answer"]["text"] == d1["answer"]["text"]


def test_claude_extraction_feeds_the_matcher(client, monkeypatch, tmp_path):
    _fake_claude(monkeypatch, tmp_path, "ok ok.")
    d = post(client, text="मदनपुरा येथे रस्त्यावर पाणी साचले आहे कृपया लक्ष द्या")
    assert d["extraction"]["source"] == "claude" and d["extraction"]["geocoded"]["locality"] == "Madanpura"
    assert d["extraction"]["issue_type"] == "Waterlogging"


def test_deadline_falls_back_to_the_deterministic_trail(client, idx, monkeypatch, tmp_path):
    _fake_claude(monkeypatch, tmp_path, "unused")

    async def slow_answer(*a, **k):
        await asyncio.sleep(5)

    monkeypatch.setattr(ai_trace, "answer", slow_answer)
    monkeypatch.setattr(route, "DEADLINE", 0.3)
    d = post(client, complaint_id=first(idx, "Resolved", True))
    assert d["answer"]["source"] == "template" and d["work_order"] is not None
    assert d["cached"] is False


def test_answer_failure_never_breaks_the_trail(client, idx, monkeypatch, tmp_path):
    _fake_claude(monkeypatch, tmp_path, "unused")

    async def boom(*a, **k):
        raise RuntimeError("api down")

    monkeypatch.setattr(ai_trace, "answer", boom)
    d = post(client, complaint_id=first(idx, "Resolved", True))
    assert d["answer"]["source"] == "template" and d["steps"]


# ------------------------------------------------------------------ guardrail on the fallback answer
def test_template_answer_uses_only_numbers_from_the_trail(idx):
    pre = app.state.pre
    for status, linked in (("Resolved", True), ("Open", False)):
        tr = T.trail(pre, idx, first(idx, status, linked))
        f = T.facts(tr)
        assert unverified_numbers([ai_trace.template_answer(f).text], f) == []
