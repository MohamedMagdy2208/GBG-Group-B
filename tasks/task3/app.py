"""
Azure Document Intelligence - Streamlit App
Entry point: run with `streamlit run app.py`
"""

import sys
import os

# Ensure the project root is on sys.path so sub-packages resolve correctly
# regardless of where Streamlit is launched from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from components.sidebar import render_sidebar
from components.uploader import render_uploader, render_custom_model_uploader
from components.results import render_results
from services.processor import process_document, process_custom_model

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Azure Document Intelligence",
    page_icon="🔍",
    layout="wide",
)

# ── Load custom CSS ─────────────────────────────────────────────────────────────
css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────────
st.title("🔍 Azure Document Intelligence")
st.markdown("Upload a document and select a processing model to extract structured data.")
st.divider()

# ── Sidebar (credentials / settings) ───────────────────────────────────────────
render_sidebar()

# ── Model selector dropdown ─────────────────────────────────────────────────────
MODEL_OPTIONS = [
    "OCR / Read",
    "Layout Analysis",
    "General Documents",
    "Invoices",
    "Receipts",
    "Custom Model",
]

selected_model = st.selectbox(
    "Select a processing model",
    MODEL_OPTIONS,
    index=0,
    key="model_selector",
)

st.divider()

# ── Conditional UI based on selection ──────────────────────────────────────────
if selected_model == "Custom Model":
    uploaded_files = render_custom_model_uploader()

    if uploaded_files and len(uploaded_files) >= 5:
        if st.button("🚀 Process Documents", type="primary"):
            with st.spinner("Processing documents with Custom Model…"):
                result = process_custom_model(uploaded_files)
            render_results(result)
    elif uploaded_files:
        st.warning(f"Please upload at least **5 documents**. You have uploaded {len(uploaded_files)}.")

else:
    uploaded_file = render_uploader(selected_model)

    if uploaded_file is not None:
        if st.button("🚀 Process Document", type="primary"):
            with st.spinner(f"Processing with **{selected_model}** model…"):
                result = process_document(uploaded_file, selected_model)
            render_results(result)