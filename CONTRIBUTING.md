# Contributing

## Rules of the day
- **Everything is written today, from scratch.** Do not copy code from other projects.
- **`main` always runs.** If `docker compose up --build` works before your merge, it must work after.
- Never commit `.env` or any secret. Use `.env.example` for new variables.

## Setup: your own API key
Copy `.env.example` to `.env` and add your own `ANTHROPIC_API_KEY`. **Never commit `.env`** (it is git-ignored and excluded from Docker images). Students use their own keys. Never paste a key into code, issues, PRs or chat.
```bash
cp .env.example .env
```

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

## Ownership (avoid conflicts)
Stay inside your area unless you talk to the tech lead first. See the roles table in `CLAUDE.md`.

## Style
- Python: type hints, pandas for maths, no LLM arithmetic. Frontend: TypeScript strict, tokens from `DESIGN.md`, no hard-coded colours.
- Fair wording in all UI and generated text: "worth checking", never "fraud".
