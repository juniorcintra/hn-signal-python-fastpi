"""
Hacker News front-page scraper.

Uses httpx (async) + BeautifulSoup (static HTML parsing).
BeautifulSoup is sufficient because HN delivers a fully server-rendered page —
no JavaScript rendering, infinite scroll, or authentication is needed.
"""

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

logger = logging.getLogger(__name__)

HN_URL = "https://news.ycombinator.com/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; HNEnricher/1.0; +https://github.com/example/hn-enricher)"
    )
}


# ---------------------------------------------------------------------------
# HTTP fetch — retried on network errors, not on 4xx/5xx (those are raised)
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(settings.scraper_max_retries),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _fetch(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=settings.scraper_timeout,
        headers=_HEADERS,
        follow_redirects=True,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_int(text: Optional[str], pattern: str = r"\d+") -> int:
    """Extract first integer from *text*; return 0 on failure."""
    if not text:
        return 0
    match = re.search(pattern, text)
    return int(match.group()) if match else 0


def _parse_articles(html: str) -> list[dict]:
    """
    Parse HN front-page HTML into a list of article dicts.

    HN structure (simplified):
        <tr class="athing" id="{hn_id}">
          <td class="title">
            <span class="rank">{rank}.</span>
            <span class="titleline">
              <a href="{url}">{title}</a>
            </span>
          </td>
        </tr>
        <tr>                        ← immediately following row
          <td class="subtext">
            <span class="score">{points} points</span>
            <a class="hnuser">{author}</a>
            <span class="age"> ...
            <a ...>{comments} comments</a>
          </td>
        </tr>
    """
    soup = BeautifulSoup(html, "lxml")
    articles: list[dict] = []

    story_rows = soup.select("tr.athing")
    for row in story_rows:
        try:
            hn_id: str = row.get("id", "").strip()
            if not hn_id:
                continue

            rank_el = row.select_one(".rank")
            title_el = row.select_one(".titleline > a")

            if not title_el:
                continue

            rank = _parse_int(rank_el.get_text() if rank_el else "0")
            title = title_el.get_text(strip=True)

            url: str = title_el.get("href", "") or ""
            if url.startswith("item?"):
                url = f"https://news.ycombinator.com/{url}"

            # Metadata lives in the next sibling <tr>
            subtext_row = row.find_next_sibling("tr")
            points = 0
            author = "unknown"
            comments_count = 0

            if subtext_row:
                score_el = subtext_row.select_one(".score")
                author_el = subtext_row.select_one(".hnuser")

                points = _parse_int(score_el.get_text() if score_el else None)
                author = author_el.get_text(strip=True) if author_el else "unknown"

                for link in subtext_row.select("a"):
                    link_text = link.get_text(strip=True).lower()
                    if "comment" in link_text:
                        comments_count = _parse_int(link_text)
                        break

            articles.append(
                {
                    "hn_id": hn_id,
                    "title": title,
                    "url": url or None,
                    "points": points,
                    "comments_count": comments_count,
                    "author": author,
                    "rank": rank,
                }
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping article row due to parse error: %s", exc)
            continue

    return articles


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

async def scrape_hn_front_page() -> list[dict]:
    """
    Fetch and parse the HN front page.

    Returns a list of article dicts ready for DB insertion.
    Raises on unrecoverable fetch errors (after retries).
    """
    logger.info("Fetching HN front page: %s", HN_URL)
    html = await _fetch(HN_URL)
    articles = _parse_articles(html)
    logger.info("Parsed %d articles from HN front page", len(articles))
    return articles
