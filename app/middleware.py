import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = None) -> None:
    """
    Verify API key for protected endpoints.
    Raises HTTPException if key is invalid or missing.
    """
    if not settings.api_key:
        return
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
        )
    
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )


class RateLimiter:
    """
    Simple in-memory rate limiter.
    For production, use Redis-backed solution like slowapi or fastapi-limiter.
    """
    
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests: defaultdict[str, list[float]] = defaultdict(list)
    
    def _clean_old_requests(self, client_id: str, current_time: float) -> None:
        """Remove requests older than 1 minute."""
        cutoff = current_time - 60
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
    
    async def check_rate_limit(self, client_id: str) -> None:
        """
        Check if client has exceeded rate limit.
        Raises HTTPException if limit exceeded.
        """
        current_time = time.time()
        self._clean_old_requests(client_id, current_time)
        
        if len(self.requests[client_id]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute.",
            )
        
        self.requests[client_id].append(current_time)


rate_limiter = RateLimiter(requests_per_minute=settings.rate_limit_per_minute)


async def get_client_id(request: Request) -> str:
    """
    Extract client identifier from request.
    Uses X-Forwarded-For if behind proxy, otherwise client IP.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    if request.client:
        return request.client.host
    
    return "unknown"
