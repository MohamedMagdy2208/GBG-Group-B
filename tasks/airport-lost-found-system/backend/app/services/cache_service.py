import fnmatch
import json
import logging
import time
from typing import Any

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._memory: dict[str, tuple[float, Any]] = {}
        self._redis = None

    async def connect(self) -> None:
        if self.settings.cache_backend != "redis":
            return
        try:
            from redis.asyncio import from_url

            self._redis = from_url(self.settings.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("redis cache connected", extra={"event": "cache_connected"})
        except Exception:
            self._redis = None
            logger.warning("redis unavailable, using in-memory cache", extra={"event": "cache_fallback"})

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def get_json(self, key: str) -> Any | None:
        if self._redis:
            value = await self._redis.get(key)
            hit = value is not None
            logger.info("cache lookup", extra={"event": "cache_lookup", "cache_hit": hit})
            return json.loads(value) if value else None
        item = self._memory.get(key)
        if not item:
            logger.info("cache lookup", extra={"event": "cache_lookup", "cache_hit": False})
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._memory.pop(key, None)
            logger.info("cache lookup", extra={"event": "cache_lookup", "cache_hit": False})
            return None
        logger.info("cache lookup", extra={"event": "cache_lookup", "cache_hit": True})
        return value

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        if self._redis:
            await self._redis.setex(key, ttl_seconds, json.dumps(value, default=str))
            return
        self._memory[key] = (time.time() + ttl_seconds, value)

    async def increment(self, key: str, ttl_seconds: int) -> int:
        if self._redis:
            value = await self._redis.incr(key)
            if value == 1:
                await self._redis.expire(key, ttl_seconds)
            return int(value)
        item = self._memory.get(key)
        if not item or item[0] < time.time():
            self._memory[key] = (time.time() + ttl_seconds, 1)
            return 1
        expires_at, value = item
        next_value = int(value) + 1
        self._memory[key] = (expires_at, next_value)
        return next_value

    async def delete(self, key: str) -> None:
        if self._redis:
            await self._redis.delete(key)
            return
        self._memory.pop(key, None)

    async def delete_pattern(self, pattern: str) -> None:
        if self._redis:
            async for key in self._redis.scan_iter(match=pattern):
                await self._redis.delete(key)
            return
        for key in list(self._memory):
            if fnmatch.fnmatch(key, pattern):
                self._memory.pop(key, None)


cache_service = CacheService()
