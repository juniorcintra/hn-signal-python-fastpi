"""
Integration tests for the complete pipeline flow.

Tests cover:
- Full scrape + enrich flow with mocked external services
- Failure scenarios and retry logic
- Idempotency (articles not re-enriched)
- Background job execution and status tracking
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.integration

from app.background_jobs import run_pipeline_job
from app.enums import EnrichmentStatus
from app.job_models import JobStatus, PipelineJob
from app.models import Article
from app.schemas import ArticleEnrichment


@pytest.fixture
def mock_scraper_data():
    """Sample HN scraper output."""
    return [
        {
            "hn_id": "item1",
            "title": "Test Article 1",
            "url": "https://example.com/1",
            "points": 100,
            "comments_count": 50,
            "author": "user1",
            "rank": 1,
        },
        {
            "hn_id": "item2",
            "title": "Test Article 2",
            "url": "https://example.com/2",
            "points": 80,
            "comments_count": 30,
            "author": "user2",
            "rank": 2,
        },
    ]


@pytest.fixture
def mock_enrichment_success():
    """Mock successful enrichment response."""
    return ArticleEnrichment(
        summary="A test summary",
        category="technology",
        tags=["python", "testing"],
        technical_level="intermediate",
        sentiment="neutral",
    )


@pytest.mark.asyncio
async def test_full_pipeline_success(db_session, mock_scraper_data, mock_enrichment_success):
    """Test complete pipeline: scrape -> upsert -> enrich."""
    
    job = PipelineJob(status=JobStatus.pending)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    
    with patch("app.background_jobs.scrape_hn_front_page", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = mock_scraper_data
        
        with patch("app.background_jobs.enrich_batch", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = [
                ("item1", mock_enrichment_success, None),
                ("item2", mock_enrichment_success, None),
            ]
            
            await run_pipeline_job(job.id)
    
    await db_session.refresh(job)
    
    assert job.status == JobStatus.completed
    assert job.scraped == 2
    assert job.new_items == 2
    assert job.enriched == 2
    assert job.failed == 0
    
    articles = (await db_session.execute(select(Article))).scalars().all()
    assert len(articles) == 2
    
    for article in articles:
        assert article.enrichment_status == EnrichmentStatus.completed
        assert article.summary == "A test summary"
        assert article.category == "technology"
        assert article.tags == ["python", "testing"]


@pytest.mark.asyncio
async def test_pipeline_with_partial_failures(db_session, mock_scraper_data, mock_enrichment_success):
    """Test pipeline when some enrichments fail."""
    
    job = PipelineJob(status=JobStatus.pending)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    
    with patch("app.background_jobs.scrape_hn_front_page", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = mock_scraper_data
        
        with patch("app.background_jobs.enrich_batch", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = [
                ("item1", mock_enrichment_success, None),
                ("item2", None, "API rate limit exceeded"),
            ]
            
            await run_pipeline_job(job.id)
    
    await db_session.refresh(job)
    
    assert job.status == JobStatus.completed
    assert job.enriched == 1
    assert job.failed == 1
    
    article1 = (await db_session.execute(
        select(Article).where(Article.hn_id == "item1")
    )).scalar_one()
    assert article1.enrichment_status == EnrichmentStatus.completed
    
    article2 = (await db_session.execute(
        select(Article).where(Article.hn_id == "item2")
    )).scalar_one()
    assert article2.enrichment_status == EnrichmentStatus.failed
    assert article2.enrichment_error == "API rate limit exceeded"


@pytest.mark.asyncio
async def test_pipeline_idempotency(db_session, mock_scraper_data, mock_enrichment_success):
    """Test that already-enriched articles are not re-enriched."""
    
    existing_article = Article(
        hn_id="item1",
        title="Existing Article",
        url="https://example.com/existing",
        points=200,
        comments_count=100,
        author="existing_user",
        rank=1,
        enrichment_status=EnrichmentStatus.completed,
        summary="Already enriched",
        category="science",
        tags=["existing"],
        technical_level="advanced",
        sentiment="positive",
    )
    db_session.add(existing_article)
    await db_session.commit()
    
    job = PipelineJob(status=JobStatus.pending)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    
    with patch("app.background_jobs.scrape_hn_front_page", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = [
            {
                "hn_id": "item1",
                "title": "Updated Title",
                "url": "https://example.com/existing",
                "points": 250,
                "comments_count": 120,
                "author": "existing_user",
                "rank": 1,
            },
            mock_scraper_data[1],
        ]
        
        with patch("app.background_jobs.enrich_batch", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = [
                ("item2", mock_enrichment_success, None),
            ]
            
            await run_pipeline_job(job.id)
    
    await db_session.refresh(job)
    
    assert job.new_items == 1
    assert job.enriched == 1
    
    await db_session.refresh(existing_article)
    assert existing_article.points == 250
    assert existing_article.comments_count == 120
    assert existing_article.summary == "Already enriched"
    assert existing_article.category == "science"


@pytest.mark.asyncio
async def test_pipeline_scraper_failure(db_session):
    """Test pipeline behavior when scraper fails."""
    
    job = PipelineJob(status=JobStatus.pending)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    
    with patch("app.background_jobs.scrape_hn_front_page", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.side_effect = Exception("Network error")
        
        await run_pipeline_job(job.id)
    
    await db_session.refresh(job)
    
    assert job.status == JobStatus.failed
    assert "Network error" in job.error_message
    assert job.scraped == 0
    assert job.enriched == 0


@pytest.mark.asyncio
async def test_concurrent_pipeline_prevention(db_session):
    """Test that only one pipeline job can run at a time."""
    from app.background_jobs import _job_lock, _running_job_id
    
    job1 = PipelineJob(status=JobStatus.pending)
    job2 = PipelineJob(status=JobStatus.pending)
    db_session.add_all([job1, job2])
    await db_session.commit()
    await db_session.refresh(job1)
    await db_session.refresh(job2)
    
    async def slow_scrape():
        await asyncio.sleep(0.5)  # Simulate slow scraping
        return []
    
    async def slow_pipeline():
        with patch("app.background_jobs.scrape_hn_front_page", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = slow_scrape
            await run_pipeline_job(job1.id)
    
    task1 = asyncio.create_task(slow_pipeline())
    
    await asyncio.sleep(0.2)  # Wait for job1 to acquire lock
    
    # Mock the second job call too to avoid real API calls
    with patch("app.background_jobs.scrape_hn_front_page", new_callable=AsyncMock) as mock_scrape2:
        mock_scrape2.return_value = []
        await run_pipeline_job(job2.id)
    
    await task1
    
    await db_session.refresh(job2)
    assert job2.status == JobStatus.failed
    assert "already running" in job2.error_message.lower()
