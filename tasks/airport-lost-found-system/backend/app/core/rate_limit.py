from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.services.cache_service import cache_service


def client_identity(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def rate_limit(name: str, limit: int, window_seconds: int = 60) -> Callable:
    async def dependency(request: Request) -> None:
        now = int(time.time())
        bucket = now // window_seconds
        key = f"rate:{name}:{client_identity(request)}:{bucket}"
        count = await cache_service.increment(key, window_seconds + 5)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please retry later.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency
