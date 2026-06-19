from datetime import datetime
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field

from .enums import EnrichmentStatus


# ---------------------------------------------------------------------------
# LLM output schema — validated immediately after model response
# ---------------------------------------------------------------------------

class ArticleEnrichment(BaseModel):
    summary: Annotated[str, Field(min_length=10, max_length=500)]
    category: Literal[
        "technology", "science", "business", "politics", "entertainment", "other"
    ]
    tags: Annotated[List[str], Field(min_length=1, max_length=5)]
    technical_level: Literal["beginner", "intermediate", "advanced", "non-technical"]
    sentiment: Literal["positive", "negative", "neutral"]


# ---------------------------------------------------------------------------
# API response schemas
# ---------------------------------------------------------------------------

class ArticleResponse(BaseModel):
    id: int
    hn_id: str
    title: str
    url: Optional[str] = None
    points: int
    comments_count: int
    author: str
    rank: int
    scraped_at: datetime
    enrichment_status: EnrichmentStatus
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    technical_level: Optional[str] = None
    sentiment: Optional[str] = None
    enriched_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedArticlesResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ArticleResponse]


class CategoriesResponse(BaseModel):
    categories: List[str]


# ---------------------------------------------------------------------------
# Pipeline schemas
# ---------------------------------------------------------------------------

class PipelineRunResponse(BaseModel):
    scraped: int
    new_items: int
    enriched: int
    failed: int
    message: str


class PipelineStatsResponse(BaseModel):
    total: int
    pending: int
    processing: int
    completed: int
    failed: int


# ---------------------------------------------------------------------------
# Health schema
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
