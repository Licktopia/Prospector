"""Tests for the dashboard web views."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile, JobPosting


async def test_dashboard_no_profiles(client: AsyncClient):
    """Should show empty state when no profiles exist."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "No profiles yet" in response.text


async def test_dashboard_with_profile(client: AsyncClient, sample_profile: Profile):
    """Should render dashboard for the first profile."""
    response = await client.get("/")
    assert response.status_code == 200
    assert sample_profile.name in response.text


async def test_dashboard_with_jobs(
    client: AsyncClient, sample_profile: Profile, sample_job: JobPosting
):
    """Should show jobs in the table."""
    response = await client.get(f"/?profile_id={sample_profile.id}")
    assert response.status_code == 200
    assert "Senior AI Engineer" in response.text
    assert "Acme Corp" in response.text


async def test_dashboard_filter_by_status(
    client: AsyncClient, sample_profile: Profile, sample_job: JobPosting
):
    """Should filter jobs by status."""
    response = await client.get(f"/?profile_id={sample_profile.id}&status=new")
    assert response.status_code == 200
    assert "Senior AI Engineer" in response.text

    response = await client.get(f"/?profile_id={sample_profile.id}&status=applied")
    assert response.status_code == 200
    assert "No jobs match" in response.text


async def test_job_detail_page(client: AsyncClient, sample_profile: Profile, sample_job: JobPosting):
    """Should render job detail page."""
    response = await client.get(f"/jobs/{sample_job.id}")
    assert response.status_code == 200
    assert "Senior AI Engineer" in response.text
    assert "Acme Corp" in response.text


async def test_job_detail_not_found(client: AsyncClient):
    """Should return 404 for nonexistent job."""
    response = await client.get("/jobs/9999")
    assert response.status_code == 404


async def test_profiles_page(client: AsyncClient, sample_profile: Profile):
    """Should render profiles management page."""
    response = await client.get("/profiles")
    assert response.status_code == 200
    assert "Test User" in response.text
    assert "Create New Profile" in response.text
