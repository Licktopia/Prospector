# Prospector - Project Plan

## Goal

**Prospector** automates the grind of job searching: scrape relevant postings, score them against a resume using an LLM, generate tailored cover letters, and surface everything through a clean web UI. Supports multiple user profiles — each with their own resume, target roles, and locations — so anyone can use it. Built as a local tool, not a SaaS product.

---

## Tech Stack

| Layer            | Choice                          | Rationale                                        |
|------------------|---------------------------------|--------------------------------------------------|
| Language         | Python 3.12                     | Already configured                               |
| Framework        | FastAPI                         | Already in project, async-native                 |
| Database         | PostgreSQL (local)              | Robust, pgvector-ready if needed later            |
| ORM              | SQLAlchemy 2.0 + asyncpg        | Async support, mature, pairs well with FastAPI    |
| Migrations       | Alembic                         | Standard for SQLAlchemy projects                  |
| Scraping         | SerpAPI (Google Jobs)           | Structured JSON, no HTML parsing needed           |
| LLM              | LangChain + ChatAnthropic (Claude Sonnet 4) | Structured output, prompt templates, chains |
| Validation       | Pydantic v2                     | FastAPI-native, LLM structured output             |
| Frontend         | Jinja2 templates + HTMX         | Simple, no build step, server-rendered            |
| Styling          | Tailwind CSS (CDN)              | Fast to prototype, clean look                     |
| Package Manager  | uv                              | Already configured                               |
| Environment      | python-dotenv                   | Keep secrets out of code                         |

### Why Jinja2 + HTMX over React?

This is a personal tool, not a product. React + Vite would add a build step, a separate dev server, and CORS config for a UI that's basically a table with filters. HTMX gives us interactive behavior (filtering, pagination, expanding cover letters) with zero JavaScript build tooling. If it ever needs to become fancier, the API endpoints are already there to bolt on a React frontend later.

---

## Database Schema

### Table: `profiles`

Each profile represents a job seeker with their own resume, target roles, and locations.

| Column           | Type        | Constraints / Notes                              |
|------------------|-------------|--------------------------------------------------|
| id               | SERIAL      | PRIMARY KEY                                      |
| name             | VARCHAR     | NOT NULL — display name (e.g. "Jeff", "Sarah")   |
| resume_pdf_path  | VARCHAR     | NOT NULL — path to resume PDF file               |
| resume_text      | TEXT        | NULLABLE — extracted text, cached after parsing   |
| target_queries   | TEXT[]      | Array of job search terms                        |
| target_locations | TEXT[]      | Array of locations to search                     |
| evaluator_prompt | TEXT        | NULLABLE — custom system prompt for this profile |
| is_active        | BOOLEAN     | DEFAULT true                                     |
| created_at       | TIMESTAMPTZ | DEFAULT NOW()                                    |

### Table: `job_postings`

| Column             | Type        | Constraints / Notes                              |
|--------------------|-------------|--------------------------------------------------|
| id                 | SERIAL      | PRIMARY KEY                                      |
| profile_id         | INTEGER     | FK -> profiles.id, NOT NULL                      |
| job_title          | VARCHAR     | NOT NULL                                         |
| company_name       | VARCHAR     | NOT NULL                                         |
| job_url            | VARCHAR     | NOT NULL                                         |
| location           | VARCHAR     |                                                  |
| source             | VARCHAR     | e.g. "serpapi", "manual"                         |
| job_description    | TEXT        |                                                  |
| match_score        | INTEGER     | NULLABLE, 1-100                                  |
| match_reasoning    | TEXT        | NULLABLE — why the LLM gave this score           |
| cover_letter       | TEXT        | NULLABLE                                         |
| application_status | VARCHAR     | DEFAULT 'new' — new/evaluated/applied/rejected/interview |
| search_query       | VARCHAR     | Which search term found this job                 |
| date_added         | TIMESTAMPTZ | DEFAULT NOW()                                    |
| date_evaluated     | TIMESTAMPTZ | NULLABLE — when the LLM processed it             |

