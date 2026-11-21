"""Claude's opinion on one flag, from the evidence JSON only. Never changes the rule result or tier."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

from ..engine.evidence import evidence_hash
from ..engine.flags import inr
from .structured import Generated, generate_checked

BANNED = ("fraud", "scam", "corrupt", "steal", "stole", "theft", "bribe", "criminal")
MAX_HEADLINE_WORDS = 20


class VerdictOut(BaseModel):
    verdict: Literal["worth_checking", "likely_justified", "needs_more_info"]
    headline: str
    reasoning: str
    context_considered: list[str]
    evidence_refs: list[str]


SYSTEM = """You are a fair civic auditor helping a ward officer in Mumbai review one flagged road-repair work order.
A deterministic rule engine has already flagged it. Its rule result and tier are fixed; you give a separate opinion and never change them.

You get one JSON evidence pack. Rules:
- Use only numbers that appear in the evidence. Write rupee amounts, percentages and multipliers exactly as the evidence supports. Do no new arithmetic. If a number is not in the evidence, leave it out.
- Before concluding, weigh anything that could justify the cost or delay: heavy rain or red/orange IMD alerts around completion, big tides, flood hotspots, a high low-lying index, a utility-trench remark, linked complaints with many upvotes, a long reopen history of the same method, how the contractor's reopen rate compares with the rate expected for its work. Also say when rain data is missing (it ends on 30 Sep).
- Be fair and plain. Say "worth checking", never fraud, scam, corrupt, theft or any accusation. Small samples are not blamed.
- verdict: "worth_checking" = the evidence does not explain it; "likely_justified" = context plausibly explains it; "needs_more_info" = the evidence cannot settle it.
- headline: one plain sentence a citizen can read, at most 20 words.
- reasoning: 2 to 4 sentences.
- context_considered: short factors you weighed, e.g. "heavy rain that week", "utility trench remark".
- evidence_refs: the evidence field names or work_order_ids you relied on (e.g. "rate_check.ratio", "WO25-00004").
All data is synthetic and all contractors are fictional."""


def _problems(v: VerdictOut) -> list[str]:
    out = []
    if len(v.headline.split()) > MAX_HEADLINE_WORDS:
        out.append(f"headline longer than {MAX_HEADLINE_WORDS} words")
    text = " ".join([v.headline, v.reasoning, *v.context_considered]).lower()
    out += [f"banned word: {b}" for b in BANNED if b in text]
    if not 2 <= v.reasoning.count(".") + v.reasoning.count("!") + v.reasoning.count("?") <= 5:
        out.append("reasoning should be 2 to 4 sentences")
    if not v.evidence_refs:
        out.append("evidence_refs is empty")
    return out


def template_verdict(ev: dict) -> VerdictOut:
    """Deterministic fallback built only from evidence values."""
    rule, ctx = ev["rule"], ev["context"]
    wid = ev["work_order_ids"][0]
    rc = ev["rate_check"]
    if rule == "OVER_RATE":
        return VerdictOut(
            verdict="worth_checking",
            headline=f"Billed {rc['ratio']:.2f}× the rate card, above the normal ±20–30% range.",
            reasoning=(f"The rate card gives about {inr(rc['expected_inr'])} for this job but {inr(rc['billed_inr'])} was billed. "
                       f"Normal variation is ±20–30%, so this is worth checking against the engineer's notes."),
            context_considered=["rate card maths", "normal ±20–30% variation"],
            evidence_refs=["rate_check.ratio", "rate_check.expected_inr", wid])
    if rule == "DOUBLE_BILL":
        other = ev["work_order_ids"][1] if len(ev["work_order_ids"]) > 1 else "an earlier job"
        return VerdictOut(
            verdict="worth_checking",
            headline="The same repair on the same road was billed twice within a week, with no complaint linked.",
            reasoning=(f"{wid} repeats the method of {other} within 7 days and has no linked complaint. "
                       "A second visit may have been needed, so the site records are worth checking."),
            context_considered=["same road and method within 7 days", "no complaint linked"],
            evidence_refs=["work_order_ids", "related_work_orders", wid])
    if rule == "DLP_PAID" and ev["tier"] == "audit":
        return VerdictOut(
            verdict="worth_checking",
            headline="This road is still under its repair warranty, yet BMC paid for a surface repair.",
            reasoning=(f"The road is under its Defect Liability Period and BMC paid {inr(rc['billed_inr'])} for a surface repair. "
                       "The original contractor may be liable, so it is worth checking whether the cost can be recovered."),
            context_considered=["road under DLP", "surface repair", "no utility-trench remark"],
            evidence_refs=["context.warranty", "road.under_dlp", wid])
    if rule == "DLP_PAID":
        trench = ctx["warranty"]["utility_trench_in_remark"]
        return VerdictOut(
            verdict="likely_justified" if trench else "needs_more_info",
            headline=("The remark points to a utility trench, which the road contractor is not liable for."
                      if trench else "Road is under warranty, but this type of work may not be covered."),
            reasoning=("The engineer's remark mentions a utility trench, which would not be the road contractor's liability. "
                       "This looks likely justified." if trench else
                       "The road is under warranty but the work type is not one the road contractor is clearly liable for. "
                       "More detail on the cause is needed to say whether BMC should have paid."),
            context_considered=["road under DLP", "work type", "engineer remark"],
            evidence_refs=["context.warranty", "context.engineer_remark", wid])
    if rule == "SLA_BREACH":
        w = ev["work_orders"][0]
        return VerdictOut(
            verdict="needs_more_info",
            headline="This job took more than twice its target time; the records do not say why.",
            reasoning=(f"It took {w['actual_hours']:.0f} hours against a {w['sla_hours']:.0f} hour target. "
                       "Rain or access problems may explain the delay, so the site log is worth checking."),
            context_considered=["time taken vs target", "rain around completion"],
            evidence_refs=["work_orders.actual_hours", "work_orders.sla_hours", "context.rain"])
    return VerdictOut(
        verdict="worth_checking",
        headline="The same repair by the same contractor failed again on this road.",
        reasoning=(f"{len(ev['work_order_ids'])} reopened jobs by the same contractor and method chain together on this road. "
                   "The method or workmanship is worth checking before more money is spent."),
        context_considered=["repeat reopens", "same contractor and method"],
        evidence_refs=["work_order_ids", "related_work_orders"])


def verdict_texts(v: VerdictOut) -> list[str]:
    return [v.headline, v.reasoning, *v.context_considered]


async def make_verdict(client, model: str, ev: dict) -> Generated[VerdictOut]:
    body = {k: x for k, x in ev.items() if k != "claude_review"}
    import json
    return await generate_checked(
        client=client, model=model, system=SYSTEM,
        user="Evidence pack:\n" + json.dumps(body, ensure_ascii=False),
        schema=VerdictOut, evidence=body, texts=verdict_texts,
        fallback=lambda: template_verdict(ev), check=_problems)


def to_entry(ev: dict, g: Generated[VerdictOut]) -> dict:
    return {"input_hash": evidence_hash(ev), "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": g.source, "model": g.model, "guardrail_retries": g.guardrail_retries, **g.value.model_dump()}


def to_review(entry: dict) -> dict:
    """The `review` shape attached to a flag (superset of the old {verdict, explanation})."""
    return {"verdict": entry["verdict"], "headline": entry["headline"], "reasoning": entry["reasoning"],
            "explanation": entry["reasoning"], "context_considered": entry["context_considered"],
            "evidence_refs": entry["evidence_refs"], "source": entry["source"], "model": entry.get("model")}
