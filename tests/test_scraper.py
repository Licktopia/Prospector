"""Tests for the SerpAPI scraper service."""

from unittest.mock import patch, MagicMock

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile, JobPosting
from app.services.scraper import scrape_jobs, _build_job_url, _search_jobs


MOCK_SERPAPI_RESULTS = [
    {
        "title": "Senior AI Engineer",
        "company_name": "Acme Corp",
        "location": "Remote",
        "description": "Looking for an experienced AI engineer...",
        "job_id": "abc123",
        "apply_options": [{"link": "https://acme.com/jobs/ai-eng"}],
    },
    {
        "title": "ML Platform Engineer",
        "company_name": "DataCo",
        "location": "Denver, CO",
        "description": "Build and maintain ML infrastructure...",
        "job_id": "def456",
        "apply_options": [{"link": "https://dataco.com/jobs/ml-plat"}],
    },
]


def test_build_job_url_with_job_id():
    """Should build a Google Jobs URL from the job_id."""
    job = {"job_id": "abc123", "title": "Engineer"}
    url = _build_job_url(job)
    assert "abc123" in url
    assert "google.com" in url


def test_build_job_url_fallback_to_apply_link():
    """Should fall back to apply link when no job_id."""
    job = {"title": "Engineer", "apply_options": [{"link": "https://example.com/apply"}]}
    url = _build_job_url(job)
    assert url == "https://example.com/apply"


@patch("app.services.scraper._search_jobs")
async def test_scrape_jobs_inserts_new(
    mock_search: MagicMock,
    session: AsyncSession,
    sample_profile: Profile,
):
    """Should insert new job postings from SerpAPI results."""
    mock_search.return_value = MOCK_SERPAPI_RESULTS

    summary = await scrape_jobs(sample_profile, session)

    assert summary["total_found"] > 0
    assert summary["new_inserted"] > 0

    # Verify jobs were persisted
    result = await session.execute(
        select(JobPosting).where(JobPosting.profile_id == sample_profile.id)
    )
    jobs = result.scalars().all()
    # sample_profile fixture already has one job from sample_job, but we don't
    # use sample_job fixture here, so all jobs are from scraping
    assert len(jobs) >= 2


@patch("app.services.scraper._search_jobs")
async def test_scrape_jobs_skips_duplicates(
    mock_search: MagicMock,
    session: AsyncSession,
    sample_profile: Profile,
):
    """Should skip jobs that already exist for the profile."""
    mock_search.return_value = MOCK_SERPAPI_RESULTS

    # First scrape
    summary1 = await scrape_jobs(sample_profile, session)
    assert summary1["new_inserted"] > 0

    # Second scrape with same results
    summary2 = await scrape_jobs(sample_profile, session)
    assert summary2["new_inserted"] == 0
    assert summary2["skipped"] == summary2["total_found"]


@patch("app.services.scraper._search_jobs")
async def test_scrape_jobs_empty_results(
    mock_search: MagicMock,
    session: AsyncSession,
    sample_profile: Profile,
):
    """Should handle empty SerpAPI results gracefully."""
    mock_search.return_value = []

    summary = await scrape_jobs(sample_profile, session)

    assert summary["total_found"] == 0
    assert summary["new_inserted"] == 0
    assert summary["skipped"] == 0


@patch("app.api.profiles.scrape_jobs")
async def test_scrape_endpoint(
    mock_scrape: MagicMock,
    client: AsyncClient,
    sample_profile: Profile,
):
    """Should trigger a scrape via the API endpoint."""
    mock_scrape.return_value = {
        "total_found": 10,
        "new_inserted": 8,
        "skipped": 2,
    }

    response = await client.post(f"/api/profiles/{sample_profile.id}/scrape")
    assert response.status_code == 200
    data = response.json()
    assert data["profile_id"] == sample_profile.id
    assert data["total_found"] == 10
    assert data["new_inserted"] == 8


async def test_scrape_endpoint_not_found(client: AsyncClient):
    """Should return 404 for nonexistent profile."""
    response = await client.post("/api/profiles/9999/scrape")
    assert response.status_code == 404
