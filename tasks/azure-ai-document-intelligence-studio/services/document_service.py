"""Central Azure Document Intelligence service layer."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from typing import Any

from azure.ai.documentintelligence import (
    DocumentIntelligenceAdministrationClient,
    DocumentIntelligenceClient,
)
from azure.ai.documentintelligence.models import (
    AzureBlobContentSource,
    BuildDocumentModelRequest,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from services.config import AzureConfig, get_azure_config
from services.model_registry import get_model_definition


@dataclass
class AnalyzeOptions:
    pages: str = ""
    locale: str = ""
    query_fields: list[str] = field(default_factory=list)
    output_content_format: str = ""
    features: list[str] = field(default_factory=list)
    output: list[str] = field(default_factory=list)

    def to_kwargs(self, model_id: str) -> dict[str, Any]:
        """Return SDK kwargs, filtered for the selected model."""

        model = get_model_definition(model_id)
        kwargs: dict[str, Any] = {}
        if self.pages.strip():
            kwargs["pages"] = self.pages.strip()
        if self.locale.strip():
            kwargs["locale"] = self.locale.strip()
        if self.output_content_format:
            allowed = model.output_content_formats if model else ("text", "markdown")
            if self.output_content_format in allowed:
                kwargs["output_content_format"] = self.output_content_format
        if self.features:
            allowed_features = set(model.supported_features if model else self.features)
            features = [f for f in self.features if f in allowed_features]
            if features:
                kwargs["features"] = features
        if self.query_fields and (not model or model.supports_query_fields):
            kwargs["query_fields"] = [f for f in self.query_fields if f.strip()]
        if self.output:
            allowed_output = set(model.output_options if model else self.output)
            output = [o for o in self.output if o in allowed_output]
            if output:
                kwargs["output"] = output
        return kwargs


def _error(message: str) -> dict[str, str]:
    return {"error": message}


def _exception_to_error(exc: Exception) -> dict[str, str]:
    if isinstance(exc, HttpResponseError):
        return _error(f"{exc.status_code or 'Azure error'}: {exc.message}")
    return _error(str(exc))


def _document_client(config: AzureConfig | None = None) -> DocumentIntelligenceClient:
    config = config or get_azure_config()
    if not config.has_document_intelligence:
        raise ValueError("Azure Document Intelligence endpoint and API key are required.")
    return DocumentIntelligenceClient(
        endpoint=config.endpoint,
        credential=AzureKeyCredential(config.api_key),
    )


def _admin_client(
    config: AzureConfig | None = None,
) -> DocumentIntelligenceAdministrationClient:
    config = config or get_azure_config()
    if not config.has_document_intelligence:
        raise ValueError("Azure Document Intelligence endpoint and API key are required.")
    return DocumentIntelligenceAdministrationClient(
        endpoint=config.endpoint,
        credential=AzureKeyCredential(config.api_key),
    )


def read_uploaded_file(uploaded_file) -> bytes:
    """Read a Streamlit UploadedFile without leaving its cursor consumed."""

    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)
    return data


def analyze_document(
    model_id: str,
    uploaded_file,
    options: AnalyzeOptions | None = None,
    *,
    config: AzureConfig | None = None,
) -> dict[str, Any]:
    """Analyze one document with a prebuilt or custom model."""

    options = options or AnalyzeOptions()
    try:
        client = _document_client(config)
        body = io.BytesIO(read_uploaded_file(uploaded_file))
        poller = client.begin_analyze_document(
            model_id,
            body=body,
            **options.to_kwargs(model_id),
        )
        result = poller.result()
        data = result.as_dict()
        data["model_id"] = model_id
        data["file_name"] = getattr(uploaded_file, "name", "")
        return data
    except Exception as exc:
        return _exception_to_error(exc)


def run_layout_for_labeling(uploaded_file) -> dict[str, Any]:
    """Run Layout with stable string offsets for custom labeling artifacts."""

    try:
        client = _document_client()
        body = io.BytesIO(read_uploaded_file(uploaded_file))
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=body,
            string_index_type="utf16CodeUnit",
        )
        result = poller.result()
        data = result.as_dict()
        data["model_id"] = "prebuilt-layout"
        data["file_name"] = getattr(uploaded_file, "name", "")
        return data
    except Exception as exc:
        return _exception_to_error(exc)


def build_custom_model(
    project_id: str,
    model_id: str,
    build_mode: str,
    blob_prefix: str,
    *,
    description: str = "",
    config: AzureConfig | None = None,
) -> dict[str, Any]:
    """Submit a custom extraction model build operation."""

    config = config or get_azure_config()
    if not config.has_storage:
        return _error("Azure Blob Storage configuration is required for training.")
    if not config.storage_container_url:
        return _error("A SAS-enabled storage container URL is required for model build.")
    if build_mode not in {"template", "neural"}:
        return _error("Build mode must be 'template' or 'neural'.")
    if not model_id.strip():
        return _error("A model ID is required.")

    try:
        client = _admin_client(config)
        request = BuildDocumentModelRequest(
            model_id=model_id.strip(),
            description=description or f"Project {project_id}",
            build_mode=build_mode,
            azure_blob_source=AzureBlobContentSource(
                container_url=config.storage_container_url,
                prefix=blob_prefix.strip("/"),
            ),
        )
        poller = client.begin_build_document_model(request)
        result = poller.result()
        data = result.as_dict()
        data["model_id"] = getattr(result, "model_id", model_id.strip())
        data["build_mode"] = build_mode
        data["project_id"] = project_id
        return data
    except Exception as exc:
        return _exception_to_error(exc)


def list_models(config: AzureConfig | None = None) -> dict[str, Any]:
    """List models in the configured Document Intelligence resource."""

    try:
        models = []
        for model in _admin_client(config).list_models():
            models.append(model.as_dict() if hasattr(model, "as_dict") else dict(model))
        return {"models": models}
    except Exception as exc:
        return _exception_to_error(exc)


def get_model(model_id: str, config: AzureConfig | None = None) -> dict[str, Any]:
    """Get one model's metadata."""

    try:
        model = _admin_client(config).get_model(model_id)
        return model.as_dict() if hasattr(model, "as_dict") else dict(model)
    except Exception as exc:
        return _exception_to_error(exc)


