"""Job posting API routes — thin handlers, no business logic."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import JobPosting, Profile
from app.services.evaluator import generate_cover_letter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/")
async def list_jobs(
    profile_id: int,
    status: str | None = Query(None),
    min_score: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List jobs for a profile with optional filters."""
    query = select(JobPosting).where(JobPosting.profile_id == profile_id)

    if status:
        query = query.where(JobPosting.application_status == status)
    if min_score is not None:
        query = query.where(JobPosting.match_score >= min_score)

    query = query.order_by(JobPosting.match_score.desc().nullslast())

    result = await session.execute(query)
    jobs = result.scalars().all()
    return [
        {
            "id": j.id,
            "job_title": j.job_title,
            "company_name": j.company_name,
            "location": j.location,
            "match_score": j.match_score,
            "application_status": j.application_status,
            "date_added": j.date_added.isoformat(),
        }
        for j in jobs
    ]


@router.get("/{job_id}")
async def get_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get a single job posting with full details."""
    job = await session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "profile_id": job.profile_id,
        "job_title": job.job_title,
        "company_name": job.company_name,
        "job_url": job.job_url,
        "location": job.location,
        "source": job.source,
        "job_description": job.job_description,
        "match_score": job.match_score,
        "match_reasoning": job.match_reasoning,
        "cover_letter": job.cover_letter,
        "application_status": job.application_status,
        "search_query": job.search_query,
        "date_added": job.date_added.isoformat(),
        "apply_links": job.apply_links,
        "date_evaluated": job.date_evaluated.isoformat() if job.date_evaluated else None,
    }


@router.patch("/{job_id}/status")
async def update_job_status(
    job_id: int,
    status: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update the application status of a job posting."""
    valid_statuses = {"new", "evaluated", "applied", "rejected", "interview"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    job = await session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.application_status = status
    await session.commit()

    logger.info("Updated job %d status to %s", job_id, status)
    return {"id": job.id, "application_status": job.application_status}


@router.post("/{job_id}/generate-cover-letter")
async def generate_cover_letter_endpoint(
    job_id: int,
    model: str = Query("sonnet", pattern="^(sonnet|opus)$"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Generate a cover letter on demand for a specific job.

    Accepts a model param: 'sonnet' (fast/cheap) or 'opus' (highest quality).
    """
    job = await session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = await session.get(Profile, job.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    cover_letter = await generate_cover_letter(job, profile, session, model=model)

    return {
        "id": job.id,
        "cover_letter": cover_letter,
        "model_used": model,
    }
