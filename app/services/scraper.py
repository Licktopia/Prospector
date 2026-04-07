"""SerpAPI Google Jobs integration for scraping job postings."""

import hashlib
import logging
from typing import Any

from serpapi import GoogleSearch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import JobPosting, Profile

logger = logging.getLogger(__name__)


def _build_job_url(job: dict[str, Any]) -> str:
    """Build a canonical URL for deduplication.

    Uses the SerpAPI job_id to create a stable identifier. Falls back to
    the first apply link or a hash-based string.
    """
    job_id = job.get("job_id", "")
    if job_id:
        return f"https://www.google.com/search?ibp=htl;jobs&q={job_id}#htidocid={job_id}"
    apply_options = job.get("apply_options", [])
    if apply_options:
        return apply_options[0].get("link", "")
    key = (job.get("title", "") + job.get("company_name", "")).encode()
    return f"serpapi-{hashlib.sha256(key).hexdigest()[:16]}"


def _extract_apply_links(job: dict[str, Any]) -> list[dict[str, str]]:
    """Extract direct apply links from SerpAPI apply_options.

    Returns a list of {title, link} dicts for each application source
    (e.g. Indeed, LinkedIn, company career page).
    """
    apply_options = job.get("apply_options", [])
    return [
        {"title": opt.get("title", "Apply"), "link": opt.get("link", "")}
        for opt in apply_options
        if opt.get("link")
    ]


def _search_jobs(query: str, location: str) -> list[dict[str, Any]]:
    """Execute a single SerpAPI Google Jobs search.

    This is synchronous because the SerpAPI Python client is synchronous.
    Called from the async scrape_jobs via run_in_executor pattern.
    """
    settings = get_settings()
    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "api_key": settings.serpapi_key,
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get("jobs_results", [])


async def scrape_jobs(profile: Profile, session: AsyncSession) -> dict[str, int]:
    """Scrape jobs from SerpAPI for all query × location combos of a profile.

    Returns a summary dict with counts of total found, new inserted, and skipped.
    """
    import asyncio

    total_found = 0
    new_inserted = 0
    skipped = 0

    for query in profile.target_queries:
        for location in profile.target_locations:
            logger.info("Scraping: '%s' in '%s' for profile %d", query, location, profile.id)

            # Run synchronous SerpAPI call in a thread
            loop = asyncio.get_event_loop()
            jobs = await loop.run_in_executor(None, _search_jobs, query, location)
            total_found += len(jobs)

            for job_data in jobs:
                job_url = _build_job_url(job_data)
                if not job_url:
                    skipped += 1
                    continue

                # Check for duplicate
                existing = await session.execute(
                    select(JobPosting).where(
                        JobPosting.profile_id == profile.id,
                        JobPosting.job_url == job_url,
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue

                apply_links = _extract_apply_links(job_data)
                posting = JobPosting(
                    profile_id=profile.id,
                    job_title=job_data.get("title", "Unknown"),
                    company_name=job_data.get("company_name", "Unknown"),
                    job_url=job_url,
                    location=job_data.get("location", ""),
                    source="serpapi",
                    job_description=job_data.get("description", ""),
                    apply_links=apply_links if apply_links else None,
                    application_status="new",
                    search_query=query,
                )
                session.add(posting)
                new_inserted += 1

            await session.commit()

    summary = {
        "total_found": total_found,
        "new_inserted": new_inserted,
        "skipped": skipped,
    }
    logger.info(
        "Scrape complete for profile %d: %d found, %d new, %d skipped",
        profile.id, total_found, new_inserted, skipped,
    )
    return summary


async def backfill_apply_links(profile: Profile, session: AsyncSession) -> dict[str, int]:
    """Re-scrape SerpAPI to backfill apply_links for existing jobs missing them.

    Runs the same query × location combos and matches results to existing jobs
    by job URL. Only updates jobs that currently have no apply_links.
    """
    import asyncio

    updated = 0
    checked = 0

    for query in profile.target_queries:
        for location in profile.target_locations:
            logger.info("Backfill scraping: '%s' in '%s'", query, location)

            loop = asyncio.get_event_loop()
            jobs = await loop.run_in_executor(None, _search_jobs, query, location)

            for job_data in jobs:
                job_url = _build_job_url(job_data)
                if not job_url:
                    continue

                checked += 1

                # Find existing job
                result = await session.execute(
                    select(JobPosting).where(
                        JobPosting.profile_id == profile.id,
                        JobPosting.job_url == job_url,
                    )
                )
                existing = result.scalar_one_or_none()
                if not existing or existing.apply_links:
                    continue

                apply_links = _extract_apply_links(job_data)
                if apply_links:
                    existing.apply_links = apply_links
                    updated += 1

            await session.commit()

    logger.info(
        "Backfill complete for profile %d: %d checked, %d updated",
        profile.id, checked, updated,
    )
    return {"checked": checked, "updated": updated}
