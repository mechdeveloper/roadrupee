# CLAUDE.md — RoadRupee

## Product
**RoadRupee — "Where did the repair money go, and did the fix hold?"** A Claude-powered audit tool for the Claude Impact Lab Mumbai hackathon, built from scratch in one day. Theme: "Follow the Rupee: Mumbai Monsoon Roads".

Features: (1) hook home screen, (2) deterministic audit engine plus Claude review of each flag, (3) fair contractor and ward scorecards, (4) next-rupee planner, (5) Trace my complaint (multilingual), (6) stretch: Ask the auditor.

Judging: audit accuracy 25 · fair accountability 20 · budget smarts 20 · connects the trail 15 · usable + demo 20.

**All data is synthetic and all contractors are fictional.** Never describe anything as real BMC data or a real firm.

## Data contract
Dataset lives in `data/` (CSV + GeoJSON; docs in `data/DATA_DICTIONARY.md`, `data/STARTER_IDEAS.md`). CC BY 4.0, by Sumeet Doshi. Do not edit the files. Loaded in one place: `backend/app/loader.py`.

Key joins: `work_orders.linked_complaint_ids` (pipe-separated) → `complaints`; `road_id` → `roads` (DLP) / `traffic`; `repair_method` → `rate_card`; `ward_code` → `wards` (budget, low_lying_index).

## Engine rules (deterministic Python; **no LLM arithmetic, ever**)
Expected cost = rate × `area_sqm` (per sqm) or rate (per job). Normal variation is ±20–30%.

| Rule | Tier | Logic |
|---|---|---|
| OVER_RATE | audit | cost > 1.5 × expected |
| DOUBLE_BILL | audit | same road + same repair_method within 7 days; the later WO has no linked complaint |
| DLP_PAID | audit / review | road `under_dlp=Y` and cost > 0. **audit**: work_type in (Pothole, Broken paver blocks, Road cave-in) AND surface repair method (cold/hot mix, mastic, paver blocks relaid, PQC patch) AND remark has no MTNL/MGL utility trench. **review**: everything else on DLP roads ("DLP road, but work not covered by road contractor's liability") |
| SLA_BREACH | review | completion > 2 × `sla_hours` only (plain misses are a scorecard metric) |
| REPEAT_FAILURE | review | repeat reopens on the same road (single reopen = scorecard metric only) |

Claude **adds** a one-line explanation or "likely justified" to each flag. It never deletes or changes the rule result.
Scorecards compare observed vs EXPECTED reopen rate (method baseline, adjusted for rain in the completion week and ward `low_lying_index`). Small samples are not blamed.
Planner: transparent risk formula shown in the UI; recommend the most durable method (lowest reopen rate), not the cheapest, within ward budget − spend.

## Stack
`frontend/` Next.js + TS + Tailwind + shadcn/ui + react-leaflet + Recharts. `backend/` FastAPI + Anthropic SDK (Messages API tool loop, no betas), uv, Python 3.12, pandas. Audit, scorecards and risk are precomputed at startup.

The browser only calls same-origin `/api/*`, via the Next.js catch-all route handler `frontend/app/api/[...path]/route.ts`. It reads `BACKEND_URL` at runtime and must stream SSE. No rewrites, no `NEXT_PUBLIC_*` API URL.

Models via env: `CLAUDE_MODEL_LIVE=claude-sonnet-5-5`, `CLAUDE_MODEL_EXTRACT=claude-opus-5-5`. Key: `ANTHROPIC_API_KEY` (never committed).

## Design
Follow `DESIGN.md`: tokens only, fair wording ("worth checking", never "fraud/scam"), ₹ Indian formatting, loading/empty/error states.

## Roles
| Who | Area |
|---|---|
| Tech lead | engine, API contracts, merges, deploy |
| Student 1 | scorecards + Claude summaries (EN/HI/MR) |
| Student 2 | next-rupee planner (backend + UI) |
| Student 3 | Trace my complaint (extraction, geocoding, trail UI) |
| Student 4 | flag explanations (Claude review), Ask the auditor, demo video |

## PR workflow
Branch per feature, PR into `main`, tech lead merges, `main` always runs. See `CONTRIBUTING.md`.

## Commands
```
docker compose up --build                  # everything, http://localhost:3000
cd backend && uv run pytest                # engine tests
cd backend && uv run python -m app.engine.report   # flag counts per rule + hook numbers
cd backend && uv run fastapi dev app/main.py
cd frontend && npm run dev
```
