from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str = "neo4j"
    openai_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    max_result_rows: int = 50


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer.") from exc


def load_settings(
    *,
    require_openai: bool = True,
    require_neo4j: bool = True,
) -> Settings:
    load_dotenv()
    provider = os.getenv("OPENAI_PROVIDER", "openai").strip().lower() or "openai"

    settings = Settings(
        neo4j_uri=os.getenv("NEO4J_URI", "").strip(),
        neo4j_username=os.getenv("NEO4J_USERNAME", "").strip(),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j").strip() or "neo4j",
        openai_provider=provider,
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o").strip() or "gpt-4o",
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "").strip(),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", "").strip(),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip(),
        azure_openai_api_version=os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-12-01-preview"
        ).strip()
        or "2024-12-01-preview",
        max_result_rows=_read_int("MAX_RESULT_ROWS", 50),
    )

    missing: list[str] = []
    if settings.openai_provider not in {"openai", "azure"}:
        raise ConfigError("OPENAI_PROVIDER must be either 'openai' or 'azure'.")

    if require_neo4j:
        if not settings.neo4j_uri:
            missing.append("NEO4J_URI")
        if not settings.neo4j_username:
            missing.append("NEO4J_USERNAME")
        if not settings.neo4j_password:
            missing.append("NEO4J_PASSWORD")
    if require_openai:
        if settings.openai_provider == "azure":
            if not settings.azure_openai_endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not settings.azure_openai_api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not settings.azure_openai_deployment:
                missing.append("AZURE_OPENAI_DEPLOYMENT")
        elif not settings.openai_api_key:
            missing.append("OPENAI_API_KEY")

    if missing:
        names = ", ".join(missing)
        raise ConfigError(f"Missing required environment variable(s): {names}.")

    if settings.max_result_rows < 1:
        raise ConfigError("MAX_RESULT_ROWS must be at least 1.")

    return settings
