"""Tests for SQLAlchemy ORM models."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile, JobPosting


async def test_create_profile(session: AsyncSession):
    """Should create a profile with all fields."""
    profile = Profile(
        name="Jeff",
        resume_pdf_path="resumes/jeff_resume.pdf",
        resume_text="Software engineer with 5 years experience.",
        target_queries=["AI Engineer", "Python Developer"],
        target_locations=["Remote"],
    )
    session.add(profile)
    await session.flush()

    assert profile.id is not None
    assert profile.name == "Jeff"
    assert profile.is_active is True
    assert profile.created_at is not None
    assert len(profile.target_queries) == 2


async def test_create_job_posting(session: AsyncSession, sample_profile: Profile):
    """Should create a job posting linked to a profile."""
    job = JobPosting(
        profile_id=sample_profile.id,
        job_title="ML Engineer",
        company_name="TechCo",
        job_url="https://example.com/jobs/456",
        location="Denver, CO",
        source="serpapi",
        application_status="new",
    )
    session.add(job)
    await session.flush()

    assert job.id is not None
    assert job.profile_id == sample_profile.id
    assert job.application_status == "new"
    assert job.match_score is None
    assert job.date_evaluated is None


async def test_profile_job_relationship(
    session: AsyncSession, sample_profile: Profile, sample_job: JobPosting
):
    """Profile should have a relationship to its job postings."""
    result = await session.execute(
        select(Profile).where(Profile.id == sample_profile.id)
    )
    profile = result.scalar_one()

    await session.refresh(profile, ["job_postings"])
    assert len(profile.job_postings) >= 1
    assert profile.job_postings[0].job_title == "Senior AI Engineer"


async def test_job_default_status(session: AsyncSession, sample_profile: Profile):
    """New jobs should default to 'new' status."""
    job = JobPosting(
        profile_id=sample_profile.id,
        job_title="Data Scientist",
        company_name="DataCo",
        job_url="https://example.com/jobs/789",
    )
    session.add(job)
    await session.flush()

    assert job.application_status == "new"
