from __future__ import annotations

import asyncio
import csv
import io
import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

import anthropic

from . import cache, ratelimit
from .ai import client as ai_client
from .ai.structured import Generated
from .ai.verdict import make_verdict, template_verdict, to_entry, to_review
from .engine import evidence
from .routes.home import router as home_router
from .routes.pages import router as pages_router
from .routes.plan import router as plan_router
from .routes.trace import router as trace_router

load_dotenv()

EXPLAIN_TIMEOUT = 30.0  # seconds before falling back to the automatic summary

CSV_COLUMNS = [
    "work_order_id", "rule", "tier", "severity", "reason", "related_work_order_ids",
    "ward_code", "road_id", "contractor_id", "cost_inr", "expected_inr", "amount_inr",
    "claude_verdict", "claude_headline",  # appended; empty when no verdict was computed
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pre = cache.build()  # precompute audit, scorecards at startup
    yield


app = FastAPI(title="RoadRupee API", lifespan=lifespan)
app.include_router(pages_router)
app.include_router(home_router)
app.include_router(trace_router)
app.include_router(plan_router)


def pre(request: Request) -> cache.Precomputed:
    return request.app.state.pre


@app.get("/api/health")
def health(request: Request) -> dict:
    p = pre(request)
    return {"status": "ok", "work_orders": len(p.wo), "flags": len(p.flags)}


@app.get("/api/summary")
def summary(request: Request) -> dict:
    return pre(request).summary


@app.get("/api/wards")
def wards(request: Request) -> list[dict]:
    return pre(request).wards


@app.get("/api/wards.geojson")
def wards_geojson(request: Request) -> Response:
    path = pre(request).data.dir / "wards.geojson"
    return Response(path.read_bytes(), media_type="application/geo+json")


@app.get("/api/contractors")
def contractors(request: Request) -> list[dict]:
    return pre(request).contractors


def _filtered(request: Request, rule, tier, ward, severity):
    out = pre(request).flags
    if rule:
        out = [f for f in out if f.rule == rule.upper()]
    if tier:
        out = [f for f in out if f.tier == tier]
    if ward:
        out = [f for f in out if f.ward_code == ward]
    if severity:
        out = [f for f in out if f.severity == severity]
    return out


@app.get("/api/flags")
def flags(request: Request, rule: str | None = None, tier: str | None = None,
          ward: str | None = None, severity: str | None = None,
          limit: int = Query(500, le=5000), offset: int = 0) -> dict:
    fl = _filtered(request, rule, tier, ward, severity)
    return {"total": len(fl), "items": [f.to_dict() for f in fl[offset:offset + limit]]}


@app.get("/api/flags.csv")
def flags_csv(request: Request, rule: str | None = None, tier: str | None = None,
              ward: str | None = None, severity: str | None = None) -> Response:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    w.writeheader()
    for f in _filtered(request, rule, tier, ward, severity):
        w.writerow({
            "work_order_id": f.work_order_ids[0],
            "rule": f.rule, "tier": f.tier, "severity": f.severity, "reason": f.reason,
            "related_work_order_ids": "|".join(f.work_order_ids[1:]),
            "ward_code": f.ward_code, "road_id": f.road_id, "contractor_id": f.contractor_id,
            "cost_inr": round(f.cost_inr, 2),
            "expected_inr": "" if f.expected_inr is None else round(f.expected_inr, 2),
            "amount_inr": round(f.amount_inr, 2),
            "claude_verdict": (f.review or {}).get("verdict", ""),
            "claude_headline": (f.review or {}).get("headline", ""),
        })
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="roadrupee_flags.csv"'})


# --- Claude-powered endpoints: stubs for later milestones -------------------
def _stub(name: str) -> JSONResponse:
    return JSONResponse({"error": "not_implemented", "endpoint": name,
                         "detail": "Claude-powered endpoint, coming in a later milestone."}, status_code=501)


@app.post("/api/explain/{flag_id}")
async def explain(request: Request, flag_id: str) -> dict:
    """Claude's verdict for one flag (any tier). Cached after the first call; never changes the rule result."""
    p = pre(request)
    f = next((x for x in p.flags if x.flag_id == flag_id.upper()), None)
    if f is None:
        raise HTTPException(404, f"Unknown flag '{flag_id}'")
    ev = evidence.build(p.evidence_index, f)
    h = evidence.evidence_hash(ev)
    hit = p.verdicts.get(f.flag_id, h)
    if hit:
        f.review = to_review(hit)
        return {"flag_id": f.flag_id, "review": f.review, "cached": True}
    if not ai_client.have_key():  # no key: show the deterministic template, do not cache it
        g = Generated(template_verdict(ev), "template", None, 0, [])
        return {"flag_id": f.flag_id, "review": to_review(to_entry(ev, g)), "cached": False}
    ok, wait = ratelimit.live.check(ratelimit.client_ip(request))  # only a call that reaches Claude counts
    if not ok:
        return ratelimit.too_many(wait)
    try:
        g = await asyncio.wait_for(make_verdict(ai_client.get_client(), ai_client.model_live(), ev), EXPLAIN_TIMEOUT)
    except (anthropic.APIError, asyncio.TimeoutError):  # Claude down or slow: show the automatic summary, never an error
        g = Generated(template_verdict(ev), "template", None, 0, [])
        return {"flag_id": f.flag_id, "review": to_review(to_entry(ev, g)), "cached": False}
    entry = to_entry(ev, g)
    p.verdicts.put(f.flag_id, entry)
    p.verdicts.save()
    f.review = to_review(entry)
    return {"flag_id": f.flag_id, "review": f.review, "cached": False}


@app.post("/api/ask")
def ask() -> JSONResponse:
    return _stub("ask")


@app.get("/api/_sse_test")
async def sse_test() -> StreamingResponse:
    """Tiny SSE stream used to verify the Next.js proxy streams without buffering."""
    async def gen():
        for i in range(5):
            yield f"data: {json.dumps({'tick': i})}\n\n"
            await asyncio.sleep(0.4)
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
