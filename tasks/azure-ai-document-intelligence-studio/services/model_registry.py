"""Model registry for the supported Document Intelligence models."""

from __future__ import annotations

from dataclasses import dataclass, field


FEATURE_LABELS = {
    "ocrHighResolution": "High resolution OCR",
    "languages": "Language detection",
    "barcodes": "Barcodes",
    "formulas": "Formulas",
    "keyValuePairs": "Key-value pairs",
    "styleFont": "Font/style extraction",
}


@dataclass(frozen=True)
class ModelDefinition:
    """Static UI/API metadata for a Document Intelligence model."""

    display_name: str
    model_id: str
    description: str
    category: str = "Prebuilt"
    supports_query_fields: bool = False
    supported_features: tuple[str, ...] = field(default_factory=tuple)
    output_content_formats: tuple[str, ...] = ("text",)
    output_options: tuple[str, ...] = field(default_factory=tuple)
    accepted_file_types: tuple[str, ...] = (
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "tiff",
        "bmp",
        "heif",
    )
    warning: str = ""


PREBUILT_MODELS: dict[str, ModelDefinition] = {
    "prebuilt-read": ModelDefinition(
        display_name="OCR / Read",
        model_id="prebuilt-read",
        description="Extract printed and handwritten text.",
        output_options=("pdf",),
        accepted_file_types=(
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "tiff",
            "bmp",
            "heif",
            "docx",
            "xlsx",
            "pptx",
            "html",
        ),
    ),
    "prebuilt-layout": ModelDefinition(
        display_name="Layout Analysis",
        model_id="prebuilt-layout",
        description="Extract text, tables, selection marks, structure, and layout.",
        supports_query_fields=True,
        supported_features=(
            "ocrHighResolution",
            "languages",
            "barcodes",
            "formulas",
            "keyValuePairs",
            "styleFont",
        ),
        output_content_formats=("text", "markdown"),
        output_options=("figures",),
        accepted_file_types=(
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "tiff",
            "bmp",
            "heif",
            "docx",
            "xlsx",
            "pptx",
            "html",
        ),
    ),
    "prebuilt-document": ModelDefinition(
        display_name="General Documents",
        model_id="prebuilt-document",
        description="Extract text, layout, and general key-value pairs.",
        supports_query_fields=True,
        supported_features=("ocrHighResolution", "languages", "barcodes"),
        warning=(
            "Microsoft marks prebuilt-document as deprecated in newer API "
            "guidance. Azure service errors are shown as-is."
        ),
    ),
    "prebuilt-invoice": ModelDefinition(
        display_name="Invoices",
        model_id="prebuilt-invoice",
        description="Extract common invoice fields and line items.",
        supports_query_fields=True,
        supported_features=("ocrHighResolution", "languages", "barcodes"),
    ),
    "prebuilt-receipt": ModelDefinition(
        display_name="Receipts",
        model_id="prebuilt-receipt",
        description="Extract common receipt fields and transaction details.",
        supports_query_fields=True,
        supported_features=("ocrHighResolution", "languages", "barcodes"),
    ),
}


DISPLAY_NAME_TO_MODEL_ID = {
    model.display_name: model_id for model_id, model in PREBUILT_MODELS.items()
}


def get_prebuilt_options() -> list[str]:
    """Return display names for the app's supported prebuilt models."""

    return [model.display_name for model in PREBUILT_MODELS.values()]


def resolve_model_id(name_or_id: str) -> str:
    """Resolve either a display name or direct model ID to a model ID."""

    return DISPLAY_NAME_TO_MODEL_ID.get(name_or_id, name_or_id)


def get_model_definition(name_or_id: str) -> ModelDefinition | None:
    """Return registry metadata for a supported model."""

    return PREBUILT_MODELS.get(resolve_model_id(name_or_id))


def is_supported_prebuilt(name_or_id: str) -> bool:
    """Return whether the model is one of this app's supported prebuilt models."""

    return resolve_model_id(name_or_id) in PREBUILT_MODELS
