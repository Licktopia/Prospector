"""Tests for profile API routes."""

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile


async def test_list_profiles_empty(client: AsyncClient):
    """Should return empty list when no profiles exist."""
    response = await client.get("/api/profiles/")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_profiles(client: AsyncClient, sample_profile: Profile):
    """Should return all profiles."""
    response = await client.get("/api/profiles/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test User"


async def test_get_profile(client: AsyncClient, sample_profile: Profile):
    """Should return a single profile by ID."""
    response = await client.get(f"/api/profiles/{sample_profile.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["target_queries"] == ["AI Engineer", "Python Developer"]
    assert data["target_locations"] == ["Remote", "Denver, CO"]


async def test_get_profile_not_found(client: AsyncClient):
    """Should return 404 for nonexistent profile."""
    response = await client.get("/api/profiles/9999")
    assert response.status_code == 404


async def test_create_profile(client: AsyncClient):
    """Should create a profile with resume upload."""
    with (
        patch("app.api.profiles.extract_text_from_pdf") as mock_parse,
        patch("app.api.profiles.shutil.copyfileobj"),
    ):
        mock_parse.return_value = "Extracted resume text content"

        response = await client.post(
            "/api/profiles/",
            data={
                "name": "New User",
                "target_queries": "ML Engineer",
                "target_locations": "Remote",
            },
            files={"resume": ("resume.pdf", b"fake pdf content", "application/pdf")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New User"
    assert data["status"] == "created"


async def test_update_resume(client: AsyncClient, sample_profile: Profile):
    """Should update the resume for an existing profile."""
    with (
        patch("app.api.profiles.extract_text_from_pdf") as mock_parse,
        patch("app.api.profiles.shutil.copyfileobj"),
    ):
        mock_parse.return_value = "Updated resume text"

        response = await client.post(
            f"/api/profiles/{sample_profile.id}/resume",
            files={"resume": ("new_resume.pdf", b"new pdf content", "application/pdf")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resume_updated"


async def test_update_resume_not_found(client: AsyncClient):
    """Should return 404 for nonexistent profile."""
    response = await client.post(
        "/api/profiles/9999/resume",
        files={"resume": ("resume.pdf", b"content", "application/pdf")},
    )
    assert response.status_code == 404
