"""
Integration tests for the HTTP layer.

All tests run against an in-memory SQLite DB (see conftest.py).
No network calls are made (scraper and LLM are not invoked).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import EnrichmentStatus
from app.models import Article


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(**kwargs) -> Article:
    defaults = dict(
        hn_id="99001",
        title="Default Test Article",
        url="https://example.com",
        points=100,
        comments_count=20,
        author="tester",
        rank=1,
        enrichment_status=EnrichmentStatus.completed,
        summary="A test article about software engineering.",
        category="technology",
        tags=["python", "testing"],
        technical_level="intermediate",
        sentiment="neutral",
    )
    defaults.update(kwargs)
    return Article(**defaults)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    async def test_returns_200(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_response_shape(self, client: AsyncClient):
        data = (await client.get("/health")).json()
        assert data["status"] == "ok"
        assert "database" in data
        assert "version" in data


# ---------------------------------------------------------------------------
# List articles
# ---------------------------------------------------------------------------

class TestListArticles:
    async def test_empty_db_returns_empty_list(self, client: AsyncClient):
        response = await client.get("/api/v1/articles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_returns_seeded_article(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_article(hn_id="10001"))
        await db_session.commit()

        response = await client.get("/api/v1/articles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["hn_id"] == "10001"

    async def test_pagination_page_size(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        for i in range(5):
            db_session.add(_make_article(hn_id=f"2000{i}", rank=i + 1))
        await db_session.commit()

        response = await client.get("/api/v1/articles?page=1&page_size=3")
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5

    async def test_filter_by_category(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_article(hn_id="30001", category="technology"))
        db_session.add(_make_article(hn_id="30002", category="science"))
        await db_session.commit()

        response = await client.get("/api/v1/articles?category=science")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "science"

    async def test_filter_by_enrichment_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(
            _make_article(hn_id="40001", enrichment_status=EnrichmentStatus.completed)
        )
        db_session.add(
            _make_article(hn_id="40002", enrichment_status=EnrichmentStatus.failed)
        )
        await db_session.commit()

        response = await client.get("/api/v1/articles?enrichment_status=failed")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["hn_id"] == "40002"

    async def test_invalid_page_returns_422(self, client: AsyncClient):
        assert (await client.get("/api/v1/articles?page=0")).status_code == 422

    async def test_invalid_page_size_too_large_returns_422(self, client: AsyncClient):
        assert (await client.get("/api/v1/articles?page_size=101")).status_code == 422


# ---------------------------------------------------------------------------
# Get single article
# ---------------------------------------------------------------------------

class TestGetArticle:
    async def test_returns_article(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        article = _make_article(hn_id="50001")
        db_session.add(article)
        await db_session.commit()
        await db_session.refresh(article)

        response = await client.get(f"/api/v1/articles/{article.id}")
        assert response.status_code == 200
        assert response.json()["hn_id"] == "50001"

    async def test_not_found_returns_404(self, client: AsyncClient):
        response = await client.get("/api/v1/articles/999999")
        assert response.status_code == 404

    async def test_response_contains_enrichment_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        article = _make_article(hn_id="60001")
        db_session.add(article)
        await db_session.commit()
        await db_session.refresh(article)

        data = (await client.get(f"/api/v1/articles/{article.id}")).json()
        assert data["summary"] == "A test article about software engineering."
        assert data["category"] == "technology"
        assert data["tags"] == ["python", "testing"]


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class TestCategories:
    async def test_returns_distinct_categories(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(_make_article(hn_id="70001", category="technology"))
        db_session.add(_make_article(hn_id="70002", category="science"))
        db_session.add(_make_article(hn_id="70003", category="technology"))
        await db_session.commit()

        data = (await client.get("/api/v1/articles/categories")).json()
        assert set(data["categories"]) == {"technology", "science"}

    async def test_excludes_null_categories(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(
            _make_article(
                hn_id="80001",
                category=None,
                enrichment_status=EnrichmentStatus.pending,
                summary=None,
                tags=None,
                technical_level=None,
                sentiment=None,
            )
        )
        await db_session.commit()

        data = (await client.get("/api/v1/articles/categories")).json()
        assert None not in data["categories"]


# ---------------------------------------------------------------------------
# Pipeline stats
# ---------------------------------------------------------------------------

class TestPipelineStats:
    async def test_empty_db(self, client: AsyncClient):
        data = (await client.get("/api/v1/pipeline/stats")).json()
        assert data["total"] == 0
        assert data["pending"] == 0
        assert data["completed"] == 0

    async def test_counts_by_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        db_session.add(
            _make_article(hn_id="90001", enrichment_status=EnrichmentStatus.completed)
        )
        db_session.add(
            _make_article(hn_id="90002", enrichment_status=EnrichmentStatus.failed)
        )
        db_session.add(
            _make_article(
                hn_id="90003",
                enrichment_status=EnrichmentStatus.pending,
                summary=None,
                category=None,
                tags=None,
                technical_level=None,
                sentiment=None,
            )
        )
        await db_session.commit()

        data = (await client.get("/api/v1/pipeline/stats")).json()
        assert data["total"] == 3
        assert data["completed"] == 1
        assert data["failed"] == 1
        assert data["pending"] == 1
