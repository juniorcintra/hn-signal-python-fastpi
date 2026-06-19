from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, func, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..enums import EnrichmentStatus
from ..models import Article
from ..schemas import ArticleResponse, CategoriesResponse, PaginatedArticlesResponse

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


@router.get("", response_model=PaginatedArticlesResponse)
async def list_articles(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag (substring match)"),
    enrichment_status: Optional[str] = Query(
        None,
        description=(
            "Filter by enrichment status. "
            f"Valid values: {[e.value for e in EnrichmentStatus]}"
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> PaginatedArticlesResponse:
    # Normalize empty strings (e.g. from ?param=) to None before any further processing
    category = category or None
    tag = tag or None

    parsed_status: Optional[EnrichmentStatus] = None
    if enrichment_status:
        try:
            parsed_status = EnrichmentStatus(enrichment_status)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid enrichment_status '{enrichment_status}'. "
                    f"Must be one of: {[e.value for e in EnrichmentStatus]}"
                ),
            )

    base_filter = _build_filters(category, tag, parsed_status)

    total: int = await db.scalar(
        select(func.count()).select_from(Article).where(*base_filter)
    )

    result = await db.execute(
        select(Article)
        .where(*base_filter)
        .order_by(Article.rank)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    articles = result.scalars().all()

    return PaginatedArticlesResponse(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=articles,
    )


@router.get("/categories", response_model=CategoriesResponse)
async def list_categories(db: AsyncSession = Depends(get_db)) -> CategoriesResponse:
    result = await db.execute(
        select(Article.category)
        .where(Article.category.isnot(None))
        .distinct()
        .order_by(Article.category)
    )
    categories = [row[0] for row in result.all()]
    return CategoriesResponse(categories=categories)


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int, db: AsyncSession = Depends(get_db)
) -> ArticleResponse:
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_filters(
    category: Optional[str],
    tag: Optional[str],
    enrichment_status: Optional[EnrichmentStatus],
) -> list:
    filters = []

    if category:
        filters.append(Article.category == category)

    if tag:
        # SQLite stores JSON as text; using LIKE on the string representation
        # is a pragmatic approach. On PostgreSQL, GIN index + @> would be used.
        filters.append(cast(Article.tags, String).like(f'%"{tag}"%'))

    if enrichment_status:
        filters.append(Article.enrichment_status == enrichment_status)

    return filters
