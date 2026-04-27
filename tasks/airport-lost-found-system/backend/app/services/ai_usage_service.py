import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from app.core.config import get_settings
from app.services.cache_service import cache_service


logger = logging.getLogger(__name__)


@dataclass
class AIUsageRecord:
    operation: str
    deployment: str | None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0
    timestamp: str = ""


class AIUsageService:
    async def record(
        self,
        operation: str,
        deployment: str | None,
        usage: object | None,
        is_embedding: bool = False,
    ) -> None:
        settings = get_settings()
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or prompt_tokens + completion_tokens)
        if is_embedding:
            estimated_cost = (total_tokens / 1000) * settings.azure_openai_embedding_cost_per_1k
        else:
            estimated_cost = (
                (prompt_tokens / 1000) * settings.azure_openai_chat_input_cost_per_1k
                + (completion_tokens / 1000) * settings.azure_openai_chat_output_cost_per_1k
            )
        record = AIUsageRecord(
            operation=operation,
            deployment=deployment,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=round(estimated_cost, 6),
            timestamp=datetime.now(UTC).isoformat(),
        )
        logger.info(
            "azure openai usage",
            extra={
                "event": "ai_usage",
                "operation": operation,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        )
        summary = await cache_service.get_json("analytics:ai-usage") or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0,
            "requests": 0,
            "by_operation": {},
            "recent": [],
        }
        summary["prompt_tokens"] += prompt_tokens
        summary["completion_tokens"] += completion_tokens
        summary["total_tokens"] += total_tokens
        summary["estimated_cost_usd"] = round(summary["estimated_cost_usd"] + record.estimated_cost_usd, 6)
        summary["requests"] += 1
        operation_summary = summary["by_operation"].setdefault(operation, {"requests": 0, "total_tokens": 0})
        operation_summary["requests"] += 1
        operation_summary["total_tokens"] += total_tokens
        summary["recent"] = [asdict(record), *summary["recent"][:19]]
        await cache_service.set_json("analytics:ai-usage", summary, settings.cache_analytics_ttl_seconds)

    async def summary(self) -> dict:
        return await cache_service.get_json("analytics:ai-usage") or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0,
            "requests": 0,
            "by_operation": {},
            "recent": [],
        }


ai_usage_service = AIUsageService()