**Unique constraint:** `(profile_id, job_url)` — the same job can appear for different profiles but not duplicated within one.

---

## Project Structure

```
Prospector/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan events
│   ├── config.py            # Settings via pydantic-settings + .env
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py      # SQLAlchemy async engine + session factory
│   │   └── models.py        # SQLAlchemy ORM models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scraper.py       # SerpAPI integration
│   │   ├── evaluator.py     # LangChain evaluation pipeline
│   │   └── resume_parser.py # PDF text extraction
│   ├── api/
│   │   ├── __init__.py
│   │   ├── profiles.py      # Profile routes (thin handlers)
│   │   └── jobs.py          # Job routes (thin handlers)
│   └── templates/
│       ├── base.html        # Layout with Tailwind
│       ├── dashboard.html   # Job list with filters
│       ├── job_detail.html  # Single job + cover letter view
│       └── profiles.html    # Profile management
├── alembic/                 # Database migrations
├── docs/                    # Mermaid flowcharts and architecture docs
├── resumes/                 # PDF storage directory (git-ignored)
├── .env.example
├── .env                     # git-ignored
├── pyproject.toml
├── alembic.ini
├── CLAUDE.md
├── BUGS.md
└── project_plan.md
```

---

## Implementation Phases

### Phase 1: Foundation

**Goal:** Running FastAPI app with database, profiles, config, and resume parsing.

