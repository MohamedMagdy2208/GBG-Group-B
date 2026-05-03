"""
Sidebar component — Azure credentials & app settings.
"""

import streamlit as st


def render_sidebar():
    """Render the sidebar with Azure connection settings."""
    with st.sidebar:
        st.header("⚙️ Configuration")

        st.subheader("Azure Credentials")
        endpoint = st.text_input(
            "Endpoint URL",
            value=st.session_state.get("azure_endpoint", ""),
            placeholder="https://<resource>.cognitiveservices.azure.com/",
            type="default",
        )
        api_key = st.text_input(
            "API Key",
            value=st.session_state.get("azure_api_key", ""),
            placeholder="Your Azure API key",
            type="password",
        )

        if st.button("💾 Save Credentials"):
            st.session_state["azure_endpoint"] = endpoint
            st.session_state["azure_api_key"] = api_key
            st.success("Credentials saved for this session.")

        st.divider()
        st.subheader("Custom Model Settings")
        custom_model_id = st.text_input(
            "Custom Model ID",
            value=st.session_state.get("custom_model_id", ""),
            placeholder="e.g. my-custom-model-v1",
        )
        if custom_model_id:
            st.session_state["custom_model_id"] = custom_model_id

        st.divider()
        st.caption("Azure Document Intelligence · Streamlit UI")