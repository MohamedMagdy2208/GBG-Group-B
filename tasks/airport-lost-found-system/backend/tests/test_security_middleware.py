from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security_middleware import security_headers_middleware, validate_production_security_settings


def test_security_headers_are_added_to_responses() -> None:
    app = FastAPI()
    app.middleware("http")(security_headers_middleware)

    @app.get("/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    response = TestClient(app).get("/ping")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


def test_production_security_validation_flags_unsafe_defaults() -> None:
    settings = Settings(
        environment="production",
        jwt_secret="change-me-in-production",
        cors_origins=["*"],
        allowed_hosts=["*"],
        force_https=False,
    )

    issues = validate_production_security_settings(settings)

    assert any("JWT_SECRET" in issue for issue in issues)
    assert any("CORS_ORIGINS" in issue for issue in issues)
    assert any("ALLOWED_HOSTS" in issue for issue in issues)
    assert any("FORCE_HTTPS" in issue for issue in issues)


def test_production_security_validation_accepts_safe_pilot_settings() -> None:
    settings = Settings(
        environment="production",
        jwt_secret="x" * 48,
        cors_origins=["https://lostfound.example.com"],
        allowed_hosts=["api.lostfound.example.com"],
        force_https=True,
        use_azure_services=False,
    )

    assert validate_production_security_settings(settings) == []
