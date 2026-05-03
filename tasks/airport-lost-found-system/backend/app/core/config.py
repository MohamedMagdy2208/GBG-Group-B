import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


SECRET_FIELD_NAMES = {
    "DATABASE_URL": "database_url",
    "JWT_SECRET": "jwt_secret",
    "AZURE_OPENAI_ENDPOINT": "azure_openai_endpoint",
    "AZURE_OPENAI_API_KEY": "azure_openai_api_key",
    "AZURE_OPENAI_API_VERSION": "azure_openai_api_version",
    "AZURE_OPENAI_CHAT_DEPLOYMENT": "azure_openai_chat_deployment",
    "AZURE_OPENAI_FAST_DEPLOYMENT": "azure_openai_fast_deployment",
    "AZURE_OPENAI_FAST_ENDPOINT": "azure_openai_fast_endpoint",
    "AZURE_OPENAI_FAST_API_KEY": "azure_openai_fast_api_key",
    "AZURE_OPENAI_REASONING_DEPLOYMENT": "azure_openai_reasoning_deployment",
    "AZURE_OPENAI_REASONING_ENDPOINT": "azure_openai_reasoning_endpoint",
    "AZURE_OPENAI_REASONING_API_KEY": "azure_openai_reasoning_api_key",
    "AZURE_OPENAI_DEEP_REASONING_DEPLOYMENT": "azure_openai_deep_reasoning_deployment",
    "AZURE_OPENAI_DEEP_REASONING_ENDPOINT": "azure_openai_deep_reasoning_endpoint",
    "AZURE_OPENAI_DEEP_REASONING_API_KEY": "azure_openai_deep_reasoning_api_key",
    "AZURE_OPENAI_EMBEDDING_ENDPOINT": "azure_openai_embedding_endpoint",
    "AZURE_OPENAI_EMBEDDING_API_KEY": "azure_openai_embedding_api_key",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "azure_openai_embedding_deployment",
    "AZURE_STORAGE_ACCOUNT_NAME": "azure_storage_account_name",
    "AZURE_STORAGE_CONTAINER_NAME": "azure_storage_container_name",
    "AZURE_STORAGE_CONNECTION_STRING": "azure_storage_connection_string",
    "AZURE_AI_VISION_ENDPOINT": "azure_ai_vision_endpoint",
    "AZURE_AI_VISION_KEY": "azure_ai_vision_key",
    "AZURE_SEARCH_ENDPOINT": "azure_search_endpoint",
    "AZURE_SEARCH_KEY": "azure_search_key",
    "AZURE_SEARCH_INDEX_NAME": "azure_search_index_name",
    "AZURE_COMMUNICATION_CONNECTION_STRING": "azure_communication_connection_string",
    "AZURE_COMMUNICATION_EMAIL_SENDER": "azure_communication_email_sender",
    "AZURE_COMMUNICATION_SMS_SENDER": "azure_communication_sms_sender",
    "AZURE_SPEECH_KEY": "azure_speech_key",
    "AZURE_SPEECH_REGION": "azure_speech_region",
    "AZURE_SPEECH_ENDPOINT": "azure_speech_endpoint",
    "AZURE_COSMOS_GREMLIN_ENDPOINT": "azure_cosmos_gremlin_endpoint",
    "AZURE_COSMOS_GREMLIN_KEY": "azure_cosmos_gremlin_key",
    "REDIS_URL": "redis_url",
    "APPLICATIONINSIGHTS_CONNECTION_STRING": "applicationinsights_connection_string",
}


