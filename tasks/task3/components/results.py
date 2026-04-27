"""
Results component — renders raw JSON and structured table side by side.
"""

import json
import streamlit as st
import pandas as pd
from utils.formatters import result_to_dataframe


def render_results(result: dict):
    if not result:
        st.warning("No results to display.")
        return

    # Surface errors clearly
    if "error" in result:
        st.error(f"❌ {result['error']}")
        return

    st.divider()
    st.subheader("📊 Results")

    col_json, col_table = st.columns(2, gap="large")

    # ── Raw JSON ──────────────────────────────────────────────────────────────
    with col_json:
        st.markdown("#### 🗂️ Raw JSON Output")
        st.json(result, expanded=True)
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_str,
            file_name="result.json",
            mime="application/json",
        )

    # ── Structured table ──────────────────────────────────────────────────────
    with col_table:
        st.markdown("#### 📋 Structured Table")
        model_id = result.get("model_id", "")
        df = result_to_dataframe(result, model_id)

        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="result.csv",
                mime="text/csv",
            )
        else:
            st.info("No tabular data could be extracted. Check the JSON output.")