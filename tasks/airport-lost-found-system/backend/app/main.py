from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import (
    ai,
    analytics,
    admin_ops,
    audit_logs,
    auth,
    chat,
    claim_verifications,
    custody,
    demo,
    files,
    found_items,
    graph_rag,
    labels,
    lost_reports,
    matches,
    metadata,
    notifications,
    voice,
)
from app.core.config import get_settings
from app.core.database import engine
from app.core.observability import request_context_middleware, setup_logging, setup_opentelemetry
from app.core.security_middleware import security_headers_middleware, validate_production_security_settings
from app.models import Base
from app.services.azure_search_service import azure_search_service
from app.services.cache_service import cache_service


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    security_issues = validate_production_security_settings(settings)
    if security_issues:
        raise RuntimeError("Production security settings are not safe: " + " ".join(security_issues))
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    await cache_service.connect()
    await azure_search_service.create_or_update_index()
    yield
    await cache_service.close()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
setup_opentelemetry(app)
app.middleware("http")(request_context_middleware)
if settings.security_headers_enabled:
    app.middleware("http")(security_headers_middleware)
if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(settings.local_upload_dir)), name="uploads")

app.include_router(auth.router)
app.include_router(lost_reports.router)
app.include_router(found_items.router)
app.include_router(files.router)
app.include_router(ai.router)
app.include_router(matches.router)
app.include_router(custody.router)
app.include_router(notifications.router)
app.include_router(analytics.router)
app.include_router(metadata.router)
app.include_router(chat.router)
app.include_router(claim_verifications.router)
app.include_router(labels.router)
app.include_router(audit_logs.router)
app.include_router(voice.router)
app.include_router(graph_rag.router)
app.include_router(admin_ops.router)
app.include_router(admin_ops.health_router)
app.include_router(demo.router)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready")
def ready() -> dict[str, str | bool]:
    return {"status": "ready", "use_azure_services": settings.use_azure_services}
