"""Profile API routes — thin handlers, no business logic."""

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Profile
from app.services.resume_parser import extract_text_from_pdf
from app.services.evaluator import evaluate_jobs
from app.services.scraper import backfill_apply_links, scrape_jobs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

RESUMES_DIR = Path("resumes")


@router.get("/")
async def list_profiles(session: AsyncSession = Depends(get_session)) -> list[dict]:
    """List all profiles."""
    result = await session.execute(
        select(Profile).order_by(Profile.created_at.desc())
    )
    profiles = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "is_active": p.is_active,
            "target_queries": p.target_queries,
            "target_locations": p.target_locations,
            "created_at": p.created_at.isoformat(),
        }
        for p in profiles
    ]


def _parse_multiline_form(value: list[str]) -> list[str]:
    """Parse form input that may be a single newline-separated string or a list."""
    items = []
    for v in value:
        items.extend(line.strip() for line in v.splitlines() if line.strip())
    return items


@router.post("/", status_code=201)
async def create_profile(
    request: Request,
    name: str = Form(...),
    target_queries: list[str] = Form(...),
    target_locations: list[str] = Form(...),
    resume: UploadFile = ...,
    session: AsyncSession = Depends(get_session),
):
    """Create a new profile with a resume PDF."""
    # Parse textarea inputs (newline-separated) into lists
    queries = _parse_multiline_form(target_queries)
    locations = _parse_multiline_form(target_locations)

    # Save the uploaded resume
    RESUMES_DIR.mkdir(exist_ok=True)
    resume_path = RESUMES_DIR / f"{name.lower().replace(' ', '_')}_{resume.filename}"
    with open(resume_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    # Extract text from the resume
    resume_text = extract_text_from_pdf(resume_path)

    profile = Profile(
        name=name,
        resume_pdf_path=str(resume_path),
        resume_text=resume_text,
        target_queries=queries,
        target_locations=locations,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)

    logger.info("Created profile %d: %s", profile.id, profile.name)

    # If request came from browser form, redirect to dashboard
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url=f"/?profile_id={profile.id}", status_code=303)
    return {"id": profile.id, "name": profile.name, "status": "created"}


@router.post("/{profile_id}/scrape")
async def scrape_profile_jobs(
    profile_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger a job scrape for a specific profile."""
    profile = await session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    summary = await scrape_jobs(profile, session)
    return {"profile_id": profile_id, "profile_name": profile.name, **summary}


@router.post("/{profile_id}/backfill-apply-links")
async def backfill_profile_apply_links(
    profile_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Re-scrape SerpAPI to backfill apply links for existing jobs missing them."""
    profile = await session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    summary = await backfill_apply_links(profile, session)
    return {"profile_id": profile_id, "profile_name": profile.name, **summary}


@router.post("/{profile_id}/evaluate")
async def evaluate_profile_jobs(
    profile_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger LLM evaluation for all unevaluated jobs of a profile."""
    profile = await session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    summary = await evaluate_jobs(profile, session)
    return {"profile_id": profile_id, "profile_name": profile.name, **summary}


@router.post("/{profile_id}/resume")
async def update_resume(
    request: Request,
    profile_id: int,
    resume: UploadFile,
    session: AsyncSession = Depends(get_session),
):
    """Upload a new resume PDF for an existing profile."""
    profile = await session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Save the new resume
    RESUMES_DIR.mkdir(exist_ok=True)
    resume_path = RESUMES_DIR / f"{profile.name.lower().replace(' ', '_')}_{resume.filename}"
    with open(resume_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    # Re-extract text
    profile.resume_pdf_path = str(resume_path)
    profile.resume_text = extract_text_from_pdf(resume_path)
    await session.commit()

    logger.info("Updated resume for profile %d: %s", profile.id, profile.name)

    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/profiles", status_code=303)
    return {"id": profile.id, "name": profile.name, "status": "resume_updated"}


@router.patch("/{profile_id}")
async def update_profile(
    profile_id: int,
    data: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update profile fields (name, target_queries, target_locations)."""
    profile = await session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if "name" in data:
        profile.name = data["name"]
    if "target_queries" in data:
        profile.target_queries = data["target_queries"]
    if "target_locations" in data:
        profile.target_locations = data["target_locations"]

    await session.commit()
    logger.info("Updated profile %d: %s", profile.id, profile.name)
    return {"id": profile.id, "name": profile.name, "status": "updated"}


@router.get("/{profile_id}")
async def get_profile(
    profile_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get a single profile by ID."""
    profile = await session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "id": profile.id,
        "name": profile.name,
        "resume_pdf_path": profile.resume_pdf_path,
        "target_queries": profile.target_queries,
        "target_locations": profile.target_locations,
        "evaluator_prompt": profile.evaluator_prompt,
        "is_active": profile.is_active,
        "created_at": profile.created_at.isoformat(),
    }
