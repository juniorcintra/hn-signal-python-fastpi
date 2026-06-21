"""
Tests for authentication and rate limiting.
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.config import settings
from app.middleware import RateLimiter

pytestmark = pytest.mark.security


@pytest.mark.asyncio
async def test_pipeline_requires_api_key(client: AsyncClient):
    """Test that pipeline endpoints require API key when configured."""
    
    if not settings.api_key:
        pytest.skip("API key not configured")
    
    response = await client.post("/api/v1/pipeline/run")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "API key required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_pipeline_with_invalid_api_key(client: AsyncClient):
    """Test that invalid API key is rejected."""
    
    if not settings.api_key:
        pytest.skip("API key not configured")
    
    response = await client.post(
        "/api/v1/pipeline/run",
        headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Invalid API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_pipeline_with_valid_api_key(client: AsyncClient):
    """Test that valid API key allows access."""
    
    if not settings.api_key:
        pytest.skip("API key not configured")
    
    response = await client.post(
        "/api/v1/pipeline/run",
        headers={"X-API-Key": settings.api_key}
    )
    
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_409_CONFLICT]


@pytest.mark.asyncio
async def test_test_llm_requires_api_key(client: AsyncClient):
    """Test that LLM test endpoint requires API key."""
    
    if not settings.api_key:
        pytest.skip("API key not configured")
    
    response = await client.get("/api/v1/pipeline/test-llm")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = RateLimiter(requests_per_minute=3)
    
    await limiter.check_rate_limit("client1")
    await limiter.check_rate_limit("client1")
    await limiter.check_rate_limit("client1")
    
    with pytest.raises(Exception) as exc_info:
        await limiter.check_rate_limit("client1")
    
    assert "Rate limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rate_limiter_different_clients():
    """Test that rate limiter tracks clients separately."""
    limiter = RateLimiter(requests_per_minute=2)
    
    await limiter.check_rate_limit("client1")
    await limiter.check_rate_limit("client1")
    
    await limiter.check_rate_limit("client2")
    await limiter.check_rate_limit("client2")
    
    with pytest.raises(Exception):
        await limiter.check_rate_limit("client1")
    
    with pytest.raises(Exception):
        await limiter.check_rate_limit("client2")


@pytest.mark.asyncio
async def test_public_endpoints_no_auth(client: AsyncClient):
    """Test that public endpoints don't require authentication."""
    
    response = await client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    
    response = await client.get("/api/v1/articles")
    assert response.status_code == status.HTTP_200_OK
    
    response = await client.get("/api/v1/pipeline/stats")
    assert response.status_code == status.HTTP_200_OK
