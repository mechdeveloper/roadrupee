"""Per-IP rate limit on the live-Claude endpoints, and the friendly fallbacks. No live API calls."""
import asyncio

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import ratelimit
from app.ai import client as ai_client
from app.ai import trace as ai_trace
from app.ai.store import JsonStore
from app.ai.structured import Generated
from app.ai.verdict import template_verdict
from app.main import app


# ------------------------------------------------------------------ the limiter
def test_sliding_window_with_a_fake_clock():
    t = [0.0]
    rl = ratelimit.RateLimiter(limit=3, window=60, clock=lambda: t[0])
    assert [rl.check("a")[0] for _ in range(3)] == [True, True, True]
    ok, wait = rl.check("a")
    assert not ok and 1 <= wait <= 60
    assert rl.check("b")[0]  # another IP is unaffected
    t[0] = 59.0
    assert not rl.check("a")[0]
    t[0] = 60.5  # the first hit has left the window
    assert rl.check("a")[0]


def test_default_is_twenty_per_minute():
    assert ratelimit.LIMIT == 20 and ratelimit.WINDOW == 60.0


def test_memory_is_bounded(monkeypatch):
    monkeypatch.setattr(ratelimit, "MAX_TRACKED", 50)
    rl = ratelimit.RateLimiter(limit=1)
    for i in range(500):
        rl.check(f"ip{i}")
    assert len(rl.hits) <= 51


# ------------------------------------------------------------------ the endpoints
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path, client):
    monkeypatch.setattr(ratelimit, "live", ratelimit.RateLimiter(limit=3))
    monkeypatch.setattr(ai_client, "have_key", lambda: False)
    app.state.trace_store = JsonStore(tmp_path / "trace.json")
    monkeypatch.setattr(app.state.pre, "verdicts", JsonStore(tmp_path / "verdicts.json"))
    yield
    app.state.trace_store = None


def ids(n: int) -> list[str]:
    c = app.state.pre.data.complaints
    return list(c[c.status == "Open"].complaint_id[:n])


def test_trace_is_limited_per_ip_with_a_friendly_message(client):
    for cid in ids(3):
        assert client.post("/api/trace", json={"complaint_id": cid}).status_code == 200
    r = client.post("/api/trace", json={"complaint_id": ids(4)[3]})
    assert r.status_code == 429
    body = r.json()
    assert body["error"] == "rate_limited" and "wait" in body["message"].lower() and body["retry_after"] >= 1
    assert int(r.headers["Retry-After"]) == body["retry_after"]
    # a different client (the proxy sets x-client-ip) has its own allowance
    other = client.post("/api/trace", json={"complaint_id": ids(1)[0]}, headers={"x-client-ip": "203.0.113.9"})
    assert other.status_code == 200


def test_cached_trace_answers_are_free(client, monkeypatch):
    monkeypatch.setattr(ai_client, "have_key", lambda: True)
    monkeypatch.setattr(ai_client, "get_client", lambda: object())

    async def answer(client_, model, facts, lang):
        return Generated(ai_trace.AnswerOut(text="Fixed. You can send the RTI request below."), "claude", model, 0, [])

    monkeypatch.setattr(ai_trace, "answer", answer)
    first, *rest = ids(4)
    assert client.post("/api/trace", json={"complaint_id": first}).json()["cached"] is False
    for _ in range(8):  # eight repeats, limit is 3: all served from cache without counting
        assert client.post("/api/trace", json={"complaint_id": first}).json()["cached"] is True
    assert client.post("/api/trace", json={"complaint_id": rest[0]}).status_code == 200
    assert client.post("/api/trace", json={"complaint_id": rest[1]}).status_code == 200
    assert client.post("/api/trace", json={"complaint_id": rest[2]}).status_code == 429


def _review_flags(n: int) -> list[str]:
    return [f.flag_id for f in app.state.pre.flags if f.tier == "review" and f.review is None][:n]


def test_explain_is_limited_only_when_it_would_call_claude(client, monkeypatch):
    monkeypatch.setattr(ai_client, "have_key", lambda: True)
    monkeypatch.setattr(ai_client, "get_client", lambda: object())

    async def verdict(_client, _model, ev):
        return Generated(template_verdict(ev), "claude", "test", 0, [])

    monkeypatch.setattr(main, "make_verdict", verdict)
    fids = _review_flags(5)
    for fid in fids[:3]:
        assert client.post(f"/api/explain/{fid}").status_code == 200
    again = client.post(f"/api/explain/{fids[0]}").json()
    assert again["cached"] is True  # a stored verdict is free
    r = client.post(f"/api/explain/{fids[3]}")
    assert r.status_code == 429 and "wait" in r.json()["message"].lower()


def test_explain_falls_back_to_the_automatic_summary_when_claude_is_slow(client, monkeypatch):
    monkeypatch.setattr(ai_client, "have_key", lambda: True)
    monkeypatch.setattr(ai_client, "get_client", lambda: object())
    monkeypatch.setattr(main, "EXPLAIN_TIMEOUT", 0.2)

    async def slow(*a, **k):
        await asyncio.sleep(3)

    monkeypatch.setattr(main, "make_verdict", slow)
    r = client.post(f"/api/explain/{_review_flags(1)[0]}")
    assert r.status_code == 200
    d = r.json()
    assert d["review"]["source"] == "template" and d["cached"] is False
