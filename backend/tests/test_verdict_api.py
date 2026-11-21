"""Verdict columns, flag review and POST /api/explain (no live API calls)."""
import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.ai import client as ai_client
from app.main import app

OLD_COLUMNS = ["work_order_id", "rule", "tier", "severity", "reason", "related_work_order_ids",
               "ward_code", "road_id", "contractor_id", "cost_inr", "expected_inr", "amount_inr"]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import os
    os.environ["VERDICTS_PATH"] = str(tmp_path_factory.mktemp("v") / "verdicts.json")
    with TestClient(app) as c:
        yield c


def test_csv_columns_work_order_first_and_existing_unchanged(client):
    r = client.get("/api/flags.csv")
    header = next(csv.reader(io.StringIO(r.text)))
    assert header[0] == "work_order_id"
    assert header[:len(OLD_COLUMNS)] == OLD_COLUMNS
    assert header[-2:] == ["claude_verdict", "claude_headline"]


def test_flags_items_have_verdict_keys(client):
    item = client.get("/api/flags?limit=1").json()["items"][0]
    assert "claude_verdict" in item and "claude_headline" in item
    assert {"rule", "tier", "reason"} <= item.keys()


def test_explain_without_key_returns_uncached_template(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fid = client.get("/api/flags?rule=OVER_RATE&limit=1").json()["items"][0]["flag_id"]
    r = client.post(f"/api/explain/{fid}").json()
    assert r["review"]["source"] == "template" and r["cached"] is False
    f = client.get(f"/api/flags/{fid}").json()
    assert f["rule"] == "OVER_RATE" and f["tier"] == "audit" and f["review"] is None


def test_explain_caches_after_first_call(client, monkeypatch):
    from app import main
    from app.ai.structured import Generated
    from app.ai.verdict import template_verdict

    calls = []

    async def fake(_c, _m, ev):
        calls.append(1)
        return Generated(template_verdict(ev), "claude", "fake-model", 0, [])

    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(main, "make_verdict", fake)
    monkeypatch.setattr(ai_client, "get_client", lambda: None)
    fid = client.get("/api/flags?tier=review&rule=SLA_BREACH&limit=1").json()["items"][0]["flag_id"]
    a = client.post(f"/api/explain/{fid}").json()
    b = client.post(f"/api/explain/{fid}").json()
    assert (a["cached"], b["cached"], len(calls)) == (False, True, 1)
    d = client.get(f"/api/flags/{fid}").json()
    assert d["review"]["verdict"] == d["claude_verdict"] and d["claude_headline"]
    assert d["tier"] == "review" and d["rule"] == "SLA_BREACH"
    ev = client.get(f"/api/flags/{fid}/evidence").json()
    assert ev["claude_review"]["verdict"] == d["claude_verdict"]


def test_explain_unknown_flag(client):
    assert client.post("/api/explain/F9999").status_code == 404


def test_committed_verdicts_are_valid_and_fair():
    from app.ai.store import verdict_store
    from app.ai.verdict import BANNED, VerdictOut

    for k, e in verdict_store().items.items():
        v = VerdictOut(**{f: e[f] for f in VerdictOut.model_fields})
        assert not any(b in (v.headline + v.reasoning).lower() for b in BANNED), k


def test_flags_csv_is_audit_tier_only_and_flags_all_has_every_tier(client):
    rows = list(csv.DictReader(io.StringIO(client.get("/api/flags.csv").text)))
    assert len(rows) == 391 and {r["tier"] for r in rows} == {"audit"}
    allrows = list(csv.DictReader(io.StringIO(client.get("/api/flags_all.csv").text)))
    assert len(allrows) > 1000 and {"audit", "review"} <= {r["tier"] for r in allrows}

