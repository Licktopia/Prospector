"""Tests for the LangChain evaluator service."""

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Profile, JobPosting
from app.schemas.schemas import JobEvaluation
from app.services.evaluator import evaluate_jobs, _build_chain, _load_prompt


MOCK_EVALUATION = JobEvaluation(
    match_score=82,
    match_reasoning="Strong match due to Python and AI experience. The candidate's background in building ML pipelines aligns well with the role requirements.",
    cover_letter="Dear Hiring Manager,\n\nI am excited about the Senior AI Engineer role at Acme Corp...\n\nIn my previous role, I built production ML pipelines serving 1M+ requests daily...\n\nI would welcome the opportunity to bring this expertise to your team.",
)


def test_job_evaluation_schema():
    """JobEvaluation schema should validate correctly."""
    evaluation = JobEvaluation(
        match_score=75,
        match_reasoning="Good match.",
        cover_letter="Dear Hiring Manager...",
    )
    assert evaluation.match_score == 75
    assert evaluation.match_reasoning == "Good match."


def test_job_evaluation_score_bounds():
    """JobEvaluation should reject scores outside 1-100."""
    import pytest

    with pytest.raises(ValueError):
        JobEvaluation(match_score=0, match_reasoning="Bad", cover_letter="...")
    with pytest.raises(ValueError):
        JobEvaluation(match_score=101, match_reasoning="Bad", cover_letter="...")


def test_load_prompts():
    """Should load prompt files from the prompts directory."""
    system = _load_prompt("evaluator_system.txt")
    human = _load_prompt("evaluator_human.txt")
    assert "senior hiring evaluator" in system.lower()
    assert "{resume_text}" in human
    assert "{job_title}" in human


def test_build_chain():
    """Should build a runnable chain from prompt + model + structured output."""
    chain = _build_chain("fake-api-key", _load_prompt("evaluator_system.txt"))
    # Chain should be a RunnableSequence (prompt | model)
    assert chain is not None


@patch("app.services.evaluator._build_chain")
async def test_evaluate_jobs_processes_new_jobs(
    mock_build_chain: MagicMock,
    session: AsyncSession,
    sample_profile: Profile,
    sample_job: JobPosting,
):
    """Should evaluate new jobs and update their scores."""
    # Mock the chain's ainvoke to return our mock evaluation
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MOCK_EVALUATION
    mock_build_chain.return_value = mock_chain

    summary = await evaluate_jobs(sample_profile, session)

    assert summary["jobs_evaluated"] == 1
    assert summary["avg_score"] == 82.0

    # Verify the job was updated
    result = await session.execute(
        select(JobPosting).where(JobPosting.id == sample_job.id)
    )
    job = result.scalar_one()
    assert job.match_score == 82
    assert job.application_status == "evaluated"
    assert job.date_evaluated is not None
    assert "Python and AI" in job.match_reasoning
    assert job.cover_letter is not None


@patch("app.services.evaluator._build_chain")
async def test_evaluate_jobs_skips_evaluated(
    mock_build_chain: MagicMock,
    session: AsyncSession,
    sample_profile: Profile,
    sample_job: JobPosting,
):
    """Should only evaluate jobs with 'new' status."""
    # Mark the job as already evaluated
    sample_job.application_status = "evaluated"
    await session.flush()

    mock_chain = AsyncMock()
    mock_build_chain.return_value = mock_chain

    summary = await evaluate_jobs(sample_profile, session)

    assert summary["jobs_evaluated"] == 0
    mock_chain.ainvoke.assert_not_called()


@patch("app.services.evaluator._build_chain")
async def test_evaluate_jobs_handles_errors(
    mock_build_chain: MagicMock,
    session: AsyncSession,
    sample_profile: Profile,
    sample_job: JobPosting,
):
    """Should continue evaluating other jobs if one fails."""
    mock_chain = AsyncMock()
    mock_chain.ainvoke.side_effect = Exception("API error")
    mock_build_chain.return_value = mock_chain

    summary = await evaluate_jobs(sample_profile, session)

    assert summary["jobs_evaluated"] == 0
    # Job should still be 'new' since evaluation failed
    result = await session.execute(
        select(JobPosting).where(JobPosting.id == sample_job.id)
    )
    job = result.scalar_one()
    assert job.application_status == "new"


@patch("app.services.evaluator._build_chain")
async def test_evaluate_jobs_uses_custom_prompt(
    mock_build_chain: MagicMock,
    session: AsyncSession,
    sample_profile: Profile,
    sample_job: JobPosting,
):
    """Should use the profile's custom evaluator prompt when set."""
    sample_profile.evaluator_prompt = "You are a custom evaluator."
    await session.flush()

    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MOCK_EVALUATION
    mock_build_chain.return_value = mock_chain

    await evaluate_jobs(sample_profile, session)

    # Verify _build_chain was called with the custom prompt
    mock_build_chain.assert_called_once()
    call_args = mock_build_chain.call_args
    assert call_args[0][1] == "You are a custom evaluator."


@patch("app.api.profiles.evaluate_jobs")
async def test_evaluate_endpoint(
    mock_evaluate: MagicMock,
    client: AsyncClient,
    sample_profile: Profile,
):
    """Should trigger evaluation via the API endpoint."""
    mock_evaluate.return_value = {"jobs_evaluated": 5, "avg_score": 72.4}

    response = await client.post(f"/api/profiles/{sample_profile.id}/evaluate")
    assert response.status_code == 200
    data = response.json()
    assert data["profile_id"] == sample_profile.id
    assert data["jobs_evaluated"] == 5
    assert data["avg_score"] == 72.4


async def test_evaluate_endpoint_not_found(client: AsyncClient):
    """Should return 404 for nonexistent profile."""
    response = await client.post("/api/profiles/9999/evaluate")
    assert response.status_code == 404
