"""Result rendering for Azure Document Intelligence responses."""

from __future__ import annotations

import json
import html

import pandas as pd
import streamlit as st

from utils.formatters import (
    fields_to_dataframe,
    pages_to_dataframe,
    result_to_dataframe,
    tables_to_dataframes,
    to_azure_studio_json,
)


def render_results(result: dict):
    """Render full SDK result dictionaries with Studio-like tabs."""

    if not result:
        st.warning("No results to display.")
        return

    if "error" in result:
        st.error(result["error"])
        return

    st.markdown("---")
    st.subheader("Results")

    if result.get("model_id") == "annotation-based":
        _render_annotation_result(result)
        return

    summary_tab, fields_tab, tables_tab, pages_tab, json_tab = st.tabs(
        ["Summary", "Fields", "Tables", "Pages", "JSON"]
    )

    with summary_tab:
        _render_summary(result)

    with fields_tab:
        fields_df = fields_to_dataframe(result)
        if fields_df.empty:
            st.info("No structured fields were returned.")
        else:
            st.dataframe(fields_df, use_container_width=True)
            _download_dataframe(fields_df, "fields.csv")

    with tables_tab:
        table_dfs = tables_to_dataframes(result)
        if not table_dfs:
            st.info("No tables were returned.")
        for name, df in table_dfs:
            st.markdown(f"#### {name}")
            st.dataframe(df, use_container_width=True)
            _download_dataframe(df, f"{name.lower().replace(' ', '_')}.csv")

    with pages_tab:
        pages_df = pages_to_dataframe(result)
        if pages_df.empty:
            st.info("No page lines, words, or selection marks were returned.")
        else:
            st.dataframe(pages_df, use_container_width=True)
            _download_dataframe(pages_df, "pages.csv")
        with st.expander("Full content", expanded=False):
            st.text(result.get("content", ""))

    with json_tab:
        json_view = st.radio(
            "JSON view",
            ["Azure Studio", "Raw SDK"],
            horizontal=True,
            label_visibility="collapsed",
        )
        payload = to_azure_studio_json(result) if json_view == "Azure Studio" else result
        st.json(payload, expanded=True)
        json_str = json.dumps(payload, indent=2, ensure_ascii=False)
        json_name = "azure_studio_result.json" if json_view == "Azure Studio" else "raw_sdk_result.json"
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=json_name,
            mime="application/json",
        )
        table = result_to_dataframe(result, result.get("model_id", ""))
        if table is not None and not table.empty:
            _download_dataframe(table, "result.csv")


def _render_summary(result: dict):
    documents = result.get("documents", []) or []
    pages = result.get("pages", []) or []
    tables = result.get("tables", []) or []

    _render_summary_cards(
        [
            ("Model", result.get("model_id", result.get("modelId", "unknown"))),
            ("Pages", len(pages)),
            ("Documents", len(documents)),
            ("Tables", len(tables)),
        ]
    )

    if result.get("apiVersion") or result.get("api_version"):
        st.caption(f"API version: {result.get('apiVersion') or result.get('api_version')}")
    if result.get("file_name"):
        st.caption(f"File: {result['file_name']}")

    doc_rows = []
    for idx, document in enumerate(documents):
        doc_rows.append(
            {
                "Document": idx + 1,
                "Type": document.get("docType") or document.get("doc_type", ""),
                "Confidence": document.get("confidence", ""),
                "Fields": len(document.get("fields", {}) or {}),
            }
        )
    if doc_rows:
        st.markdown("#### Documents")
        st.dataframe(pd.DataFrame(doc_rows), use_container_width=True)


def _render_summary_cards(items: list[tuple[str, object]]):
    st.markdown(_summary_cards_html(items), unsafe_allow_html=True)


def _summary_cards_html(items: list[tuple[str, object]]) -> str:
    cards = []
    for label, value in items:
        safe_label = html.escape(str(label))
        safe_value = html.escape(str(value))
        cards.append(
            '<div class="di-summary-card">'
            f'<div class="di-summary-label">{safe_label}</div>'
            f'<div class="di-summary-value">{safe_value}</div>'
            "</div>"
        )
    return f'<div class="di-summary-grid">{"".join(cards)}</div>'


def _download_dataframe(df: pd.DataFrame, file_name: str):
    st.download_button(
        label=f"Download {file_name}",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=file_name,
        mime="text/csv",
        key=f"download_{file_name}_{len(df)}",
    )


def _render_annotation_result(result: dict):
    """Special renderer for local annotation matching results."""

    if "warning" in result:
        st.warning(result["warning"])

    st.markdown(
        f"**File:** `{result.get('file_name', '-')}` | "
        f"**Match rate:** `{result.get('match_rate', '-')}`"
    )

    matched = result.get("matched_fields", [])
    unmatched = result.get("unmatched_annotations", [])
    skipped = result.get("skipped_annotations", [])

    col_a, col_b, col_c = st.columns(3, gap="large")

    with col_a:
        st.markdown("#### Matched fields")
        st.dataframe(pd.DataFrame(matched), use_container_width=True) if matched else st.info(
            "No fields matched."
        )

    with col_b:
        st.markdown("#### Unmatched annotations")
        st.dataframe(pd.DataFrame(unmatched), use_container_width=True) if unmatched else st.success(
            "No unmatched non-empty annotations."
        )

    with col_c:
        st.markdown("#### Skipped")
        st.dataframe(pd.DataFrame(skipped), use_container_width=True) if skipped else st.info(
            "No empty annotation values."
        )

    with st.expander("Full OCR text"):
        st.text(result.get("ocr_content", ""))
