# RoadRupee

**Where did the repair money go, and did the fix hold?**

Built for Claude Impact Lab Mumbai ("Follow the Rupee: Mumbai Monsoon Roads"). Every monsoon Mumbai spends crores fixing the same roads, and the potholes come back. RoadRupee shows, for each ward, where the road repair money went, whether the work held up, who is responsible, and where the next rupee should go.

> **All data is synthetic and all contractors are fictional.** Nothing here is real BMC data. Don't use it to judge any real person, contractor or department.

## North Star
**Promise:** "From a citizen's complaint to a ward officer's action — with evidence at every step."

We are judged on audit accuracy (25%), fair accountability (20%), budget smarts (20%), connecting the trail from complaints to work orders (15%) and usability plus demo (20%). The interface comes first: a hook home screen with three doors (Trace my complaint, Explore your ward, I'm a ward officer), in English, Hindi and Marathi. Claude does real work (multilingual complaint tracing, fair evidence verdicts, plain-language report cards, explained next-rupee plans, silent-failure spotting). Python does all the maths, and Claude never invents numbers or changes rule results. Full text: [CLAUDE.md](CLAUDE.md#north-star).

## How it works
1. **Hook screen.** Headline numbers are computed from the data: money spent on repairs that failed within 30 days, money paid on roads still under their Defect Liability Period (DLP), billing above the rate card, and fatal accidents tied to road defects. A ward map is coloured by "money that didn't hold".
2. **Audit engine.** Plain Python (pandas), no LLM arithmetic. Rules: OVER_RATE, DOUBLE_BILL, DLP_PAID, SLA_BREACH, REPEAT_FAILURE. Every flag lists its work order ids, severity and reason. Claude then reviews each flag in context and adds an explanation. It never removes the rule result.
3. **Fair scorecards.** Observed vs expected reopen rate (adjusted for repair method, rain and flood-proneness), plus SLA, cost vs rate card and volume.
4. **Next-rupee planner.** Risk score per road segment with a visible formula; recommends the most durable method within the ward's remaining budget.
5. **Trace my complaint.** Paste a complaint in Marathi, Hindi, Hinglish or English and follow it to the work order, contractor, cost and outcome.

Wording is deliberately fair: flags say "worth checking", never "fraud".

## Setup: your own API key
Copy `.env.example` to `.env` and add your own `ANTHROPIC_API_KEY`. **Never commit `.env`** (it is git-ignored and excluded from Docker images). Everyone on the team uses their own key; never paste a key into code, issues, PRs or chat.
```bash
cp .env.example .env
```

## Run it
```bash
cp .env.example .env        # add your own ANTHROPIC_API_KEY (only needed for Claude features)
docker compose up --build   # http://localhost:3000
```
Without Docker:
```bash
cd backend && uv sync && uv run fastapi dev app/main.py        # :8000
cd frontend && npm install && npm run dev                      # :3000 (BACKEND_URL=http://localhost:8000)
```
Tests and counts: `cd backend && uv run pytest && uv run python -m app.engine.report`.

Audit export for judges: `GET /api/flags.csv` (one row per flag, `work_order_id` first).

## Repo map
`backend/` FastAPI + engine · `frontend/` Next.js · `data/` dataset · `infra/` Azure deploy · `DESIGN.md` · `CLAUDE.md` · `CONTRIBUTING.md`

## Data attribution
Dataset: **Follow the Rupee: Mumbai Monsoon Roads** by Sumeet Doshi, Claude Community Ambassador, Anthropic, for Claude Impact Lab Mumbai. Source: https://github.com/SumeetGDoshi/Claude-Impact-Labs-data-2. Licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Included unmodified in `data/` with its original README and DATA_DICTIONARY.md.

The code in this repository was written from scratch during the hackathon.

## Planner and trace endpoints
`GET /api/plan?ward=f-s` returns the `PlanResponse` contract for every ward (engine: `backend/app/engine/planner.py`). `POST /api/trace {"text": "BMC25-000005"}` takes a complaint ID or free text in EN/HI/MR/Hinglish. `GET /api/linker/accuracy` checks complaint linking against complaints a work order fixed: issue type 95.3% (83.5% for the category citizens pick), ward 96%, road segment ~74%.
