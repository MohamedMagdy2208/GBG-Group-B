from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.config import Settings


PRODUCTION_ENVIRONMENTS = {"production", "prod", "staging"}


async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(self), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


def validate_production_security_settings(settings: Settings) -> list[str]:
    environment = settings.environment.lower()
    if environment not in PRODUCTION_ENVIRONMENTS:
        return []

    issues: list[str] = []
    if not settings.jwt_secret or settings.jwt_secret == "change-me-in-production" or len(settings.jwt_secret) < 32:
        issues.append("JWT_SECRET must be a strong non-default value with at least 32 characters.")
    if "*" in settings.cors_origins:
        issues.append("CORS_ORIGINS cannot contain '*' in production or staging.")
    if not settings.cors_origins:
        issues.append("CORS_ORIGINS must list the deployed frontend origins.")
    insecure_origins = [
        origin
        for origin in settings.cors_origins
        if origin.startswith("http://") and "localhost" not in origin and "127.0.0.1" not in origin
    ]
    if insecure_origins:
        issues.append("CORS_ORIGINS must use HTTPS for public origins.")
    if not settings.allowed_hosts or "*" in settings.allowed_hosts:
        issues.append("ALLOWED_HOSTS must explicitly list deployed API hostnames.")
    if not settings.force_https:
        issues.append("FORCE_HTTPS should be true behind the production ingress/proxy.")
    if settings.use_azure_services and not settings.azure_key_vault_url:
        issues.append("AZURE_KEY_VAULT_URL should be configured when USE_AZURE_SERVICES=true.")
    return issues
