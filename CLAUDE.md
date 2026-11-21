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
| REPEAT_FAILURE | review | same road + same contractor + same repair_method, ≥2 reopened WOs whose completion dates chain within 60 days (63 WOs, 30 flags). A single reopen is a scorecard metric only |

Claude **adds** a one-line explanation or "likely justified" to each flag. It never deletes or changes the rule result.
Scorecards compare observed vs EXPECTED reopen rate (method baseline, adjusted for rain in the completion week and ward `low_lying_index`). Small samples are not blamed.
Planner: transparent risk formula shown in the UI; recommend the most durable method (lowest reopen rate), not the cheapest, within ward budget − spend.

## Planner contract
`GET /api/plan?ward={slug}` → `PlanResponse`. **Engine owner: Student C. UI owner: tech lead.** Models: `backend/app/contracts/plan.py` (Pydantic, source of truth) and `frontend/lib/types.ts` (TypeScript mirror). Change both in the same commit and update the example below (a test fails if the example drifts from the model). Until the engine exists the route returns **HTTP 501** and the frontend shows clearly labelled example data. **Only on 501**: never fake data once the route returns 200.

`slug` is the ward code lower-cased with `/` replaced by `-` (`G/S` → `g-s`); the `slug` field is on every ward in `/api/wards`.

| Field | Meaning |
|---|---|
| `ward_slug`, `ward_code`, `ward_name` | which ward |
| `budget_inr`, `spent_inr`, `remaining_inr` | monsoon budget, spend so far, `budget − spend` (can be ≤ 0) |
| `formula` | `{weights: [{key, label, weight, description}], note}`. `weight` = max points of that part; weights sum to 100. Rendered transparently in the UI |
| `items[]` | ranked road segments, `rank` 1 = fix first (about 5 to 15 items) |
| `items[].road_id, road_name, segment_no, road_type, length_m, lat, lon` | the segment (lat/lon = midpoint) |
| `items[].risk_score` | 0–100, **equals the sum of `score_parts[].points`** |
| `items[].score_parts[]` | `{key: complaints\|flood\|traffic\|accidents\|facilities, label, points, max_points}` |
| `items[].reasons[]` | icon chips: `{kind: flood_hotspot\|tide\|ambulance_route\|school_route\|accidents\|open_complaints\|traffic\|bus_route, label, detail, count?}`. `label` is plain English |
| `items[].recommended_method` | `{repair_method, reopen_rate_pct, rate_inr, unit, why}`. **Most durable method (lowest 30-day reopen rate among methods suited to the issue), not the cheapest.** `repair_method` must exist in `rate_card.csv` |
| `items[].alternatives[]` | optional `{repair_method, reopen_rate_pct, estimated_cost_inr}` |
| `items[].area_sqm_estimate`, `estimated_cost_inr`, `cost_basis` | cost = rate × area (per sqm) or rate (per job); `cost_basis` says how, in words |
| `items[].within_budget` | greedy fit: fund items in rank order until `remaining_inr` runs out |
| `items[].evidence` | `{complaint_ids, accident_ids, hotspot_ids, facility_ids}`: every number links to evidence |
| `items[].explanation` | Claude's one-line explanation; `null` until wired. Claude never computes numbers |

Engine rules: deterministic Python (pandas), no LLM arithmetic. Inputs: open/unresolved complaints (severity, upvotes), flood hotspot proximity (+ tide sensitivity), traffic (congestion, bus routes), pothole / waterlogging / open-chamber accidents, school and hospital `ambulance_entry_road`. Open complaints have no `road_id`, so match each to the nearest road segment in its ward (GPS if present, else the locality centroid from `localities.csv`).

