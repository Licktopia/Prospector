"""SQLAlchemy ORM models for Prospector."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Profile(Base):
    """A job seeker with their own resume, target roles, and locations."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    resume_pdf_path: Mapped[str] = mapped_column(String, nullable=False)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_queries: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    target_locations: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    evaluator_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job_postings: Mapped[list["JobPosting"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Profile id={self.id} name={self.name!r}>"


class JobPosting(Base):
    """A scraped job posting tied to a specific profile."""

    __tablename__ = "job_postings"

    __table_args__ = (
        UniqueConstraint("profile_id", "job_url", name="uq_profile_job_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id"), nullable=False
    )
    job_title: Mapped[str] = mapped_column(String, nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    job_url: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_links: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    application_status: Mapped[str] = mapped_column(String, default="new")
    search_query: Mapped[str | None] = mapped_column(String, nullable=True)
    date_added: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    date_evaluated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    profile: Mapped["Profile"] = relationship(back_populates="job_postings")

    def __repr__(self) -> str:
        return f"<JobPosting id={self.id} title={self.job_title!r} company={self.company_name!r}>"
