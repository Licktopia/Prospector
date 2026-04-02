"""Pydantic schemas for request/response models and LLM structured output."""

from pydantic import BaseModel, Field


class JobScore(BaseModel):
    """Structured output from the LLM scoring pass (no cover letter)."""

    match_score: int = Field(
        ...,
        ge=1,
        le=100,
        description="Match score from 1-100 based on resume fit to the job posting",
    )
    match_reasoning: str = Field(
        ...,
        description="2-3 sentences explaining why this score was given, referencing specific qualifications",
    )


class JobEvaluation(JobScore):
    """Full evaluation including cover letter, used for high-scoring jobs."""

    cover_letter: str = Field(
        ...,
        description="3-paragraph cover letter: hook, evidence from resume mapped to JD, close",
    )


class CoverLetterResult(BaseModel):
    """Structured output for on-demand cover letter generation."""

    cover_letter: str = Field(
        ...,
        description="3-paragraph cover letter: hook, evidence from resume mapped to JD, close",
    )