1. Install dependencies via `uv add`:
   - `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
   - `pydantic-settings`, `python-dotenv`
   - `langchain`, `langchain-anthropic`, `langchain-core`
   - `google-search-results` (SerpAPI)
   - `pymupdf` (PDF parsing)
   - `jinja2`, `python-multipart` (templates)
   - `httpx` (async HTTP client)

2. Create `app/config.py` — Pydantic `Settings` class loading from `.env`:
   - `DATABASE_URL`, `SERPAPI_KEY`, `ANTHROPIC_API_KEY`

3. Create `app/db/database.py` — async SQLAlchemy engine + session factory

4. Create `app/db/models.py` — `Profile` and `JobPosting` ORM models

5. Set up Alembic for migrations, generate initial migration

6. Create `app/services/resume_parser.py` — extract text from PDF
   - Parse on profile creation, store extracted text in `profiles.resume_text`

7. Move FastAPI app into `app/main.py`, wire up lifespan events

**Checkpoint:** `uvicorn app.main:app --reload` starts clean, tables exist, can create a profile with a resume.

---

### Phase 2: The Scraper

**Goal:** Fetch jobs from SerpAPI and persist them, scoped to a profile.

1. Create `app/services/scraper.py`:
   - Function: `async def scrape_jobs(profile: Profile) -> dict`
   - Read `target_queries` and `target_locations` from the profile
   - Hit SerpAPI Google Jobs endpoint for each query + location combo
   - Extract: title, company, URL, location, full description
   - Insert with conflict handling on `(profile_id, job_url)` — skip duplicates
   - Return summary: how many found, how many new, how many skipped

2. Add API route in `app/api/profiles.py`: `POST /api/profiles/{id}/scrape` — triggers a scrape for that profile

3. Add CLI entrypoint: `python -m app.services.scraper --profile-id 1`

**Checkpoint:** Run a scrape for a profile, see new jobs in the database tied to that profile.

---

### Phase 3: The Evaluator

**Goal:** Score jobs and generate cover letters using Claude, tailored per profile.

1. Create `app/schemas/schemas.py` — Pydantic model for structured LLM output:
   ```python
   class JobEvaluation(BaseModel):
       match_score: int          # 1-100
       match_reasoning: str      # 2-3 sentences on why
       cover_letter: str         # 3 paragraphs, tailored
   ```

2. Create `app/services/evaluator.py` using LangChain:
   - Query jobs for a given profile where `application_status = 'new'`
   - Load `resume_text` from the profile
   - Set up `ChatAnthropic` (Claude Sonnet 4) with `.with_structured_output(JobEvaluation)`
   - Use `ChatPromptTemplate` for prompt construction:
     - If the profile has a custom `evaluator_prompt`, use it as the system message
     - Otherwise, build a default prompt using the resume text:
       - Persona: Senior hiring evaluator
       - Scoring rubric: weight relevant experience, tech stack overlap, seniority match
       - Cover letter instructions: reference specific resume accomplishments that map to the JD, technical and concise, 3 paragraphs (hook, evidence, close)
   - Compose as a chain: prompt | model | structured output
   - Update row with results, set status to `'evaluated'`, stamp `date_evaluated`
   - Rate limit: small delay between API calls

3. Add API route in `app/api/profiles.py`: `POST /api/profiles/{id}/evaluate`

4. Add CLI entrypoint: `python -m app.services.evaluator --profile-id 1`

**Checkpoint:** Run evaluator for a profile, jobs move to `'evaluated'` with scores and tailored cover letters.

---

### Phase 4: Dashboard

**Goal:** Web UI to browse, filter, and act on results across profiles.

1. Set up Jinja2 template rendering in FastAPI

2. **Profile selector / management:**
   - Switch between profiles from the nav bar
   - Create new profile: name, upload resume PDF, set target queries + locations
   - Edit profile: update search terms, locations, custom evaluator prompt

3. **Dashboard page (`GET /`):**
   - Table of jobs for the selected profile: title, company, location, score, status, date
   - Sort by match score (highest first) by default
   - Filter by: status, minimum score, search query
   - Color-code scores: green (75+), yellow (50-74), red (<50)
   - Click a row to expand/navigate to detail

4. **Job detail page (`GET /jobs/{id}`):**
   - Full job description
   - Match score with reasoning
   - Cover letter (with copy-to-clipboard button)
   - Status update buttons: Mark as Applied / Rejected / Interview

5. **HTMX interactions:**
   - Filter/sort without full page reload
   - Inline status updates
   - "Run Scraper" / "Run Evaluator" buttons with progress feedback

**Checkpoint:** Open browser, switch between profiles, see jobs ranked by fit, read cover letters, update statuses.

---

## Default Profile: Jeff

```
name: Jeff
target_queries:
  - "AI Software Engineer"
  - "AI Engineer"
  - "LLM Engineer"
  - "Applied AI Engineer"
  - "RAG Engineer"
  - "Python Backend Engineer"
  - "AI Platform Engineer"
target_locations:
  - "Remote"
  - "Colorado"
  - "Denver, CO"
```

---

## API Keys Required

| Service   | Free Tier                | Paid                             |
|-----------|--------------------------|----------------------------------|
| SerpAPI   | 100 searches/month       | $50/mo for 5,000 searches        |
| Anthropic | Pay-as-you-go            | ~$0.01-0.03 per job evaluation   |

---

## Intended Daily Workflow

1. **Automated** (scheduled, e.g. noon daily): scraper + evaluator run for all active profiles
2. **Email digest** lands in inbox — summary of new jobs, top matches with cover letters inline
3. **User reviews email** — copy cover letter, apply to interesting jobs
4. **Dashboard** (optional) — mark jobs as Applied/Rejected/Interview, tweak profile settings, review history

The dashboard is a management/configuration tool, not the daily touchpoint. The email is.

---

## Future Ideas (Not in v1)

- **Daily email digest** — summary of new matches with cover letters inline, sent after scheduled run
- **Scheduled runs** — cron-based scraping + evaluation on autopilot (hosting-dependent)
- **Multiple resume variants per profile** — pick the best one per job type
- **Application tracking** — link to where you applied, interview dates, notes
- **Additional sources** — LinkedIn RSS, Indeed, HN "Who's Hiring"
- **Analytics** — trends in what's being posted, which skills appear most
