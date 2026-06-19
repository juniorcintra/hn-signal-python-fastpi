"""
LLM-based article enrichment via OpenAI.

Design decisions:
- response_format=json_object guarantees valid JSON from the model, eliminating
  most JSONDecodeError scenarios. Pydantic validation still runs to enforce schema.
- Retries only on transient infrastructure errors (RateLimitError, APIError);
  validation errors are NOT retried — they indicate a model output issue, not infra.
- Semaphore limits concurrency to avoid rate-limit bursts.
- Titles are truncated before sending to control token cost.
- Temperature=0.2 reduces non-determinism and improves schema conformance.
"""

import asyncio
import json
import logging
from typing import Optional

from openai import APIError, AsyncOpenAI, RateLimitError
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import settings
from ..schemas import ArticleEnrichment

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM_PROMPT = """\
You are a content analyst for a tech news aggregator.
Given an article title (and optionally a URL), return a JSON object with EXACTLY these fields:

- summary    : string — one to two sentences describing what the article is likely about
- category   : one of ["technology", "science", "business", "politics", "entertainment", "other"]
- tags       : array of 2–5 lowercase strings (relevant topics or technologies)
- technical_level : one of ["beginner", "intermediate", "advanced", "non-technical"]
- sentiment  : one of ["positive", "negative", "neutral"]

Respond with ONLY valid JSON. No markdown fences, no extra keys, no explanation."""


# ---------------------------------------------------------------------------
# Single-item enrichment with retry on transient API errors
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((RateLimitError, APIError)),
    reraise=True,
)
async def _call_llm(title: str, url: Optional[str]) -> Optional[ArticleEnrichment]:
    """
    Call the LLM and validate the output against ArticleEnrichment.

    Returns None if output doesn't match the expected schema (logged as warning).
    Re-raises on unrecoverable API errors after retries.
    """
    truncated_title = title[: settings.llm_title_max_chars]
    user_content = f"Title: {truncated_title}"
    if url:
        user_content += f"\nURL: {url[:120]}"

    try:
        response = await _client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=settings.llm_max_tokens,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content or ""
        data = json.loads(raw_content)
        return ArticleEnrichment(**data)

    except json.JSONDecodeError as exc:
        logger.warning("LLM returned non-JSON for %r: %s", title[:60], exc)
        return None

    except ValidationError as exc:
        logger.warning(
            "LLM output failed schema validation for %r: %s", title[:60], exc
        )
        return None


# ---------------------------------------------------------------------------
# Batch enrichment with bounded concurrency
# ---------------------------------------------------------------------------

async def enrich_article(
    hn_id: str,
    title: str,
    url: Optional[str],
    semaphore: asyncio.Semaphore,
) -> tuple[str, Optional[ArticleEnrichment], Optional[str]]:
    """
    Enrich a single article within the shared semaphore.

    Returns (hn_id, enrichment_or_None, error_message_or_None).
    Never raises — all errors are captured and returned as a failed result.
    """
    async with semaphore:
        try:
            enrichment = await _call_llm(title, url)
            if enrichment is None:
                return hn_id, None, "LLM output did not pass schema validation"
            return hn_id, enrichment, None
        except Exception as exc:  # noqa: BLE001
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error("Enrichment failed for hn_id=%s: %s", hn_id, error_msg)
            return hn_id, None, error_msg


async def enrich_batch(
    articles: list[dict],
) -> list[tuple[str, Optional[ArticleEnrichment], Optional[str]]]:
    """
    Enrich a list of articles concurrently, bounded by LLM_CONCURRENCY.

    Each element of *articles* must have keys: hn_id, title, url.
    Returns a list of (hn_id, enrichment_or_None, error_or_None) tuples.
    """
    semaphore = asyncio.Semaphore(settings.llm_concurrency)
    tasks = [
        enrich_article(a["hn_id"], a["title"], a.get("url"), semaphore)
        for a in articles
    ]
    results = await asyncio.gather(*tasks)
    return list(results)
