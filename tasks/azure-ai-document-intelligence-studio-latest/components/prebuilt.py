"""Prebuilt model analysis UI."""

from __future__ import annotations

import streamlit as st

from components.results import render_results
from components.uploader import render_uploader
from services.document_service import AnalyzeOptions, analyze_document
from services.model_registry import FEATURE_LABELS, get_prebuilt_options, get_model_definition


def render_analyze_options(model_id: str, key_prefix: str = "prebuilt") -> AnalyzeOptions:
    """Render Studio-like analyze options for a model."""

    model = get_model_definition(model_id)
    if not model:
        return AnalyzeOptions()

    with st.expander("Analyze options", expanded=False):
        pages = st.text_input(
            "Pages",
            placeholder="Example: 1-3,5",
            key=f"{key_prefix}_pages_{model_id}",
        )
        locale = st.text_input(
            "Locale",
            placeholder="Example: en-US, ar, fr",
            key=f"{key_prefix}_locale_{model_id}",
        )

        output_content_format = ""
        if len(model.output_content_formats) > 1:
            output_content_format = st.selectbox(
                "Output content format",
                [""] + list(model.output_content_formats),
                format_func=lambda value: "Service default" if not value else value,
                key=f"{key_prefix}_content_format_{model_id}",
            )

        features = []
        if model.supported_features:
            selected_feature_labels = st.multiselect(
                "Add-on features",
                [FEATURE_LABELS.get(feature, feature) for feature in model.supported_features],
                key=f"{key_prefix}_features_{model_id}",
            )
            label_to_feature = {
                FEATURE_LABELS.get(feature, feature): feature
                for feature in model.supported_features
            }
            features = [label_to_feature[label] for label in selected_feature_labels]

        output = []
        if model.output_options:
            output = st.multiselect(
                "Extra outputs",
                list(model.output_options),
                key=f"{key_prefix}_output_{model_id}",
            )

        query_fields = []
        if model.supports_query_fields:
            query_text = st.text_area(
                "Query fields",
                placeholder="One field per line, for example: Customer account number",
                key=f"{key_prefix}_query_{model_id}",
            )
            query_fields = [line.strip() for line in query_text.splitlines() if line.strip()]

    return AnalyzeOptions(
        pages=pages,
        locale=locale,
        query_fields=query_fields,
        output_content_format=output_content_format,
        features=features,
        output=output,
    )


def render_prebuilt_analyzer():
    """Render the first-class prebuilt analysis experience."""

    st.header("Prebuilt model analysis")
    selected_name = st.selectbox("Model", get_prebuilt_options(), key="prebuilt_model")
    model = get_model_definition(selected_name)
    if not model:
        st.error("Unsupported model selection.")
        return

    st.caption(model.description)
    if model.warning:
        st.warning(model.warning)

    uploaded_file = render_uploader(
        selected_name,
        key=f"prebuilt_upload_{model.model_id}",
        accepted_types=model.accepted_file_types,
    )
    options = render_analyze_options(model.model_id)

    if uploaded_file and st.button("Run analysis", key=f"run_{model.model_id}"):
        with st.spinner(f"Analyzing with {model.model_id}..."):
            result = analyze_document(model.model_id, uploaded_file, options)
        st.session_state["last_prebuilt_result"] = result

    if "last_prebuilt_result" in st.session_state:
        render_results(st.session_state["last_prebuilt_result"])