### Example response
```json
{
  "ward_slug": "g-s",
  "ward_code": "G/S",
  "ward_name": "Worli, Lower Parel, Prabhadevi",
  "budget_inr": 1400000,
  "spent_inr": 1020000,
  "remaining_inr": 380000,
  "formula": {
    "weights": [
      {
        "key": "complaints",
        "label": "Open complaints",
        "weight": 30,
        "description": "More unresolved complaints, weighted by severity and 'me too' votes, add more points."
      },
      {
        "key": "flood",
        "label": "Flooding",
        "weight": 25,
        "description": "Roads near a chronic flood spot score higher; tide-sensitive spots score highest."
      },
      {
        "key": "traffic",
        "label": "Traffic",
        "weight": 15,
        "description": "Busier roads and bus routes score higher."
      },
      {
        "key": "accidents",
        "label": "Accidents",
        "weight": 15,
        "description": "Pothole, waterlogging and open-chamber accidents on the road add points."
      },
      {
        "key": "facilities",
        "label": "Schools and hospitals",
        "weight": 15,
        "description": "Roads that are a hospital's ambulance entry or serve a school score higher."
      }
    ],
    "note": "Items are funded in rank order until the remaining budget runs out."
  },
  "items": [
    {
      "rank": 1,
      "road_id": "RD0151",
      "road_name": "Dr E Moses Road",
      "segment_no": 2,
      "road_type": "Arterial",
      "length_m": 310,
      "lat": 18.9985,
      "lon": 72.8292,
      "risk_score": 81.5,
      "score_parts": [
        {
          "key": "complaints",
          "label": "Open complaints",
          "points": 24.0,
          "max_points": 30
        },
        {
          "key": "flood",
          "label": "Flooding",
          "points": 22.5,
          "max_points": 25
        },
        {
          "key": "traffic",
          "label": "Traffic",
          "points": 11.0,
          "max_points": 15
        },
        {
          "key": "accidents",
          "label": "Accidents",
          "points": 9.0,
          "max_points": 15
        },
        {
          "key": "facilities",
          "label": "Schools and hospitals",
          "points": 15.0,
          "max_points": 15
        }
      ],
      "reasons": [
        {
          "kind": "flood_hotspot",
          "label": "Floods when rain passes 75 mm a day",
          "detail": "Flagged in 4 of the last 5 years",
          "count": null
        },
        {
          "kind": "ambulance_route",
          "label": "Ambulance entry road for a hospital",
          "detail": "Serves an emergency department",
          "count": 1
        },
        {
          "kind": "open_complaints",
          "label": "7 complaints still open",
          "detail": "Most recent 3 days ago",
          "count": 7
        },
        {
          "kind": "accidents",
          "label": "2 accidents blamed on potholes",
          "detail": "1 fatal, 1 grievous",
          "count": 2
        }
      ],
      "recommended_method": {
        "repair_method": "Hot mix patch",
        "reopen_rate_pct": 22.6,
        "rate_inr": 2600,
        "unit": "per sqm",
        "why": "Hot mix patches reopened less often (22.6%) than cold mix (32.2%), so the dearer repair wastes less money."
      },
      "alternatives": [
        {
          "repair_method": "Cold mix patch",
          "reopen_rate_pct": 32.2,
          "estimated_cost_inr": 86400
        }
      ],
      "area_sqm_estimate": 48,
      "estimated_cost_inr": 124800,
      "cost_basis": "₹2,600 per sqm × 48 sqm",
      "within_budget": true,
      "evidence": {
        "complaint_ids": [
          "BMC25-001234",
          "BMC25-001301"
        ],
        "accident_ids": [
          "ACC-0042",
          "ACC-0107"
        ],
        "hotspot_ids": [
          "FH07"
        ],
        "facility_ids": [
          "FAC-021"
        ]
      },
      "explanation": null
    }
  ]
}
```

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

## Git workflow (mandatory)

### Tech lead (repo owner, `mechdeveloper`)
- Commits directly to `main`. After **each** working feature or fix: run the tests (`cd backend && uv run pytest`; `cd frontend && npm run lint && npm run build` if the frontend was touched), commit with a conventional message (`feat:`, `fix:`, `chore:`, `docs:`) and push immediately.
- `git pull --rebase origin main` before pushing so teammates' merged PRs are never overwritten. **Never force-push `main`.**

### Team members (students)
- `git pull --rebase origin main` before starting each task.
- Work on a feature branch: `feat/<area>` (`feat/trace`, `feat/scorecard`, `feat/planner`, `feat/ui-home`).
- Commit and push the branch after each working step. Open a PR into `main` early with `gh pr create --fill` and keep PRs small.
- Rebase on `main` if there are conflicts.
- Data contract changes (backend models **and** frontend types) go in the same PR and are called out in the PR description.

### Everyone
- `main` must always run: tests pass before pushing or merging.
- Never commit `.env`, secrets, `node_modules` or large generated files. Check `git status` before every commit.
- Claude Code sessions: commit and push after every working step, without waiting to be asked.

Full details and ownership: `CONTRIBUTING.md`.

## Commands
```
docker compose up --build                  # everything, http://localhost:3000
cd backend && uv run pytest                # engine tests
cd backend && uv run python -m app.engine.report   # flag counts per rule + hook numbers
cd backend && uv run fastapi dev app/main.py
cd frontend && npm run dev
```
