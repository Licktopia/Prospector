"""Tests for job posting API routes."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile, JobPosting


async def test_list_jobs(client: AsyncClient, sample_profile: Profile, sample_job: JobPosting):
    """Should return jobs for a profile."""
    response = await client.get(f"/api/jobs/?profile_id={sample_profile.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["job_title"] == "Senior AI Engineer"


async def test_list_jobs_filter_by_status(
    client: AsyncClient, sample_profile: Profile, sample_job: JobPosting
):
    """Should filter jobs by status."""
    response = await client.get(
        f"/api/jobs/?profile_id={sample_profile.id}&status=new"
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1

    response = await client.get(
        f"/api/jobs/?profile_id={sample_profile.id}&status=applied"
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


async def test_list_jobs_filter_by_min_score(
    client: AsyncClient,
    session: AsyncSession,
    sample_profile: Profile,
    sample_job: JobPosting,
):
    """Should filter jobs by minimum score."""
    sample_job.match_score = 85
    await session.flush()

    response = await client.get(
        f"/api/jobs/?profile_id={sample_profile.id}&min_score=80"
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1

    response = await client.get(
        f"/api/jobs/?profile_id={sample_profile.id}&min_score=90"
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


async def test_get_job(client: AsyncClient, sample_job: JobPosting):
    """Should return full job details."""
    response = await client.get(f"/api/jobs/{sample_job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_title"] == "Senior AI Engineer"
    assert data["company_name"] == "Acme Corp"
    assert data["job_url"] == "https://example.com/jobs/123"


async def test_get_job_not_found(client: AsyncClient):
    """Should return 404 for nonexistent job."""
    response = await client.get("/api/jobs/9999")
    assert response.status_code == 404


async def test_update_job_status(client: AsyncClient, sample_job: JobPosting):
    """Should update job application status."""
    response = await client.patch(
        f"/api/jobs/{sample_job.id}/status?status=applied"
    )
    assert response.status_code == 200
    assert response.json()["application_status"] == "applied"


async def test_update_job_status_invalid(client: AsyncClient, sample_job: JobPosting):
    """Should reject invalid status values."""
    response = await client.patch(
        f"/api/jobs/{sample_job.id}/status?status=bogus"
    )
    assert response.status_code == 400


async def test_update_job_status_not_found(client: AsyncClient):
    """Should return 404 for nonexistent job."""
    response = await client.patch("/api/jobs/9999/status?status=applied")
    assert response.status_code == 404
