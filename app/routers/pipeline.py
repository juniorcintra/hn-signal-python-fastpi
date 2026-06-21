"""
Pipeline router — scrape + enrich orchestration with background jobs.

The pipeline now runs asynchronously in background to avoid blocking HTTP requests.
Jobs can be tracked via status endpoint and only one job runs at a time.
"""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..background_jobs import get_running_job_id, run_pipeline_job
from ..config import settings
from ..database import get_db
from ..enrichment.llm_enricher import _client as llm_client
from ..enums import EnrichmentStatus
from ..job_models import JobStatus, PipelineJob
from ..middleware import api_key_header, get_client_id, rate_limiter, verify_api_key
from ..models import Article
from ..schemas import JobResponse, JobStatusResponse, PipelineStatsResponse

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)


@router.get("/test-llm")
async def test_llm(
    request: Request,
    api_key: str | None = Depends(api_key_header),
) -> dict:
    """
    Smoke-test the OpenAI connection with a minimal call (< 10 tokens).
    Returns status ok/error without touching the database.
    Use this to verify your API key and quota before running the pipeline.
    
    Requires API key authentication and is rate-limited.
    """
    await verify_api_key(api_key)
    
    client_id = await get_client_id(request)
    await rate_limiter.check_rate_limit(client_id)
    
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


@router.post("/run", response_model=JobStatusResponse)
async def run_pipeline(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str | None = Depends(api_key_header),
) -> JobStatusResponse:
    """
    Start a background pipeline job: scrape HN front page → upsert → enrich pending items.
    
    Returns immediately with a job ID. Use GET /jobs/{job_id} to check status.
    Only one pipeline job can run at a time to prevent race conditions.
    
    Requires API key authentication and is rate-limited.
    """
    await verify_api_key(api_key)
    
    client_id = await get_client_id(request)
    await rate_limiter.check_rate_limit(client_id)
    
    running_job_id = await get_running_job_id()
    if running_job_id is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline job {running_job_id} is already running. Wait for it to complete.",
        )
    
    job = PipelineJob(status=JobStatus.pending)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    asyncio.create_task(run_pipeline_job(job.id))
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        message=f"Pipeline job {job.id} started in background",
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Get the status and results of a pipeline job.
    """
    job = await db.get(PipelineJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return JobResponse.model_validate(job)


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    """
    List recent pipeline jobs, ordered by creation time (newest first).
    """
    result = await db.execute(
        select(PipelineJob)
        .order_by(PipelineJob.created_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()
    return [JobResponse.model_validate(job) for job in jobs]


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
