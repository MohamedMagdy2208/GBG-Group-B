"""Sidebar component for Azure configuration."""

from __future__ import annotations

import streamlit as st

from services.config import AzureConfig, get_azure_config, redact, write_local_secrets


def render_sidebar():
    """Render Azure connection settings with session overrides."""

    config = get_azure_config()

    with st.sidebar:
        st.header("Configuration")

        st.subheader("Document Intelligence")
        endpoint = st.text_input(
            "Endpoint URL",
            value=config.endpoint,
            placeholder="https://<resource>.cognitiveservices.azure.com/",
            type="default",
        )
        api_key = st.text_input(
            "API Key",
            value=config.api_key,
            placeholder="Your Azure API key",
            type="password",
        )

        st.subheader("Blob Storage")
        storage_container_url = st.text_input(
            "Container SAS URL",
            value=config.storage_container_url,
            placeholder="https://<account>.blob.core.windows.net/<container>?<sas>",
            type="password",
            help="Required for model build. Also used for upload when provided.",
        )
        storage_connection_string = st.text_input(
            "Connection string",
            value=config.storage_connection_string,
            type="password",
            help="Optional upload fallback. Model build still needs a SAS container URL.",
        )
        storage_container_name = st.text_input(
            "Container name",
            value=config.storage_container_name,
            help="Required only when using a connection string.",
        )

        st.subheader("Custom model")
        custom_model_id = st.text_input(
            "Active custom model ID",
            value=config.custom_model_id,
            placeholder="e.g. forms-neural-v1",
        )

        if st.button("Save configuration"):
            saved_config = AzureConfig(
                endpoint=endpoint.strip(),
                api_key=api_key.strip(),
                storage_container_url=storage_container_url.strip(),
                storage_connection_string=storage_connection_string.strip(),
                storage_container_name=storage_container_name.strip(),
                custom_model_id=custom_model_id.strip(),
            )
            st.session_state["azure_endpoint"] = saved_config.endpoint
            st.session_state["azure_api_key"] = saved_config.api_key
            st.session_state["storage_container_url"] = saved_config.storage_container_url
            st.session_state["storage_connection_string"] = saved_config.storage_connection_string
            st.session_state["storage_container_name"] = saved_config.storage_container_name
            st.session_state["custom_model_id"] = saved_config.custom_model_id
            try:
                path = write_local_secrets(saved_config)
                st.success(f"Configuration saved for this session and future runs at `{path}`.")
            except Exception as exc:
                st.error(f"Saved for this session, but could not write secrets.toml: {exc}")

        st.markdown("---")
        st.caption(
            "Config can also come from env vars or `.streamlit/secrets.toml`: "
            "`DOCUMENTINTELLIGENCE_ENDPOINT`, `DOCUMENTINTELLIGENCE_API_KEY`, "
            "`AZURE_STORAGE_CONTAINER_URL`."
        )
        if config.api_key:
            st.caption(f"Loaded key: {redact(config.api_key)}")
