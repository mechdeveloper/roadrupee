"""Trace my complaint: complaint id OR free text (EN / HI / MR / Hinglish) -> work order -> outcome.

All facts come from the engine. Claude is optional and only (a) extracts locality / issue when the
rules cannot, validated against the gazetteer, and (b) writes the answer in the citizen's language
from the facts. Without ANTHROPIC_API_KEY the deterministic answer is returned.
"""
from __future__ import annotations

import json
import os
import re

import pandas as pd

from .flags import Flag, inr
from .linker import ISSUE_TYPES, Gazetteer, classify, detect_language, match_road

ID_RE = re.compile(r"BMC25-\d{6}", re.I)
LANG_NAME = {"en": "English", "hi": "Hindi (Devanagari)", "mr": "Marathi (Devanagari)", "hi-en": "Hinglish (Hindi in Roman script)"}


def _wo_card(w: pd.Series, flags: list[Flag]) -> dict:
    return {
        "work_order_id": w.work_order_id, "ward_code": w.ward_code, "road_id": w.road_id,
        "work_type": w.work_type, "repair_method": w.repair_method,
        "contractor_id": w.contractor_id, "contractor_name": w.contractor_name,
        "completed_at": str(w.completed_at)[:16], "cost_inr": float(w.cost_inr),
        "expected_inr": float(w.expected_cost_inr), "cost_ratio": round(float(w.cost_ratio), 2),
        "sla_hours": int(w.sla_hours), "sla_met": w.sla_met == "Y", "held_up": not bool(w.reopened),
        "flags": [{"rule": f.rule, "tier": f.tier, "reason": f.reason} for f in flags if w.work_order_id in f.work_order_ids],
    }


def _steps(c: dict | None, w: dict | None, plan: dict | None, understood: dict) -> list[dict]:
    s = []
    if c:
        s.append({"label": "Complaint received", "detail": f"{c['complaint_id']} · {c['received_at']} · {c['channel']}", "status": "info"})
    s.append({"label": "Understood as", "detail": f"{understood['issue_type']} ({understood['type_source']}) · "
              f"{understood.get('locality') or '?'} · ward {understood.get('ward_code') or '?'}", "status": "info"})
    if understood.get("road_name"):
        s.append({"label": "Matched road", "detail": f"{understood['road_name']} ({understood['road_id']}) by {understood['road_match']}", "status": "info"})
    if w:
        s.append({"label": "Repair job", "detail": f"{w['work_order_id']} · {w['repair_method']} by {w['contractor_name']}", "status": "info"})
        s.append({"label": "Cost", "detail": f"{inr(w['cost_inr'])} vs {inr(w['expected_inr'])} rate card ({w['cost_ratio']}×)",
                  "status": "warn" if w["cost_ratio"] > 1.5 else "ok"})
        s.append({"label": "On time", "detail": f"{'Met' if w['sla_met'] else 'Missed'} the {w['sla_hours']} h target", "status": "ok" if w["sla_met"] else "warn"})
        s.append({"label": "Held up 30 days", "detail": "Yes" if w["held_up"] else "No, it was reopened within 30 days", "status": "ok" if w["held_up"] else "bad"})
        for f in w["flags"]:
            s.append({"label": "Worth checking" if f["tier"] == "audit" else "For review", "detail": f["reason"], "status": "warn"})
    elif plan:
        s.append({"label": "Still open", "detail": f"#{plan['ward_rank']} of {plan['ward_code']}'s next-rupee list (risk {plan['risk_score']}/100)", "status": "warn"})
        s.append({"label": "Planned fix", "detail": f"{plan['action']} · {plan['funding']}", "status": "info"})
    return s


def _summary(c, w, plan, understood) -> str:
    if w and c is None:
        held = "and it held up" if w["held_up"] else "but that fix failed within 30 days"
        return (f"No open complaint matches this yet. The last {w['work_type'].lower()} repair on record here was "
                f"{w['work_order_id']} by {w['contractor_name']} on {w['completed_at'][:10]} ({w['repair_method']}), {held}. "
                f"If the problem is back, report it and it will join the ward's next-rupee list.")
    if w:
        held = "and it held up" if w["held_up"] else "but the fix failed within 30 days"
        flag = " Part of this job is flagged as worth checking." if any(f["tier"] == "audit" for f in w["flags"]) else ""
        return (f"Fixed by {w['contractor_name']} on {w['completed_at'][:10]} ({w['work_order_id']}, {w['repair_method']}), "
                f"{held}. It cost {inr(w['cost_inr'])} against a standard {inr(w['expected_inr'])} and "
                f"{'met' if w['sla_met'] else 'missed'} its {w['sla_hours']} h target.{flag}")
    if plan:
        return (f"Not fixed yet. It is #{plan['ward_rank']} on ward {plan['ward_code']}'s next-rupee list "
                f"(risk {plan['risk_score']}/100): {plan['action'].lower()}.")
    if c is not None and str(c.get("status", "")).startswith(("Forwarded", "Rejected")):
        return f"Status: {c['status']}. BMC routed this away from its road repair budget."
    return "We could not link this to a repair job or an open issue yet."


