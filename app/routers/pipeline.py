"""
Pipeline router — scrape + enrich orchestration.

The pipeline runs synchronously within the request for observability and simplicity.
At ~10-15s for 30 articles it's acceptable; a production service would use
Celery/RQ workers with a job-status polling endpoint.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..enrichment.llm_enricher import enrich_batch, _client as llm_client
from ..enums import EnrichmentStatus
from ..models import Article
from ..schemas import PipelineRunResponse, PipelineStatsResponse
from ..scraper.hn_scraper import scrape_hn_front_page

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)


@router.get("/test-llm")
async def test_llm() -> dict:
    """
    Smoke-test the OpenAI connection with a minimal call (< 10 tokens).
    Returns status ok/error without touching the database.
    Use this to verify your API key and quota before running the pipeline.
    """
    try:
        response = await llm_client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_tokens=5,
        )
        reply = response.choices[0].message.content or ""
        return {
            "status": "ok",
            "model": settings.openai_model,
            "reply": reply.strip(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "model": settings.openai_model,
            "error": f"{type(exc).__name__}: {exc}",
        }


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(db: AsyncSession = Depends(get_db)) -> PipelineRunResponse:
    """
    Full pipeline: scrape HN front page → upsert new articles → enrich pending items.

    Already-enriched articles are never re-sent to the LLM (idempotent).
    """
    # 1. Scrape
    try:
        scraped_items = await scrape_hn_front_page()
    except Exception as exc:
        logger.error("Scraping failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Scraping failed: {exc}") from exc

    # 2. Upsert: insert new, refresh metadata for existing
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

    # 3. Collect all pending articles (includes any from previous failed runs)
    pending_result = await db.execute(
        select(Article).where(Article.enrichment_status == EnrichmentStatus.pending)
    )
    pending_articles = list(pending_result.scalars().all())

    if not pending_articles:
        return PipelineRunResponse(
            scraped=len(scraped_items),
            new_items=new_count,
            enriched=0,
            failed=0,
            message="Pipeline completed — no pending articles to enrich",
        )

    # Mark as processing to prevent concurrent pipeline runs from re-picking them
    for article in pending_articles:
        article.enrichment_status = EnrichmentStatus.processing
    await db.commit()

    # 4. Batch enrich
    article_payloads = [
        {"hn_id": a.hn_id, "title": a.title, "url": a.url}
        for a in pending_articles
    ]
    enrichment_results = await enrich_batch(article_payloads)

    # 5. Persist enrichment results
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

    return PipelineRunResponse(
        scraped=len(scraped_items),
        new_items=new_count,
        enriched=enriched_count,
        failed=failed_count,
        message="Pipeline completed successfully",
    )


@router.post("/retry", response_model=PipelineRunResponse)
async def retry_failed(db: AsyncSession = Depends(get_db)) -> PipelineRunResponse:
    """
    Re-enrich only articles that previously failed enrichment.
    Useful for recovering from transient LLM outages without re-scraping.
    """
    failed_result = await db.execute(
        select(Article).where(Article.enrichment_status == EnrichmentStatus.failed)
    )
    failed_articles = list(failed_result.scalars().all())

    if not failed_articles:
        return PipelineRunResponse(
            scraped=0,
            new_items=0,
            enriched=0,
            failed=0,
            message="No failed articles to retry",
        )

    for article in failed_articles:
        article.enrichment_status = EnrichmentStatus.processing
    await db.commit()

    article_payloads = [
        {"hn_id": a.hn_id, "title": a.title, "url": a.url}
        for a in failed_articles
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

    return PipelineRunResponse(
        scraped=0,
        new_items=0,
        enriched=enriched_count,
        failed=failed_count,
        message=f"Retry completed: {enriched_count} recovered, {failed_count} still failing",
    )


@router.get("/stats", response_model=PipelineStatsResponse)
async def pipeline_stats(db: AsyncSession = Depends(get_db)) -> PipelineStatsResponse:
    """Return a breakdown of articles by enrichment status."""
    rows = await db.execute(
        select(Article.enrichment_status, func.count().label("count"))
        .group_by(Article.enrichment_status)
    )
    counts = {row.enrichment_status: row.count for row in rows.all()}

    total = await db.scalar(select(func.count()).select_from(Article)) or 0

    return PipelineStatsResponse(
        total=total,
        pending=counts.get(EnrichmentStatus.pending, 0),
        processing=counts.get(EnrichmentStatus.processing, 0),
        completed=counts.get(EnrichmentStatus.completed, 0),
        failed=counts.get(EnrichmentStatus.failed, 0),
    )
