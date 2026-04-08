"""
Uploader components for standard and custom model flows.
"""

import streamlit as st

# Accepted file types for document upload
ACCEPTED_TYPES = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp"]


def render_uploader(model_name: str):
    """
    Single-file uploader for standard models (OCR, Layout, etc.).

    Returns:
        UploadedFile | None
    """
    st.subheader(f"📄 Upload Document — {model_name}")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=ACCEPTED_TYPES,
        accept_multiple_files=False,
        key="single_uploader",
        help="Supported formats: PDF, PNG, JPG, JPEG, TIFF, BMP",
    )
    if uploaded_file:
        st.success(f"✅ File ready: **{uploaded_file.name}** ({round(uploaded_file.size / 1024, 1)} KB)")
    return uploaded_file


def render_custom_model_uploader():
    """
    Multi-file uploader for the Custom Model flow (minimum 5 documents required).

    Returns:
        list[UploadedFile] | None
    """
    st.subheader("📂 Upload Documents — Custom Model")
    st.info("ℹ️ Custom model training requires **at least 5 documents**.")

    uploaded_files = st.file_uploader(
        "Choose files (minimum 5)",
        type=ACCEPTED_TYPES,
        accept_multiple_files=True,
        key="multi_uploader",
        help="Upload 5 or more documents to use with your custom model.",
    )

    if uploaded_files:
        count = len(uploaded_files)
        color = "✅" if count >= 5 else "⚠️"
        st.markdown(f"{color} **{count} file(s) uploaded** (minimum required: 5)")

        # Show a compact file list
        with st.expander("View uploaded files"):
            for f in uploaded_files:
                st.markdown(f"- `{f.name}` — {round(f.size / 1024, 1)} KB")

    return uploaded_files if uploaded_files else None