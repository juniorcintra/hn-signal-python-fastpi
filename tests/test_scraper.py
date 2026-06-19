"""
Unit tests for the HN scraper parser.

All tests are pure (no network calls) — they exercise _parse_articles and
_parse_int with controlled HTML fixtures.
"""

import pytest

from app.scraper.hn_scraper import _parse_articles, _parse_int

# ---------------------------------------------------------------------------
# Minimal HTML that mirrors the real HN structure the parser depends on
# ---------------------------------------------------------------------------

_FIXTURE_TWO_ITEMS = """<!doctype html>
<html><body><table>
  <tr class="athing" id="11111">
    <td class="title"><span class="rank">1.</span></td>
    <td class="title">
      <span class="titleline">
        <a href="https://example.com/article">Example Article</a>
      </span>
    </td>
  </tr>
  <tr>
    <td class="subtext">
      <span class="score" id="score_11111">42 points</span>
      by <a class="hnuser">alice</a>
      | <a href="item?id=11111">15 comments</a>
    </td>
  </tr>
  <tr class="athing" id="22222">
    <td class="title"><span class="rank">2.</span></td>
    <td class="title">
      <span class="titleline">
        <a href="item?id=22222">Ask HN: No External Link</a>
      </span>
    </td>
  </tr>
  <tr>
    <td class="subtext">
      <span class="score" id="score_22222">5 points</span>
      by <a class="hnuser">bob</a>
      | <a href="item?id=22222">discuss</a>
    </td>
  </tr>
</table></body></html>"""

_FIXTURE_MISSING_SCORE = """<!doctype html>
<html><body><table>
  <tr class="athing" id="33333">
    <td class="title"><span class="rank">1.</span></td>
    <td class="title">
      <span class="titleline">
        <a href="https://example.com">No Score Item</a>
      </span>
    </td>
  </tr>
  <tr>
    <td class="subtext">
      by <a class="hnuser">carol</a>
    </td>
  </tr>
</table></body></html>"""

_FIXTURE_EMPTY = """<!doctype html><html><body><table></table></body></html>"""


# ---------------------------------------------------------------------------
# _parse_int
# ---------------------------------------------------------------------------

class TestParseInt:
    def test_extracts_integer_from_text(self):
        assert _parse_int("42 points") == 42

    def test_extracts_from_comment_text(self):
        assert _parse_int("15 comments") == 15

    def test_returns_zero_for_none(self):
        assert _parse_int(None) == 0

    def test_returns_zero_for_no_digits(self):
        assert _parse_int("discuss") == 0

    def test_returns_zero_for_empty_string(self):
        assert _parse_int("") == 0

    def test_extracts_first_integer(self):
        assert _parse_int("100 points by 3 users") == 100


# ---------------------------------------------------------------------------
# _parse_articles
# ---------------------------------------------------------------------------

class TestParseArticles:
    def test_returns_two_items(self):
        articles = _parse_articles(_FIXTURE_TWO_ITEMS)
        assert len(articles) == 2

    def test_first_item_fields(self):
        articles = _parse_articles(_FIXTURE_TWO_ITEMS)
        first = articles[0]
        assert first["hn_id"] == "11111"
        assert first["title"] == "Example Article"
        assert first["url"] == "https://example.com/article"
        assert first["points"] == 42
        assert first["author"] == "alice"
        assert first["rank"] == 1
        assert first["comments_count"] == 15

    def test_hn_relative_link_is_normalised(self):
        articles = _parse_articles(_FIXTURE_TWO_ITEMS)
        second = articles[1]
        assert second["url"].startswith("https://news.ycombinator.com/item?")

    def test_missing_score_defaults_to_zero(self):
        articles = _parse_articles(_FIXTURE_MISSING_SCORE)
        assert len(articles) == 1
        assert articles[0]["points"] == 0
        assert articles[0]["author"] == "carol"

    def test_empty_html_returns_empty_list(self):
        assert _parse_articles(_FIXTURE_EMPTY) == []

    def test_each_item_has_required_keys(self):
        required = {"hn_id", "title", "url", "points", "comments_count", "author", "rank"}
        for article in _parse_articles(_FIXTURE_TWO_ITEMS):
            assert required.issubset(article.keys())
