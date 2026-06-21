import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal
from .enrichment.llm_enricher import enrich_batch
from .enums import EnrichmentStatus
from .job_models import JobStatus, PipelineJob
from .models import Article
from .scraper.hn_scraper import scrape_hn_front_page

logger = logging.getLogger(__name__)

_job_lock = asyncio.Lock()
_running_job_id: Optional[int] = None


async def get_running_job_id() -> Optional[int]:
    """Get the ID of the currently running job, if any."""
    return _running_job_id


async def run_pipeline_job(job_id: int) -> None:
    """
    Execute the pipeline in background.
    This function runs the full scrape + enrich flow and updates the job status.
    """
    global _running_job_id
    
    async with _job_lock:
        if _running_job_id is not None:
            logger.warning(
                "Attempted to start job %s but job %s is already running",
                job_id, _running_job_id
            )
            async with AsyncSessionLocal() as db:
                job = await db.get(PipelineJob, job_id)
                if job:
                    job.status = JobStatus.failed
                    job.error_message = f"Another job ({_running_job_id}) is already running"
                    await db.commit()
            return
        
        _running_job_id = job_id
    
    try:
        await _execute_pipeline(job_id)
    finally:
        async with _job_lock:
            _running_job_id = None


async def _execute_pipeline(job_id: int) -> None:
    """Internal pipeline execution logic."""
    async with AsyncSessionLocal() as db:
        job = await db.get(PipelineJob, job_id)
        if not job:
            logger.error("Job %s not found", job_id)
            return
        
        job.status = JobStatus.running
        job.started_at = datetime.utcnow()
        await db.commit()
        
        try:
            scraped_items = await scrape_hn_front_page()
            job.scraped = len(scraped_items)
            await db.commit()
            
            new_count = await _upsert_articles(db, scraped_items)
            job.new_items = new_count
            await db.commit()
            
            enriched, failed = await _enrich_pending_articles(db)
            job.enriched = enriched
            job.failed = failed
            
            job.status = JobStatus.completed
            job.completed_at = datetime.utcnow()
            await db.commit()
            
            logger.info(
                "Job %s completed: scraped=%s, new=%s, enriched=%s, failed=%s",
                job_id, job.scraped, job.new_items, job.enriched, job.failed
            )
            
        except Exception as exc:
            logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
            job.status = JobStatus.failed
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            await db.commit()


async def _upsert_articles(db: AsyncSession, scraped_items: list[dict]) -> int:
    """Upsert scraped articles into the database."""
    new_count = 0
    for item in scraped_items:
        existing = await db.scalar(
            select(Article).where(Article.hn_id == item["hn_id"])
        )
        if existing is None:
            db.add(Article(**item))
            new_count += 1
        else:
            existing.points = item["points"]
            existing.comments_count = item["comments_count"]
            existing.rank = item["rank"]
    
    await db.commit()
    return new_count


async def _enrich_pending_articles(db: AsyncSession) -> tuple[int, int]:
    """Enrich all pending articles and return (enriched_count, failed_count)."""
    pending_result = await db.execute(
        select(Article).where(Article.enrichment_status == EnrichmentStatus.pending)
    )
    pending_articles = list(pending_result.scalars().all())
    
    if not pending_articles:
        return 0, 0
    
    for article in pending_articles:
        article.enrichment_status = EnrichmentStatus.processing
    await db.commit()
    
    article_payloads = [
        {"hn_id": a.hn_id, "title": a.title, "url": a.url}
        for a in pending_articles
    ]
    enrichment_results = await enrich_batch(article_payloads)
    
    enriched_count = 0
    failed_count = 0
    
    for hn_id, enrichment, error in enrichment_results:
        article = await db.scalar(select(Article).where(Article.hn_id == hn_id))
        if article is None:
            continue
        
        if enrichment is not None:
            article.summary = enrichment.summary
            article.category = enrichment.category
            article.tags = enrichment.tags
            article.technical_level = enrichment.technical_level
            article.sentiment = enrichment.sentiment
            article.enrichment_status = EnrichmentStatus.completed
            article.enriched_at = datetime.utcnow()
            article.enrichment_error = None
            enriched_count += 1
        else:
            article.enrichment_status = EnrichmentStatus.failed
            article.enrichment_error = error
            failed_count += 1
    
    await db.commit()
    return enriched_count, failed_count
