# Contributing

## Rules of the day
- **Everything is written today, from scratch.** Do not copy code from other projects.
- **`main` always runs.** If `docker compose up --build` works before your merge, it must work after.
- Never commit `.env` or any secret. Use `.env.example` for new variables.

## Workflow
1. `git pull origin main`
2. Branch per feature: `git switch -c feat/<short-name>` (e.g. `feat/trace-endpoint`, `fix/map-legend`).
3. Small commits, clear messages.
4. Before you push: backend `cd backend && uv run pytest`; frontend `cd frontend && npm run lint && npm run build`.
5. Open a PR into `main`. Describe what changed and how you checked it. Tech lead reviews and merges.
6. Rebase or merge `main` into your branch if it moved. Resolve conflicts yourself, then re-test.

## Ownership (avoid conflicts)
Stay inside your area unless you talk to the tech lead first. See the roles table in `CLAUDE.md`.

## Style
- Python: type hints, pandas for maths, no LLM arithmetic. Frontend: TypeScript strict, tokens from `DESIGN.md`, no hard-coded colours.
- Fair wording in all UI and generated text: "worth checking", never "fraud".
