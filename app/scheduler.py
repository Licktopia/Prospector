"""Daily scheduled scrape + evaluate for all active profiles.

Uses APScheduler to run once per day at a configurable time. The job runs
inside the existing FastAPI process — no external cron needed.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import Profile
from app.services.scraper import scrape_jobs
from app.services.evaluator import evaluate_jobs

logger = logging.getLogger(__name__)

# Run daily at 6 AM UTC (midnight MDT)
SCHEDULE_HOUR = 6
SCHEDULE_MINUTE = 0


async def daily_scrape_and_evaluate():
    """Scrape then evaluate jobs for every active profile."""
    logger.info("Scheduled job starting: daily scrape + evaluate")

    async with async_session_factory() as session:
        result = await session.execute(
            select(Profile).where(Profile.is_active.is_(True))
        )
        profiles = result.scalars().all()

        if not profiles:
            logger.info("No active profiles found, skipping")
            return

        for profile in profiles:
            try:
                logger.info("Processing profile %d: %s", profile.id, profile.name)

                scrape_summary = await scrape_jobs(profile, session)
                logger.info(
                    "Profile %d scrape: %d new, %d skipped",
                    profile.id,
                    scrape_summary["new_inserted"],
                    scrape_summary["skipped"],
                )

                eval_summary = await evaluate_jobs(profile, session)
                logger.info(
                    "Profile %d evaluate: %d scored, avg %.1f, %d cover letters",
                    profile.id,
                    eval_summary["jobs_evaluated"],
                    eval_summary["avg_score"],
                    eval_summary.get("cover_letters_generated", 0),
                )
            except Exception:
                logger.exception("Failed processing profile %d", profile.id)
                continue

    logger.info("Scheduled job complete")


def start_scheduler() -> AsyncIOScheduler:
    """Start the APScheduler with the daily job."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_scrape_and_evaluate,
        trigger=CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
        id="daily_scrape_evaluate",
        name="Daily scrape + evaluate",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — daily job at %02d:%02d UTC",
        SCHEDULE_HOUR,
        SCHEDULE_MINUTE,
    )
    return scheduler


def shutdown_scheduler(scheduler: AsyncIOScheduler):
    """Gracefully shut down the scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
