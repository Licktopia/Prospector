"""Shared test fixtures."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.database import Base, get_session
from app.db.models import Profile, JobPosting
from app.main import app

TEST_DATABASE_URL = get_settings().test_database_url

# Module-level engine for schema management
_schema_initialized = False


async def _ensure_schema(url: str) -> None:
    """Create tables in the test database if not already done this session."""
    global _schema_initialized
    if _schema_initialized:
        return
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    _schema_initialized = True


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session against the test database with a rolled-back transaction."""
    await _ensure_schema(TEST_DATABASE_URL)

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        txn = await conn.begin()

        session_factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with session_factory() as session:
            yield session

        await txn.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield a test HTTP client with the session overridden."""

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_profile(session: AsyncSession) -> Profile:
    """Create a sample profile for testing."""
    profile = Profile(
        name="Test User",
        resume_pdf_path="resumes/test_resume.pdf",
        resume_text="Experienced software engineer with Python and AI expertise.",
        target_queries=["AI Engineer", "Python Developer"],
        target_locations=["Remote", "Denver, CO"],
    )
    session.add(profile)
    await session.flush()
    return profile


@pytest_asyncio.fixture
async def sample_job(session: AsyncSession, sample_profile: Profile) -> JobPosting:
    """Create a sample job posting for testing."""
    job = JobPosting(
        profile_id=sample_profile.id,
        job_title="Senior AI Engineer",
        company_name="Acme Corp",
        job_url="https://example.com/jobs/123",
        location="Remote",
        source="serpapi",
        job_description="Looking for an AI engineer...",
        application_status="new",
        search_query="AI Engineer",
    )
    session.add(job)
    await session.flush()
    return job
