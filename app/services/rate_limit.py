"""Redis-based rate limiter for FastAPI dependencies."""

import time
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from app.core.config import settings


class RateLimiter:
    """Sliding window rate limiter using Redis."""

    def __init__(self, redis_url: str = ""):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        r = await self._get_redis()
        now = int(time.time())
        window_start = now - window_seconds

        await r.zremrangebyscore(key, 0, window_start)
        request_count = await r.zcard(key)

        if request_count >= max_requests:
            return False

        await r.zadd(key, {str(now): now})
        await r.expire(key, window_seconds)
        return True

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit(
    request: Request,
    max_requests: int = 60,
    window_seconds: int = 60,
) -> None:
    """FastAPI dependency for rate limiting by client IP."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:{client_ip}"

    allowed = await rate_limiter.check(key, max_requests, window_seconds)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
