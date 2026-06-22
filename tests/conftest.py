"""
Shared pytest fixtures - SIMPLIFIED VERSION.
"""

import os
import tempfile

# Create a temporary SQLite file for tests
_TEST_DB_FILE = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TEST_DB_PATH = _TEST_DB_FILE.name
_TEST_DB_FILE.close()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-not-real")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Create shared test engine using temporary file
_TEST_ENGINE = create_async_engine(
    f"sqlite+aiosqlite:///{_TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
_TEST_SESSION_FACTORY = async_sessionmaker(
    _TEST_ENGINE, 
    expire_on_commit=False,
    class_=AsyncSession,
)

# Import and patch app.database BEFORE any other app imports
import app.database
app.database.engine = _TEST_ENGINE
app.database.AsyncSessionLocal = _TEST_SESSION_FACTORY

# Import and patch app.background_jobs
import app.background_jobs  
app.background_jobs.AsyncSessionLocal = _TEST_SESSION_FACTORY

# Import and patch app.main
import app.main
app.main.AsyncSessionLocal = _TEST_SESSION_FACTORY

# Now safe to import other app modules
from app.database import Base, get_db
from app.models import Article
from app.job_models import PipelineJob
from fastapi import FastAPI
import app.main as main_module

# Create test app WITHOUT lifespan
app = FastAPI(
    title="HN Article Enricher",
    description="Test version without lifespan",
    version="1.0.0",
)
# Copy routes from original app
app.router = main_module.app.router


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_test_db():
    """Create tables once for entire test session."""
    async with _TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Clean up temporary database file
    await _TEST_ENGINE.dispose()
    import os
    if os.path.exists(_TEST_DB_PATH):
        os.unlink(_TEST_DB_PATH)


@pytest_asyncio.fixture
async def db_session(_setup_test_db) -> AsyncSession:
    """Provide a test database session with clean tables."""
    async with _TEST_SESSION_FACTORY() as session:
        # Clean tables before each test
        await session.execute(Article.__table__.delete())
        await session.execute(PipelineJob.__table__.delete())
        await session.commit()
        
        yield session
        
        # Rollback any uncommitted changes
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """Provide HTTP test client."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
