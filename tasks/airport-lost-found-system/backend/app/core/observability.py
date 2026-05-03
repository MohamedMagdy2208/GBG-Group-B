import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

from fastapi import FastAPI, Request, Response

from app.core.config import get_settings
from app.core.security import mask_sensitive_text


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

LOG_EXTRA_KEYS = (
    "path",
    "method",
    "status_code",
    "duration_ms",
    "event",
    "cache_hit",
    "operation",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "search_latency_ms",
    "blob_duration_ms",
    "match_score",
    "confidence_level",
    "fraud_score",
    "queue_backlog",
    "outbox_count",
    "job_count",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_text(record.getMessage()),
            "request_id": request_id_var.get(),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in LOG_EXTRA_KEYS:
            if hasattr(record, key):
                payload[key] = _redact_value(getattr(record, key))
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


def setup_opentelemetry(app: FastAPI) -> None:
    settings = get_settings()
    if not settings.applicationinsights_connection_string and not settings.otel_exporter_otlp_endpoint:
        return
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        from app.core.database import engine

        configure_azure_monitor(connection_string=settings.applicationinsights_connection_string)
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument(engine=engine)
        HTTPXClientInstrumentor().instrument()
    except Exception:
        logging.getLogger(__name__).exception("OpenTelemetry setup failed")


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    logger = logging.getLogger("api.request")
    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "event": "request_completed",
            },
        )
        return response
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            "request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "event": "request_failed",
            },
        )
        raise
    finally:
        request_id_var.reset(token)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return mask_sensitive_text(value)
    if isinstance(value, dict):
        return {
            key: _redact_value(item)
            for key, item in value.items()
            if not any(secret_word in key.lower() for secret_word in ("password", "token", "authorization", "secret", "prompt", "transcript"))
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value
