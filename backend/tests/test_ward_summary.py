"""Ward summaries: facts, guardrail and API exposure (fake client, no live calls)."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import cache
from app.ai import ward_summary as W
from app.ai.guardrail import unverified_numbers
from app.main import app


@pytest.fixture(scope="module")
def pre():
    return cache.build()


def good(f):
    c, t = f["top_contractor"], f["top_flag"]
    return W.WardSummaryOut(
        en=f"The ward spent {f['spend_text']}, mostly with {c['name']}. {f['reopen_observed_pct']}% of repairs reopened "
           f"against about {f['reopen_expected_pct']}% expected. Work order {t['work_order_id']} is worth checking.",
        hi=f"वार्ड ने {f['spend_text']} खर्च किए, ज़्यादातर {c['name']} को। {f['reopen_observed_pct']}% मरम्मत दोबारा खुली, "
           f"अपेक्षा लगभग {f['reopen_expected_pct']}% थी। वर्क ऑर्डर {t['work_order_id']} जाँचने लायक है।",
        mr=f"वॉर्डने {f['spend_text']} खर्च केले, बहुतेक {c['name']} यांना। {f['reopen_observed_pct']}% दुरुस्त्या पुन्हा उघडल्या, "
           f"अपेक्षा सुमारे {f['reopen_expected_pct']}% होती। वर्क ऑर्डर {t['work_order_id']} तपासण्यासारखा आहे।")


class Fake:
    def __init__(self, outs):
        self.outs = list(outs)
        self.messages = SimpleNamespace(parse=self.parse)

    async def parse(self, **kw):
        return SimpleNamespace(parsed_output=self.outs.pop(0), stop_reason="end_turn")


def test_facts_and_good_summary_pass(pre):
    w = next(x for x in pre.wards if x["slug"] == "g-s")
    f = W.facts(pre, w, pre.flags)
    g = asyncio.run(W.make_summary(Fake([good(f)]), "m", f))
    assert g.source == "claude" and g.guardrail_retries == 0


def test_invented_number_rejected_then_template(pre):
    w = next(x for x in pre.wards if x["slug"] == "g-s")
    f = W.facts(pre, w, pre.flags)
    bad = good(f)
    bad.en = bad.en.replace("worth checking", "worth checking, with ₹99 Cr at stake")
    g = asyncio.run(W.make_summary(Fake([bad, bad]), "m", f))
    assert g.source == "template"
    assert unverified_numbers([g.value.en], f) == []


def test_every_ward_has_facts_and_template_is_clean(pre):
    for w in pre.wards:
        f = W.facts(pre, w, pre.flags)
        assert unverified_numbers([W.template_summary(f).en], f) == [], w["slug"]


def test_ai_summary_exposed_when_cached(monkeypatch, tmp_path):
    import json
    pre = cache.build()
    w = next(x for x in pre.wards if x["slug"] == "g-s")
    f = W.facts(pre, w, pre.flags)
    g = asyncio.run(W.make_summary(Fake([good(f)]), "fake", f))
    p = tmp_path / "ws.json"
    p.write_text(json.dumps({"g-s": W.to_entry(f, g)}))
    monkeypatch.setenv("WARD_SUMMARIES_PATH", str(p))
    with TestClient(app) as c:
        assert set(c.get("/api/wards/g-s").json()["ai_summary"]) == {"en", "hi", "mr"}
        by = {x["slug"]: x for x in c.get("/api/wards").json()}
        assert by["g-s"]["ai_summary"] and "ai_summary" not in by["a"]
