"""Guardrail + generate_checked with a fake client (no live API calls)."""
import asyncio
from types import SimpleNamespace

import pytest

from app.ai import verdict as V
from app.ai.guardrail import unverified_numbers
from app.ai.structured import generate_checked

EV = {"claim": "Billed ₹2,35,386 vs about ₹1,00,000 expected (2.4×). Normal variation is ±30%.",
      "rate_check": {"ratio": 2.35, "billed_inr": 235386.0, "expected_inr": 100000.0, "normal_range_pct": [20, 30]},
      "contractor": {"reopen_observed_pct": 37.6}}


def test_rejects_invented_rupee_amount():
    assert unverified_numbers(["Billed ₹9,99,999 for the job."], EV) == ["₹9,99,999"]


def test_rejects_invented_percent_and_multiplier():
    assert unverified_numbers(["About 55% reopened."], EV) == ["55%"]
    assert unverified_numbers(["That is 7.5× the rate."], EV) == ["7.5×"]


def test_accepts_numbers_in_evidence_in_any_form():
    ok = ["Billed ₹2,35,386 against ₹1,00,000.", "That is ₹2.4 L billed, ₹1 L expected.",
          "37.6% reopened; normal is ±30%.", "About 2.35× the rate card."]
    assert unverified_numbers(ok, EV) == []


class FakeClient:
    """Returns queued VerdictOut objects from messages.parse."""
    def __init__(self, outs):
        self.outs, self.calls = list(outs), 0
        self.messages = SimpleNamespace(parse=self.parse)

    async def parse(self, **kw):
        self.calls += 1
        return SimpleNamespace(parsed_output=self.outs.pop(0), stop_reason="end_turn")


def vo(text):
    return V.VerdictOut(verdict="worth_checking", headline="Billed well above the rate card.",
                        reasoning=f"{text} It is worth checking. The remark gives no reason.",
                        context_considered=["rate card"], evidence_refs=["rate_check.ratio"])


def run(client):
    ev = {"rule": "OVER_RATE", "tier": "audit", "work_order_ids": ["WO25-1"], "context": {}, **EV}
    return asyncio.run(V.make_verdict(client, "m", ev))


def test_invented_number_then_clean_retry():
    c = FakeClient([vo("Billed ₹9,99,999."), vo("Billed ₹2,35,386.")])
    g = run(c)
    assert (g.source, g.guardrail_retries, c.calls) == ("claude", 1, 2)


def test_invented_twice_falls_back_to_template():
    c = FakeClient([vo("Billed ₹9,99,999."), vo("Reopened 55% of the time.")])
    g = run(c)
    assert g.source == "template" and c.calls == 2
    assert g.value.verdict == "worth_checking"
    assert unverified_numbers(V.verdict_texts(g.value), {**EV}) == []


def test_banned_word_rejected():
    bad = vo("Billed ₹2,35,386.")
    bad.reasoning = "This looks like fraud. Please act."
    g = run(FakeClient([bad, bad]))
    assert g.source == "template"


def test_refusal_goes_to_template():
    class R(FakeClient):
        async def parse(self, **kw):
            return SimpleNamespace(parsed_output=None, stop_reason="refusal")
    assert run(R([])).source == "template"


def test_verdict_never_changes_rule_or_tier():
    ev = {"rule": "OVER_RATE", "tier": "audit", "work_order_ids": ["WO25-1"], "context": {}, **EV}
    before = dict(ev)
    asyncio.run(V.make_verdict(FakeClient([vo("Billed ₹2,35,386.")]), "m", ev))
    assert ev == before
