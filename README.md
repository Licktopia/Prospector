# Prospector

**AI-powered job search automation.** Scrape job postings, score them against your resume with Claude, get tailored cover letters, and track your applications — all from a single dashboard.

Built for personal use. Supports multiple profiles so anyone in your household can run their own job search.

## How It Works

```
SerpAPI (Google Jobs) → Score & Rank (Claude) → Cover Letters → Dashboard → Apply
```

1. **Scrape** — Pulls job postings from Google Jobs via SerpAPI for your target roles and locations
2. **Score** — Claude evaluates each job against your resume (1-100 match score with reasoning)
3. **Cover Letters** — Auto-generated for high-scoring matches (70+), on-demand for any job
4. **Apply** — Direct links to Indeed, LinkedIn, company career pages. Copy your cover letter, click apply
5. **Repeat** — Runs automatically once per day via built-in scheduler

## Features

- **Multi-profile support** — Each user gets their own resume, target roles, locations, and job pipeline
- **Smart evaluation** — Two-pass system: scores all jobs cheaply, only generates cover letters for strong matches
- **Model selection** — Use Sonnet for quick drafts, Opus for the applications you care most about
- **Direct apply links** — Links straight to job boards, not Google search pages
- **Daily automation** — APScheduler runs scrape + evaluate for all active profiles at 6 AM UTC
- **Self-hosted** — Deploy on Railway (~$5/mo) or any Docker host. Your data stays yours

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI, async |
| Frontend | React 19, TypeScript, Tailwind CSS |
| Database | PostgreSQL 16, SQLAlchemy 2.0, Alembic |
| LLM | LangChain + Claude (Sonnet/Opus) |
| Scraping | SerpAPI (Google Jobs) |
| Scheduling | APScheduler |
| Deployment | Docker, Railway |

## Quick Start

### Prerequisites

- Docker (for PostgreSQL)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- API keys: [SerpAPI](https://serpapi.com/), [Anthropic](https://console.anthropic.com/)

### Local Development

```bash
# 1. Clone and configure
git clone https://github.com/Licktopia/Prospector.git
cd Prospector
cp .env.example .env
# Edit .env with your API keys

# 2. Start PostgreSQL
docker-compose up -d db

# 3. Install dependencies and run migrations
uv sync
uv run alembic upgrade head

# 4. Start the backend
uv run uvicorn app.main:app --reload

# 5. Start the frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — create a profile, upload your resume, and start scraping.

### Deploy to Railway

```bash
# Push to GitHub first
gh repo create Prospector --public --source=. --push
```

1. Go to [railway.app](https://railway.app) and connect your GitHub repo
2. Add a **PostgreSQL** database service
3. Set environment variables on the app service:
   - `DATABASE_URL` — from Railway PostgreSQL (change `postgresql://` to `postgresql+asyncpg://`)
   - `SERPAPI_KEY`
   - `ANTHROPIC_API_KEY`
4. Deploy — Railway builds from the Dockerfile automatically

You'll get a public URL. The daily scrape + evaluate runs on its own.

## Project Structure

```
app/
  api/           # FastAPI route handlers
  db/            # SQLAlchemy models, engine, sessions
  schemas/       # Pydantic request/response models
  services/      # Business logic (scraper, evaluator, resume parser)
  scheduler.py   # APScheduler daily job
  main.py        # App entry point
frontend/
  src/
    components/  # React UI components
    api/         # API client
    types/       # TypeScript interfaces
prompts/         # LLM prompt templates
alembic/         # Database migrations
tests/           # Pytest test suite
```

## License

MIT
