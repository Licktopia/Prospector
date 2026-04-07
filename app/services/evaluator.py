"""LangChain-powered job evaluation pipeline using Claude.

Single-pass scoring: scores all jobs quickly with brief reasoning.
Cover letters are generated on demand via generate_cover_letter().
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import JobPosting, Profile
from app.schemas.schemas import CoverLetterResult, JobScore

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Model identifiers for LangChain
MODELS = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
}


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _build_scoring_chain(api_key: str, system_prompt: str):
    """Build a chain that scores a job without generating a cover letter.

    Uses the JobScore schema (score + reasoning only) for faster, cheaper evaluation.
    """
    llm = ChatAnthropic(
        model=MODELS["sonnet"],
        api_key=api_key,
        max_tokens=256,
    )
    structured_llm = llm.with_structured_output(JobScore)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", _load_prompt("evaluator_human.txt")),
    ])

    return prompt | structured_llm


def _build_cover_letter_chain(api_key: str, model: str = "sonnet"):
    """Build a chain for on-demand cover letter generation.

    Supports model selection (sonnet for speed, opus for quality).
    """
    model_id = MODELS.get(model, MODELS["sonnet"])
    llm = ChatAnthropic(
        model=model_id,
        api_key=api_key,
        max_tokens=2048,
    )
    structured_llm = llm.with_structured_output(CoverLetterResult)

    system_prompt = _load_prompt("evaluator_system.txt")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", _load_prompt("evaluator_human.txt")),
    ])

    return prompt | structured_llm


async def evaluate_jobs(profile: Profile, session: AsyncSession) -> dict[str, int | float]:
    """Score all unevaluated jobs for a profile using LangChain + Claude.

    Single-pass scoring only — cover letters are generated on demand.
    Returns a summary dict with counts and average score.
    """
    settings = get_settings()

    # Get unevaluated jobs
    result = await session.execute(
        select(JobPosting).where(
            JobPosting.profile_id == profile.id,
            JobPosting.application_status == "new",
        )
    )
    jobs = result.scalars().all()

    if not jobs:
        logger.info("No unevaluated jobs for profile %d", profile.id)
        return {"jobs_evaluated": 0, "avg_score": 0}

    # Build scoring chain
    scorer_prompt = _load_prompt("scorer_system.txt")
    system_prompt = profile.evaluator_prompt or scorer_prompt
    scoring_chain = _build_scoring_chain(settings.anthropic_api_key, system_prompt)

    evaluated = 0
    total_score = 0

    for job in jobs:
        logger.info(
            "Scoring job %d: %s at %s", job.id, job.job_title, job.company_name
        )

        invoke_args = {
            "resume_text": profile.resume_text or "No resume text available.",
            "job_title": job.job_title,
            "company_name": job.company_name,
            "location": job.location or "Not specified",
            "job_description": job.job_description or "No description available.",
        }

        try:
            score_result: JobScore = await scoring_chain.ainvoke(invoke_args)

            job.match_score = score_result.match_score
            job.match_reasoning = score_result.match_reasoning
            job.application_status = "evaluated"
            job.date_evaluated = datetime.now(timezone.utc)

            evaluated += 1
            total_score += score_result.match_score

            logger.info(
                "Job %d scored %d/100: %s",
                job.id, score_result.match_score, score_result.match_reasoning[:80],
            )

        except Exception:
            logger.exception("Failed to evaluate job %d", job.id)
            continue

        # Rate limit: small delay between API calls
        await asyncio.sleep(0.5)

    await session.commit()

    avg_score = round(total_score / evaluated, 1) if evaluated else 0
    summary = {
        "jobs_evaluated": evaluated,
        "avg_score": avg_score,
    }

    logger.info(
        "Evaluation complete for profile %d: %d jobs, avg score %.1f",
        profile.id, evaluated, avg_score,
    )
    return summary


async def generate_cover_letter(
    job: JobPosting, profile: Profile, session: AsyncSession, model: str = "sonnet"
) -> str:
    """Generate a cover letter on demand for a specific job.

    Allows model selection — use 'opus' for higher quality on important applications.
    If the job hasn't been scored yet, it will be scored first.
    """
    settings = get_settings()
    chain = _build_cover_letter_chain(settings.anthropic_api_key, model)

    logger.info(
        "Generating cover letter for job %d with model %s", job.id, model
    )

    result: CoverLetterResult = await chain.ainvoke({
        "resume_text": profile.resume_text or "No resume text available.",
        "job_title": job.job_title,
        "company_name": job.company_name,
        "location": job.location or "Not specified",
        "job_description": job.job_description or "No description available.",
    })

    job.cover_letter = result.cover_letter
    await session.commit()

    logger.info("Cover letter generated for job %d", job.id)
    return result.cover_letter
