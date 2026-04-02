# CLAUDE.md — Prospector

## Project Overview

Job search automation tool: scrape postings via SerpAPI, score them against a resume using an LLM, generate tailored cover letters, and surface everything through a web UI. Supports multiple user profiles — each with their own resume, target roles, and locations. Built as a local tool, not a SaaS product.

**See `project_plan.md` for implementation phases and database schema.**

## Tech Stack

- **Backend**: Python 3.12, FastAPI, async-native
- **Database**: PostgreSQL, SQLAlchemy 2.0 + asyncpg, Alembic for migrations
- **Scraping**: SerpAPI (Google Jobs)
- **LLM**: LangChain + ChatAnthropic (Claude Sonnet 4) — structured output via Pydantic models
- **Validation**: Pydantic v2
- **Frontend**: Jinja2 templates + HTMX + Tailwind CSS (CDN)
- **Package Manager**: uv
- **Environment**: python-dotenv, pydantic-settings

## Architecture

Strict layered separation — same pattern as Legal-Document-Analyzer:

- **API** (`app/api/`) — thin route handlers only, no business logic
- **Services** (`app/services/`) — orchestration and business logic, no raw DB queries
- **DB** (`app/db/`) — SQLAlchemy models, engine, session factory
- **Schemas** (`app/schemas/`) — Pydantic request/response models, no logic

## Code Conventions

- Python type hints everywhere
- Pydantic models for all data structures and API schemas
- Async FastAPI endpoints
- Docstrings on all public functions (what AND why)
- Environment variables for all configuration (never hardcode API keys)
- `logging` module, not print statements

## Database Migration Rules

**Never write a migration that rewrites every row.** These hold exclusive locks:
- No `ADD COLUMN ... NOT NULL` without a server-side default
- No `ALTER COLUMN ... TYPE ...`
- No backfill `UPDATE` inside a migration

**Safe pattern:** `ADD COLUMN nullable` → backfill in batches outside the migration.

**Migration file naming:** `YYYYMMDDHHmmss_<rev>_<slug>.py` (configured in `alembic.ini`). Never rename existing files.

## Testing

**Policy: write tests immediately after each module, before moving on.**

```bash
uv run pytest                    # all tests
uv run pytest -m "not slow"     # skip slow integration tests
```

Mock external APIs (SerpAPI, Anthropic). DB tests use real PostgreSQL, skipped if `TEST_DATABASE_URL` not set.

## Bug Tracking

Whenever a bug is found and fixed, add an entry to `BUGS.md` with: **BUG-NNN** (sequential), Status, Discovered, Symptom, Root cause, Fix. Add even minor bugs — the log is most useful when complete.

## Git Conventions

**Never push directly to `main`** — all changes via PR.

### Branch Naming
`type/short-description` — types: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`, `perf`

### Commit Messages
Conventional Commits: `type(scope): short imperative description`

Scopes: `scraper`, `evaluator`, `api`, `db`, `config`, `frontend`, `models`, `schemas`, `tests`

Rules: lowercase, imperative mood, no period, 72 char max subject line.

## LangChain Usage

LangChain is used in the evaluator layer for LLM interactions. This is intentional — gaining experience with the framework is a project goal.

- `langchain-anthropic` for `ChatAnthropic`
- `.with_structured_output()` for the `JobEvaluation` Pydantic model
- `ChatPromptTemplate` for system/evaluator prompts (custom per profile)
- Chains to compose the evaluation pipeline

## Environment Setup

```bash
cp .env.example .env
# Fill in: DATABASE_URL, SERPAPI_KEY, ANTHROPIC_API_KEY

uv sync
uvicorn app.main:app --reload
```
