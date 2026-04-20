"""Document uploader components."""

from __future__ import annotations

import io

import streamlit as st
from PIL import Image

ACCEPTED_TYPES = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "docx", "xlsx", "pptx", "html"]
CUSTOM_TRAINING_TYPES = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp"]


def render_uploader(
    model_name: str,
    *,
    key: str = "single_uploader",
    accepted_types: list[str] | tuple[str, ...] = ACCEPTED_TYPES,
):
    """Single-file uploader."""

    st.subheader(f"Upload document - {model_name}")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=list(accepted_types),
        accept_multiple_files=False,
        key=key,
        help=f"Supported formats: {', '.join(accepted_types)}",
    )
    if uploaded_file:
        st.success(f"File ready: {uploaded_file.name} ({round(uploaded_file.size / 1024, 1)} KB)")
        _render_preview(uploaded_file)
    return uploaded_file


def render_custom_model_uploader(key: str = "multi_uploader"):
    """Multi-file uploader for custom model training."""

    st.subheader("Upload documents - custom model")
    st.info("Custom model training requires at least 5 documents of the same type.")

    uploaded_files = st.file_uploader(
        "Choose files",
        type=CUSTOM_TRAINING_TYPES,
        accept_multiple_files=True,
        key=key,
        help="Use PDF or image files for the labeling/training flow.",
    )

    if uploaded_files:
        count = len(uploaded_files)
        status = "Ready" if count >= 5 else "Need more documents"
        st.markdown(f"**{count} file(s) uploaded** - {status}")
        with st.expander("View uploaded files"):
            for file in uploaded_files:
                st.markdown(f"- `{file.name}` - {round(file.size / 1024, 1)} KB")
    return uploaded_files if uploaded_files else []


def _render_preview(uploaded_file):
    is_image = uploaded_file.type.startswith("image/") or uploaded_file.name.lower().endswith(
        (".png", ".jpg", ".jpeg", ".tiff", ".bmp")
    )
    if not is_image:
        return
    with st.expander("Preview", expanded=False):
        try:
            uploaded_file.seek(0)
            image = Image.open(io.BytesIO(uploaded_file.read()))
            st.image(image)
            uploaded_file.seek(0)
        except Exception:
            st.warning("Could not generate a preview for this file type.")