def delete_model(model_id: str, config: AzureConfig | None = None) -> dict[str, Any]:
    """Delete one custom model."""

    try:
        _admin_client(config).delete_model(model_id)
        return {"deleted": model_id}
    except Exception as exc:
        return _exception_to_error(exc)


def _container_client(config: AzureConfig):
    try:
        from azure.storage.blob import ContainerClient
    except ImportError as exc:
        raise RuntimeError(
            "azure-storage-blob is required for training data upload. "
            "Install dependencies from requirements.txt."
        ) from exc

    if config.storage_container_url:
        return ContainerClient.from_container_url(config.storage_container_url)
    if config.storage_connection_string and config.storage_container_name:
        return ContainerClient.from_connection_string(
            config.storage_connection_string,
            container_name=config.storage_container_name,
        )
    raise ValueError("Azure Blob Storage container URL or connection settings are required.")


def upload_training_assets(
    assets: list[tuple[str, bytes | str | dict[str, Any], str]],
    *,
    config: AzureConfig | None = None,
) -> dict[str, Any]:
    """Upload training files to Azure Blob Storage.

    Each asset tuple is (blob_name, payload, content_type).
    """

    config = config or get_azure_config()
    if not config.has_storage:
        return _error("Azure Blob Storage configuration is required.")

    try:
        from azure.storage.blob import ContentSettings

        container = _container_client(config)
        uploaded = []
        for blob_name, payload, content_type in assets:
            if isinstance(payload, dict):
                data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            elif isinstance(payload, str):
                data = payload.encode("utf-8")
            else:
                data = payload
            normalized_name = blob_name.replace("\\", "/").lstrip("/")
            container.upload_blob(
                name=normalized_name,
                data=data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            uploaded.append(normalized_name)
        return {"uploaded": uploaded, "count": len(uploaded)}
    except Exception as exc:
        return _exception_to_error(exc)
