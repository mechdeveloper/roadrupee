"""Claude parts of Trace my complaint: structured extraction, and the answer in the user's language.

Facts, matching, geocoding and the RTI draft are deterministic (engine/trace.py, engine/rti.py).
Claude never invents numbers: the answer goes through generate_checked (numbers guardrail + template fallback).
"""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel

from ..engine.trace import CATEGORIES, DEVANAGARI
from .structured import Generated, generate_checked
from .verdict import BANNED

SENTENCE_END = re.compile(r"[.।!?](?:\s|$)")
LANG_NAME = {
    "en": "English",
    "hi": "Hindi (Devanagari script)",
    "mr": "Marathi (Devanagari script)",
    "hi-en": "Hinglish (Hindi written in Roman letters, the way the citizen wrote)",
}


class ExtractOut(BaseModel):
    language: Literal["en", "hi", "mr", "hi-en"]
    locality: str | None
    issue_type: Literal[
        "Pothole", "Waterlogging", "Open or broken manhole", "Choked drain / nullah overflow",
        "Road cave-in", "Broken paver blocks", "other",
    ]
    summary: str


EXTRACT_SYSTEM = """You read one citizen complaint about a Mumbai road problem, written in Marathi, Hindi, Hinglish (Hindi in Roman letters) or English, possibly with spelling mistakes, abbreviations or mixed scripts.
Return:
- language: "mr" (Marathi), "hi" (Hindi in Devanagari), "hi-en" (Hinglish: Hindi words in Roman letters), or "en".
- locality: the place mentioned, normalised to EXACTLY one name from the gazetteer list you are given (match Devanagari spellings and abbreviations to the English name, e.g. "भायखळा" -> "Byculla"). If the text names a place that is not in the list, or none, return null. Never invent a name.
- issue_type: one of the six categories, or "other" if none fits. Water standing on the road is "Waterlogging"; a missing or broken manhole cover is "Open or broken manhole"; a blocked drain or overflowing nullah is "Choked drain / nullah overflow"; a road that has sunk or collapsed is "Road cave-in"; loose or broken footpath tiles are "Broken paver blocks"; holes in the road surface are "Pothole".
- summary: one short English sentence describing the problem.
All data is synthetic."""


async def extract(client, model: str, text: str, localities: list[str]) -> ExtractOut:
    r = await client.messages.parse(
        model=model, max_tokens=1000, system=EXTRACT_SYSTEM,
        messages=[{"role": "user", "content": f"Gazetteer: {json.dumps(localities, ensure_ascii=False)}\n\nComplaint:\n{text}"}],
        output_format=ExtractOut, output_config={"effort": "low"},
    )
    if r.parsed_output is None:
        raise ValueError(f"unusable extraction (stop_reason={r.stop_reason})")
    return r.parsed_output


class AnswerOut(BaseModel):
    text: str


ANSWER_SYSTEM = """You answer a Mumbai citizen who asked "What happened to my complaint?".
You get a JSON facts object computed by Python about their complaint. Rules:
- Reply in the language asked (the user's own language). Hinglish means Hindi written in Roman letters.
- 3 to 5 short, plain sentences. Say first what happened (fixed and held / fixed but reopened / still open / in progress / forwarded / rejected), then the one or two facts that matter (who did the work, the cost against the rate card, whether the road was under warranty, whether the target time was met), then what they can do next (the evidence page and the RTI request on this page).
- Use only facts in the JSON. Write money exactly as given (e.g. "₹22,935"), multipliers as given (e.g. "2.2×"), and every number with ordinary digits 0-9, never Devanagari digits. Do no new arithmetic and add no other numbers, amounts or percentages.
- Fair and calm. Say "worth checking", never fraud, scam, corrupt, theft or any accusation. The contractor and the city are doing a job; do not blame anyone. No internal rule names.
All data is synthetic and all contractors are fictional."""


def _check(lang: str):
    def check(a: AnswerOut) -> list[str]:
        out = []
        n = len(SENTENCE_END.findall(a.text))
        if not 2 <= n <= 6:
            out.append("answer should be 3 to 5 sentences")
        deva = bool(DEVANAGARI.search(a.text))
        if (lang in ("hi", "mr")) != deva:
            out.append("answer is in the wrong script for the requested language")
        if any(b in a.text.lower() for b in BANNED):
            out.append("uses an accusing word")
        return out
    return check


def template_answer(f: dict) -> AnswerOut:
    """Deterministic English fallback built only from the facts."""
    wo = f.get("work_order")
    cid, issue = f["complaint_id"], f["issue"]
    if f["outcome"] in ("fixed_held", "fixed_failed") and wo:
        s1 = (f"Your complaint {cid} about {issue.lower()} was fixed under work order {wo['id']} "
              f"({wo['repair_method']}, by {wo['contractor']}), finished on {wo['finished_on']}.")
        s2 = (f"It was billed at {wo['billed']} against about {wo['expected']} expected from the rate card "
              f"({wo['billed_vs_expected']}), and the target time was {'met' if wo['target_met'] else 'missed'}.")
        s3 = ("The repair held for 30 days." if f["outcome"] == "fixed_held"
              else "The repair did not hold: the problem came back within 30 days.")
        s4 = "The road was still under warranty, which is worth checking." if wo["road_under_warranty"] else ""
        s5 = "You can open the evidence page or send the RTI request below to ask for the records."
        return AnswerOut(text=" ".join(x for x in (s1, s2, s3, s4, s5) if x))
    msg = {
        "open": "is still open in the records: no repair has been logged yet.",
        "in_progress": "is marked In Progress, but no work order has been logged yet.",
        "forwarded": "was forwarded to another authority, so BMC has no work order for it.",
        "rejected": "was closed without a repair (it was rejected).",
    }.get(f["outcome"], "could not be matched to a repair.")
    return AnswerOut(text=f"Your complaint {cid} about {issue.lower()} {msg} You can send the RTI request below to ask what is happening.")


async def answer(client, model: str, facts: dict, lang: str) -> Generated[AnswerOut]:
    return await generate_checked(
        client=client, model=model, system=ANSWER_SYSTEM,
        user=f"Reply language: {LANG_NAME[lang]}.\nFacts (JSON):\n{json.dumps(facts, ensure_ascii=False)}",
        schema=AnswerOut, evidence=facts, texts=lambda a: [a.text],
        fallback=lambda: template_answer(facts), check=_check(lang), effort="low",
    )
