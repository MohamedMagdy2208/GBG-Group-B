"""Environment-backed application settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr


load_dotenv()


class Settings(BaseModel):
    """Typed settings object shared across the application."""

    model_config = ConfigDict(extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    openai_provider: str = Field(default="openai", alias="OPENAI_PROVIDER")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-4o", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_EMBEDDING_MODEL",
    )
    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str = Field(
        default="2024-12-01-preview",
        alias="AZURE_OPENAI_API_VERSION",
    )
    app_env: str = Field(default="development", alias="APP_ENV")
    bootstrap_on_start: bool = Field(default=False, alias="BOOTSTRAP_ON_START")
    vector_store_path: Path = Field(default=Path("vector_store"), alias="VECTOR_STORE_PATH")
    top_k_docs: int = Field(default=6, alias="TOP_K_DOCS")
    max_result_rows: int = Field(default=50, alias="MAX_RESULT_ROWS")

    @property
    def openai_api_key_value(self) -> str | None:
        """Return the decrypted API key when present."""

        return self.openai_api_key.get_secret_value() if self.openai_api_key else None

    @property
    def use_azure_openai(self) -> bool:
        """Return True when Azure OpenAI settings should be used."""

        return self.openai_provider.lower() == "azure" or bool(self.azure_openai_endpoint)


def get_settings() -> Settings:
    """Load settings from environment variables."""

    return Settings.model_validate(os.environ)