class Settings(BaseSettings):
    app_name: str = "AI-Powered Airport Lost & Found"
    environment: str = "local"
    api_prefix: str = ""
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "0.0.0.0", "testserver", "backend"])
    security_headers_enabled: bool = True
    force_https: bool = False

    database_url: str = "postgresql+psycopg://airport:airport@postgres:5432/airport_lost_found"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 14
    password_reset_token_expire_minutes: int = 30
    account_lockout_threshold: int = 5
    account_lockout_minutes: int = 15
    rate_limit_login_per_minute: int = 8
    rate_limit_public_per_minute: int = 30
    rate_limit_ai_per_minute: int = 20
    rate_limit_upload_per_minute: int = 12

    use_azure_services: bool = False

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_responses_api_version: str = "2025-04-01-preview"
    azure_openai_use_responses_api: bool = False
    azure_openai_chat_deployment: str | None = None
    azure_openai_fast_deployment: str | None = None
    azure_openai_fast_endpoint: str | None = None
    azure_openai_fast_api_key: str | None = None
    azure_openai_reasoning_deployment: str | None = None
    azure_openai_reasoning_endpoint: str | None = None
    azure_openai_reasoning_api_key: str | None = None
    azure_openai_deep_reasoning_deployment: str | None = None
    azure_openai_deep_reasoning_endpoint: str | None = None
    azure_openai_deep_reasoning_api_key: str | None = None
    azure_openai_embedding_endpoint: str | None = None
    azure_openai_embedding_api_key: str | None = None
    azure_openai_embedding_deployment: str | None = None

    azure_storage_account_name: str | None = None
    azure_storage_container_name: str = "lost-found"
    azure_storage_connection_string: str | None = None
    azure_ai_vision_endpoint: str | None = None
    azure_ai_vision_key: str | None = None
    azure_search_endpoint: str | None = None
    azure_search_key: str | None = None
    azure_search_index_name: str = "airport-lost-found"
    azure_search_vector_dimensions: int = 1536
    azure_communication_connection_string: str | None = None
    azure_communication_email_sender: str = "DoNotReply@airport.example"
    azure_communication_sms_sender: str = "+10000000000"
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_speech_endpoint: str | None = None
    azure_speech_voice_en: str = "en-US-JennyNeural"
    azure_speech_voice_ar: str = "ar-EG-SalmaNeural"
    azure_cosmos_gremlin_endpoint: str | None = None
    azure_cosmos_gremlin_key: str | None = None
    azure_cosmos_gremlin_database: str = "airport-lost-found"
    azure_cosmos_gremlin_graph: str = "operations-graph"
    azure_key_vault_url: str | None = None
    azure_key_vault_enabled: bool = True
    azure_key_vault_secret_prefix: str | None = None
    azure_key_vault_override_env: bool = False
    azure_use_managed_identity: bool = False

    redis_url: str = "redis://redis:6379/0"
    cache_backend: str = "redis"
    cache_ai_ttl_seconds: int = 86400
    cache_status_ttl_seconds: int = 60
    cache_analytics_ttl_seconds: int = 300

    log_level: str = "INFO"
    otel_service_name: str = "airport-lost-found-api"
    otel_exporter_otlp_endpoint: str | None = None
    applicationinsights_connection_string: str | None = None
    azure_openai_chat_input_cost_per_1k: float = 0
    azure_openai_chat_output_cost_per_1k: float = 0
    azure_openai_embedding_cost_per_1k: float = 0
    voice_features_enabled: bool = True
    voice_provider: str = "browser"
    qr_label_base_url: str = "http://localhost:5173"
    fraud_high_risk_threshold: int = 70
    claim_verification_expiry_hours: int = 72
    graph_rag_enabled: bool = True
    graph_rag_provider: str = "postgres"
    graph_rag_context_ttl_seconds: int = 300
    graph_rag_max_nodes: int = 80
    graph_rag_max_edges: int = 140
    worker_poll_interval_seconds: int = 5
    outbox_max_attempts: int = 5
    health_deep_timeout_seconds: int = 3
    enable_malware_scan_stub: bool = True
    proof_document_retention_days: int = 365

    local_upload_dir: Path = Path("local_uploads")
    max_upload_mb: int = 10
    auto_create_tables: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _load_key_vault_secrets(settings)
    return settings


def _load_key_vault_secrets(settings: Settings) -> None:
    if not settings.azure_key_vault_enabled or not settings.azure_key_vault_url:
        return
    if not settings.use_azure_services and not settings.azure_key_vault_override_env:
        return
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=settings.azure_key_vault_url, credential=credential)
        loaded = 0
        for env_name, field_name in SECRET_FIELD_NAMES.items():
            current_value = getattr(settings, field_name)
            if current_value and not settings.azure_key_vault_override_env:
                continue
            if os.getenv(env_name) and not settings.azure_key_vault_override_env:
                continue
            value = _get_secret_value(client, env_name, settings.azure_key_vault_secret_prefix)
            if value is not None:
                setattr(settings, field_name, value)
                loaded += 1
        logger.info("loaded Azure Key Vault secrets", extra={"event": "key_vault_loaded", "secret_count": loaded})
    except Exception:
        logger.exception("Azure Key Vault secret loading failed", extra={"event": "key_vault_failed"})


def _get_secret_value(client: Any, env_name: str, prefix: str | None) -> str | None:
    base_names = [env_name.replace("_", "-"), env_name.lower().replace("_", "-")]
    candidate_names = []
    for name in base_names:
        if prefix:
            candidate_names.append(f"{prefix}-{name}")
        candidate_names.append(name)
    for secret_name in candidate_names:
        try:
            return client.get_secret(secret_name).value
        except Exception:
            continue
    return None