def _claude(prompt: str, model_env: str, default: str) -> str | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        msg = anthropic.Anthropic().messages.create(model=os.environ.get(model_env, default), max_tokens=400,
                                                    messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    except Exception:  # Claude is an add-on: the deterministic trace still answers
        return None


def trace(text: str, data, wo: pd.DataFrame, flags: list[Flag], comp: pd.DataFrame, plan: dict, use_claude: bool = True) -> dict:
    text = (text or "").strip()
    wo_idx = wo.set_index("work_order_id", drop=False)
    roads = data.roads.set_index("road_id")
    plan_by_complaint = {cid: p for p in plan["issues"] for cid in p["complaint_ids"]}
    m = ID_RE.search(text)
    c = None
    if m:
        cid = m.group(0).upper()
        hit = comp[comp.complaint_id == cid]
        if hit.empty:
            return {"kind": "complaint", "found": False, "query": text, "summary": f"No complaint {cid} in the records.", "steps": []}
        r = hit.iloc[0]
        c = {k: (None if pd.isna(r[k]) else (str(r[k])[:16] if k == "received_at" else r[k]))
             for k in ("complaint_id", "received_at", "channel", "language", "locality_text", "ward_code", "description", "status", "upvotes")}
        c["upvotes"] = int(c["upvotes"] or 0)
        road_id, how = (None, "none")
        if pd.notna(r.work_order_id):
            road_id, how = wo_idx.loc[r.work_order_id, "road_id"], "work order"
        elif cid in plan_by_complaint:
            road_id, how = plan_by_complaint[cid]["road_id"], "road name / location"
        understood = {"issue_type": r.issue_type, "type_source": r.type_source, "locality": r.locality_text,
                      "ward_code": r.g_ward, "road_id": road_id, "road_match": how, "language": r.language}
        w = _wo_card(wo_idx.loc[r.work_order_id], flags) if pd.notna(r.work_order_id) else None
        p = plan_by_complaint.get(cid)
    else:
        issue, src = classify(text)
        gaz = Gazetteer(data.localities)
        g = gaz.find(text)
        if (g is None or issue == "Unclear") and use_claude:
            raw = _claude("Extract from this Mumbai road complaint the locality and the issue type. Issue type must be one of: "
                          "Pothole, Waterlogging, Open or broken manhole, Choked drain / nullah overflow, Road cave-in, "
                          'Broken paver blocks, Unclear. Reply with JSON only: {"locality": "...", "issue_type": "..."}\n\n'
                          f"Complaint: {text}", "CLAUDE_MODEL_EXTRACT", "claude-opus-5-5")
            try:
                j = json.loads(raw[raw.index("{"): raw.rindex("}") + 1]) if raw else {}
            except ValueError:
                j = {}
            if g is None and j.get("locality"):
                g = gaz.find(j["locality"])  # only accept a locality the gazetteer knows
            if issue == "Unclear" and j.get("issue_type") in ISSUE_TYPES:
                issue, src = j["issue_type"], "Claude (validated)"
        lat, lon, ward, loc = (g if g else (None, None, None, None))
        road_id, how = match_road(data.roads, text, ward, lat, lon)
        understood = {"issue_type": issue, "type_source": src, "locality": loc, "ward_code": ward,
                      "road_id": road_id, "road_match": how, "language": detect_language(text)}
        same = wo[(wo.road_id == road_id) & (wo.work_type == issue)].sort_values("completed_at") if road_id else wo.iloc[0:0]
        w = _wo_card(same.iloc[-1], flags) if len(same) else None
        p = next((x for x in plan["issues"] if x["road_id"] == road_id and x["issue_type"] == issue), None)
        if p and w:
            first_open = comp.loc[comp.complaint_id.isin(p["complaint_ids"]), "received_at"].min()
            if pd.Timestamp(w["completed_at"]) < first_open:
                w = None  # complaints came in after the last fix: it is an open issue, not a fixed one
    if understood.get("road_id"):
        understood["road_name"] = roads.loc[understood["road_id"], "road_name"]
    history = []
    if understood.get("road_id"):
        h = wo[(wo.road_id == understood["road_id"]) & (wo.work_type == understood["issue_type"])].sort_values("completed_at")
        history = [{"work_order_id": x.work_order_id, "completed_at": str(x.completed_at)[:10], "contractor_name": x.contractor_name,
                    "repair_method": x.repair_method, "cost_inr": float(x.cost_inr), "held_up": not bool(x.reopened)} for x in h.itertuples()][-6:]
    out = {"kind": "complaint" if m else "text", "found": True, "query": text, "understood": understood,
           "complaint": c, "work_order": w, "plan": p, "history": history}
    out["steps"] = _steps(c, w, p, understood)
    out["summary"] = _summary(c, w, p, understood)
    out["claude_summary"] = None
    if use_claude:
        lang = LANG_NAME.get(understood.get("language") or "en", "English")
        facts = {k: out[k] for k in ("understood", "complaint", "work_order", "plan", "history")}
        out["claude_summary"] = _claude(
            f"A Mumbai citizen asks what happened to their road complaint. Answer in {lang}, under 90 words, warm and plain. "
            "Use ONLY these facts (synthetic data, fictional contractors). Say what was done, by whom, cost vs the standard rate, "
            "whether it was on time and whether it held up; if still open, where it stands in the ward's queue. "
            "Mention flags neutrally as 'worth checking', never as wrongdoing. Include the work order id if there is one.\n\n"
            + json.dumps(facts, ensure_ascii=False, default=str), "CLAUDE_MODEL_LIVE", "claude-sonnet-5-5")
    return out
