"""
Unit tests for the LLM output schema (ArticleEnrichment).

These tests verify that Pydantic catches all invalid LLM outputs — the main
defence against non-deterministic model responses.
"""

import pytest
from pydantic import ValidationError

from app.schemas import ArticleEnrichment

_VALID = dict(
    summary="This article discusses a new approach to machine learning.",
    category="technology",
    tags=["machine-learning", "ai"],
    technical_level="advanced",
    sentiment="neutral",
)


class TestArticleEnrichmentValid:
    def test_valid_input_passes(self):
        e = ArticleEnrichment(**_VALID)
        assert e.category == "technology"
        assert e.sentiment == "neutral"

    def test_maximum_tags_accepted(self):
        e = ArticleEnrichment(**{**_VALID, "tags": ["a", "b", "c", "d", "e"]})
        assert len(e.tags) == 5

    def test_minimum_tags_accepted(self):
        e = ArticleEnrichment(**{**_VALID, "tags": ["single"]})
        assert len(e.tags) == 1


class TestArticleEnrichmentInvalid:
    def test_invalid_category_raises(self):
        with pytest.raises(ValidationError):
            ArticleEnrichment(**{**_VALID, "category": "sports"})

    def test_invalid_sentiment_raises(self):
        with pytest.raises(ValidationError):
            ArticleEnrichment(**{**_VALID, "sentiment": "very_positive"})

    def test_invalid_technical_level_raises(self):
        with pytest.raises(ValidationError):
            ArticleEnrichment(**{**_VALID, "technical_level": "expert"})

    def test_summary_too_short_raises(self):
        with pytest.raises(ValidationError):
            ArticleEnrichment(**{**_VALID, "summary": "Short."})

    def test_too_many_tags_raises(self):
        with pytest.raises(ValidationError):
            ArticleEnrichment(**{**_VALID, "tags": ["a", "b", "c", "d", "e", "f"]})

    def test_empty_tags_raises(self):
        with pytest.raises(ValidationError):
            ArticleEnrichment(**{**_VALID, "tags": []})

    def test_missing_field_raises(self):
        incomplete = {k: v for k, v in _VALID.items() if k != "category"}
        with pytest.raises(ValidationError):
            ArticleEnrichment(**incomplete)
