from __future__ import annotations

import asyncio
import csv
import io
import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from . import cache

load_dotenv()

CSV_COLUMNS = [
    "work_order_id", "rule", "tier", "severity", "reason", "related_work_order_ids",
    "ward_code", "road_id", "contractor_id", "cost_inr", "expected_inr", "amount_inr",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pre = cache.build()  # precompute audit, scorecards at startup
    yield


app = FastAPI(title="RoadRupee API", lifespan=lifespan)


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
        })
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="roadrupee_flags.csv"'})


# --- Claude-powered endpoints: stubs for later milestones -------------------
def _stub(name: str) -> JSONResponse:
    return JSONResponse({"error": "not_implemented", "endpoint": name,
                         "detail": "Claude-powered endpoint, coming in a later milestone."}, status_code=501)


@app.post("/api/trace")
def trace() -> JSONResponse:
    return _stub("trace")


@app.post("/api/explain")
def explain() -> JSONResponse:
    return _stub("explain")


@app.get("/api/plan")
def plan() -> JSONResponse:
    return _stub("plan")


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
