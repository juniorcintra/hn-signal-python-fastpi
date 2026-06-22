"""
Shared pytest fixtures.

Sets DATABASE_URL to an in-memory SQLite before any app module is imported,
so the module-level engine in database.py targets memory instead of a file.
StaticPool ensures all connections (lifespan + test sessions) share the same
in-memory database.
"""

import os

# Must be set before any app module is imported (pydantic-settings reads at __init__)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-not-real")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.job_models import PipelineJob  # noqa: F401 - Import necessário para criar tabela
from app.main import app
from app.models import Article  # noqa: F401 - Import necessário para criar tabela

_SHARED_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SESSION_FACTORY = async_sessionmaker(_SHARED_ENGINE, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_tables():
    """Create all tables once per test session in the shared in-memory DB."""
    async with _SHARED_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _SHARED_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Provide a database session that rolls back after each test."""
    async with _SESSION_FACTORY() as session:
        # Limpar tabelas antes de cada teste
        await session.execute(Article.__table__.delete())
        await session.execute(PipelineJob.__table__.delete())
        await session.commit()
        
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """
    HTTP test client with get_db overridden to use the test session.
    The lifespan runs normally but init_db() targets the shared in-memory engine
    because DATABASE_URL was patched at module load time.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
