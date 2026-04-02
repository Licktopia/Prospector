"""Web view routes — serve Jinja2 templates for the dashboard UI."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import JobPosting, Profile

logger = logging.getLogger(__name__)

router = APIRouter(tags=["views"])
templates = Jinja2Templates(directory="app/templates")


async def _get_all_profiles(session: AsyncSession) -> list[Profile]:
    """Fetch all profiles for the nav bar selector."""
    result = await session.execute(
        select(Profile).order_by(Profile.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/")
async def dashboard(
    request: Request,
    profile_id: int | None = None,
    status: str | None = None,
    min_score: int | None = None,
    search_query: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Main dashboard — job list with filters for the selected profile."""
    profiles = await _get_all_profiles(session)

    if not profiles:
        return templates.TemplateResponse(request, "dashboard.html", {
            "profiles": [],
            "current_profile": None,
            "jobs": [],
        })

    # Select profile: explicit param, or first active profile
    current_profile = None
    if profile_id:
        current_profile = await session.get(Profile, profile_id)
    if not current_profile:
        current_profile = profiles[0]

    # Build query for jobs
    query = select(JobPosting).where(JobPosting.profile_id == current_profile.id)

    if status:
        query = query.where(JobPosting.application_status == status)
    if min_score is not None:
        query = query.where(JobPosting.match_score >= min_score)
    if search_query:
        query = query.where(JobPosting.search_query == search_query)

    # Default: show evaluated first, then by score
    query = query.order_by(JobPosting.match_score.desc().nullslast())

    result = await session.execute(query)
    jobs = list(result.scalars().all())

    # Get unique search queries for filter dropdown
    sq_result = await session.execute(
        select(JobPosting.search_query)
        .where(JobPosting.profile_id == current_profile.id)
        .where(JobPosting.search_query.isnot(None))
        .distinct()
    )
    search_queries = [r[0] for r in sq_result.all()]

    # Calculate avg score
    scored_jobs = [j for j in jobs if j.match_score is not None]
    avg_score = sum(j.match_score for j in scored_jobs) / len(scored_jobs) if scored_jobs else 0

    return templates.TemplateResponse(request, "dashboard.html", {
        "profiles": profiles,
        "current_profile": current_profile,
        "jobs": jobs,
        "avg_score": avg_score,
        "filter_status": status,
        "filter_min_score": min_score,
        "filter_query": search_query,
        "search_queries": search_queries,
    })


@router.get("/jobs/{job_id}")
async def job_detail(
    request: Request,
    job_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Job detail view with cover letter and status controls."""
    job = await session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profiles = await _get_all_profiles(session)
    current_profile = await session.get(Profile, job.profile_id)

    return templates.TemplateResponse(request, "job_detail.html", {
        "profiles": profiles,
        "current_profile": current_profile,
        "job": job,
    })


@router.get("/profiles")
async def profiles_page(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Profile management page."""
    profiles = await _get_all_profiles(session)

    return templates.TemplateResponse(request, "profiles.html", {
        "profiles": profiles,
        "current_profile": profiles[0] if profiles else None,
    })
