"""Endpoints behind the ward / contractor / search pages. Additive; kept out of main.py on purpose."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..contracts.pages import ContractorCard, Locality, WardFlow, WardTimeline
from ..engine import views

router = APIRouter(prefix="/api")


def _ward(request: Request, slug: str) -> dict:
    for w in request.app.state.pre.wards:
        if w["slug"] == slug:
            return w
    raise HTTPException(404, f"Unknown ward '{slug}'")


@router.get("/wards/{slug}")
def ward_detail(request: Request, slug: str) -> dict:
    return _ward(request, slug)


@router.get("/wards/{slug}/flow", response_model=WardFlow)
def ward_flow(request: Request, slug: str) -> dict:
    w = _ward(request, slug)
    p = request.app.state.pre
    return views.ward_flow(p.data, p.wo, w["ward_code"], w["ward_name"], w["budget_inr"])


@router.get("/wards/{slug}/timeline", response_model=WardTimeline)
def ward_timeline(request: Request, slug: str) -> dict:
    w = _ward(request, slug)
    p = request.app.state.pre
    return views.ward_timeline(p.data, p.wo, w["ward_code"])


@router.get("/contractors/{contractor_id}", response_model=ContractorCard)
def contractor(request: Request, contractor_id: str) -> dict:
    p = request.app.state.pre
    card = views.contractor_card(p.data, p.wo, p.flags, p.contractors, p.wards, contractor_id.upper())
    if card is None:
        raise HTTPException(404, f"Unknown contractor '{contractor_id}'")
    return card


@router.get("/localities", response_model=list[Locality])
def localities(request: Request) -> list[dict]:
    p = request.app.state.pre
    ward = {w["ward_code"]: w for w in p.wards}
    out = []
    for r in p.data.localities.itertuples():
        w = ward.get(r.ward_code)
        if not w:
            continue
        aliases = [a.strip() for a in str(r.aliases).split(";") if a.strip()] if isinstance(r.aliases, str) else []
        out.append(dict(locality=r.locality, ward_code=r.ward_code, ward_slug=w["slug"],
                        ward_name=w["ward_name"], aliases=aliases))
    return out


@router.get("/flags/{flag_id}")
def flag_by_id(request: Request, flag_id: str) -> dict:
    for f in request.app.state.pre.flags:
        if f.flag_id == flag_id.upper():
            return f.to_dict()
    raise HTTPException(404, f"Unknown flag '{flag_id}'")
