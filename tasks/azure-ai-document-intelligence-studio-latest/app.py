"""Azure Document Intelligence Studio-Core Streamlit app.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys
import json

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from components.custom_studio import render_custom_studio, render_model_manager
from components.prebuilt import render_prebuilt_analyzer
from components.sidebar import render_sidebar


st.set_page_config(
    page_title="Azure Document Intelligence Studio-Core",
    page_icon=":page_facing_up:",
    layout="wide",
)


def _load_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, encoding="utf-8") as f:
            css = f.read()
        components.html(
            f"""
            <script>
            const css = {json.dumps(css)};
            const id = "azure-di-studio-css";
            const root = window.parent.document;
            let style = root.getElementById(id);
            if (!style) {{
              style = root.createElement("style");
              style.id = id;
              root.head.appendChild(style);
            }}
            style.textContent = css;
            </script>
            """,
            height=0,
        )


_load_css()
render_sidebar()

st.title("Azure Document Intelligence Studio-Core")
st.caption(
    "Analyze documents with supported prebuilt models, prepare labeled datasets, "
    "train custom extraction models, and test deployed model IDs."
)

prebuilt_tab, custom_tab, models_tab = st.tabs(
    ["Prebuilt analysis", "Custom project", "Model management"]
)

with prebuilt_tab:
    render_prebuilt_analyzer()

with custom_tab:
    render_custom_studio()

with models_tab:
    render_model_manager()
