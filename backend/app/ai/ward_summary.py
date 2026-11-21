"""Claude's plain 3-sentence summary of a ward in EN / HI / MR, from deterministic facts only."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from pydantic import BaseModel

from ..engine import views
from ..engine.flags import Flag
from .structured import Generated, generate_checked
from .verdict import BANNED

RULE_PLAIN = {
    "OVER_RATE": "a job billed well above the standard rate",
    "DOUBLE_BILL": "the same repair billed twice within a week with no complaint linked",
    "DLP_PAID": "a repair paid for by the city while the road is still under its original contractor's warranty",
    "SLA_BREACH": "a job that took more than twice its target time",
    "REPEAT_FAILURE": "the same fix by the same contractor failing again",
}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
SENTENCE_END = re.compile(r"[.।!?](?:\s|$)")


class WardSummaryOut(BaseModel):
    en: str
    hi: str
    mr: str


SYSTEM = """You write a short, fair summary of one Mumbai ward's monsoon road-repair spending for a citizen or ward officer.
You get a JSON facts object computed by Python. Rules:
- Write exactly 3 plain sentences in each of English (en), Hindi (hi, Devanagari) and Marathi (mr, Devanagari). One idea per sentence:
  1. where the money went (spend, the top contractor and top repair method by spend);
  2. did the fixes hold compared with what we would expect for the methods, rain and flooding (observed vs expected reopen rate). If small_sample is true or the interval includes the expected rate, say it is about as expected / too early to tell. Never blame on small samples;
  3. the top thing worth checking (top_flag), naming its work order id, in the plain words given in top_flag.what.
- Use only numbers in the facts. Copy money exactly as the *_text fields (e.g. "₹3.07 Cr", "₹45 L") in all three languages, and write every number with ordinary digits 0-9, never Devanagari digits. Percentages as "23%". Do no new arithmetic. Do not write any other rupee amounts, percentages or multipliers.
- Fair wording: "worth checking"; never fraud, scam, corrupt, theft or any accusation. No internal rule names.
- Plain, warm, short sentences. Natural Hindi and Marathi, not word-for-word translation.
All data is synthetic and all contractors are fictional."""


def facts(pre, w: dict, flags: list[Flag]) -> dict:
    flow = views.ward_flow(pre.data, pre.wo, w["ward_code"], w["ward_name"], w["budget_inr"])
    spend = flow["spend_inr"] or 1.0
    c, m = flow["contractors"][0], flow["methods"][0]
    mine = [f for f in flags if f.ward_code == w["ward_code"] and f.rule != "SILENT_FAILURE"]  # keeps stored summaries valid
    top = max((f for f in mine if f.tier == "audit"), key=lambda f: f.amount_inr, default=None) \
        or max(mine, key=lambda f: f.amount_inr, default=None)
    n = int(w["work_orders"])
    out = {
        "ward_name": w["ward_name"], "work_orders": n, "small_sample": n < 30,
        "spend_inr": round(flow["spend_inr"]), "spend_text": views.money(flow["spend_inr"]),
        "budget_text": views.money(w["budget_inr"]), "budget_inr": round(w["budget_inr"]),
        "failed_spend_inr": round(flow["failed_inr"]), "failed_spend_text": views.money(flow["failed_inr"]),
        "failed_pct": round(w["failed_pct"]),
        "top_contractor": {"name": c["contractor_name"], "spend_inr": round(c["spend_inr"]),
                           "spend_text": views.money(c["spend_inr"]), "share_pct": round(c["spend_inr"] / spend * 100)},
        "top_method": {"name": m["repair_method"], "spend_inr": round(m["spend_inr"]),
                       "spend_text": views.money(m["spend_inr"]), "share_pct": round(m["spend_inr"] / spend * 100)},
        "reopen_observed_pct": round(w["reopen_observed_pct"]), "reopen_expected_pct": round(w["reopen_expected_pct"]),
        "reopen_ci_low_pct": round(w["reopen_ci_low_pct"]), "reopen_ci_high_pct": round(w["reopen_ci_high_pct"]),
        "fixes_vs_expected": views_verdict(w),
        "flags_audit": w["flags_audit"], "flags_review": sum(1 for f in mine if f.tier == "review"),
    }
    if top:
        out["top_flag"] = {"work_order_id": top.work_order_ids[0], "what": RULE_PLAIN[top.rule],
                           "amount_inr": round(top.amount_inr), "amount_text": views.money(top.amount_inr),
                           "detail": top.reason}
    return out


def views_verdict(w: dict) -> str:
    if w["reopen_ci_low_pct"] > w["reopen_expected_pct"]:
        return "worse than expected"
    if w["reopen_ci_high_pct"] < w["reopen_expected_pct"]:
        return "better than expected"
    return "about as expected"


def input_hash(f: dict) -> str:
    return hashlib.sha256(json.dumps(f, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _check(s: WardSummaryOut) -> list[str]:
    out = []
    for lang in ("en", "hi", "mr"):
        t = getattr(s, lang)
        if len(SENTENCE_END.findall(t)) != 3:
            out.append(f"{lang} must be exactly 3 sentences")
        if (lang != "en") != bool(DEVANAGARI.search(t)):
            out.append(f"{lang} is in the wrong script")
        if any(b in t.lower() for b in BANNED):
            out.append(f"{lang} uses an accusing word")
    if DEVANAGARI.search("".join(re.findall(r"₹?\s*[०-९]+", s.hi + s.mr))):
        out.append("use digits 0-9 only")
    return out


def template_summary(f: dict) -> WardSummaryOut:
    """Deterministic English fallback (hi/mr fall back to the same English text)."""
    c, m = f["top_contractor"], f["top_method"]
    s1 = (f"{f['ward_name']} spent {f['spend_text']} on {f['work_orders']} repair jobs; "
          f"the biggest shares went to {c['name']} ({c['share_pct']}%) and to {m['name']} ({m['share_pct']}%).")
    tail = "too few jobs to be sure" if f["small_sample"] else f["fixes_vs_expected"]
    s2 = (f"{f['reopen_observed_pct']}% of repairs reopened within 30 days against about "
          f"{f['reopen_expected_pct']}% expected, so fixes held {tail}.")
    t = f.get("top_flag")
    s3 = (f"The top thing worth checking is work order {t['work_order_id']}: {t['what']}." if t
          else "Nothing stands out as worth checking.")
    text = " ".join([s1, s2, s3])
    return WardSummaryOut(en=text, hi=text, mr=text)


async def make_summary(client, model: str, f: dict) -> Generated[WardSummaryOut]:
    return await generate_checked(
        client=client, model=model, system=SYSTEM, user="Facts:\n" + json.dumps(f, ensure_ascii=False),
        schema=WardSummaryOut, evidence=f, texts=lambda s: [s.en, s.hi, s.mr],
        fallback=lambda: template_summary(f), check=_check)


def to_entry(f: dict, g: Generated[WardSummaryOut]) -> dict:
    return {"input_hash": input_hash(f), "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": g.source, "model": g.model, "guardrail_retries": g.guardrail_retries, **g.value.model_dump()}
