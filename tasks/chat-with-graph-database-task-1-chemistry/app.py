from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chemgraph_chat.config import ConfigError, Settings, load_settings
from chemgraph_chat.cypher_guard import CypherValidationError
from chemgraph_chat.db import create_driver, make_query_runner, verify_connectivity
from chemgraph_chat.llm import build_graph_assistant
from chemgraph_chat.pipeline import GraphChatService
from chemgraph_chat.schema import get_schema_summary


EXAMPLES = [
    "Which drugs treat diseases affecting humans?",
    "What compound is produced by C + O2?",
    "Which elements are reactants for methane?",
    "What organisms are affected by headache?",
]


@st.cache_resource(show_spinner=False)
def cached_driver(settings: Settings):
    return create_driver(settings)


@st.cache_data(show_spinner=False, ttl=300)
def cached_schema(_driver: Any, database: str) -> str:
    return get_schema_summary(_driver, database)


def get_service(settings: Settings) -> GraphChatService:
    driver = cached_driver(settings)
    return GraphChatService(
        assistant=build_graph_assistant(settings),
        schema_provider=lambda: cached_schema(driver, settings.neo4j_database),
        query_runner=make_query_runner(driver, settings.neo4j_database),
        max_rows=settings.max_result_rows,
    )


def render_message(message: dict[str, Any]) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        result = message.get("result")
        if result:
            with st.expander("Cypher"):
                st.code(result["cypher"], language="cypher")
                if result["parameters"]:
                    st.json(result["parameters"])
                if result["reason"]:
                    st.caption(result["reason"])
            with st.expander("Rows"):
                st.dataframe(result["rows"], use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Chemistry Graph Chat", page_icon="Graph", layout="wide")
    st.title("Chemistry Graph Chat")
    st.caption("Ask questions about elements, reactions, compounds, drugs, diseases, and organisms.")

    try:
        settings = load_settings()
    except ConfigError as exc:
        st.error(str(exc))
        st.info("Create a `.env` file from `.env.example`, then restart Streamlit.")
        return

    driver = cached_driver(settings)

    with st.sidebar:
        st.header("Connection")
        try:
            verify_connectivity(driver, settings.neo4j_database)
            st.success(f"Neo4j connected: {settings.neo4j_database}")
        except Exception as exc:
            st.error(f"Neo4j connection failed: {exc}")
            return

        if settings.openai_provider == "azure":
            st.caption("Provider: Azure OpenAI")
            st.caption(f"Azure deployment: {settings.azure_openai_deployment}")
            st.caption("API: Chat Completions")
        else:
            st.caption("Provider: OpenAI")
            st.caption(f"OpenAI model: {settings.openai_model}")
        st.divider()
        st.subheader("Try a question")
        selected_example = None
        for example in EXAMPLES:
            if st.button(example, use_container_width=True):
                selected_example = example

        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        render_message(message)

    typed_prompt = st.chat_input("Ask a question about the graph")
    prompt = selected_example or typed_prompt

    if not prompt:
        return

    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    render_message(user_message)

    service = get_service(settings)
    history = [
        {"role": message["role"], "content": message["content"]}
        for message in st.session_state.messages
        if message["role"] in {"user", "assistant"}
    ]

    with st.chat_message("assistant"):
        try:
            with st.status("Thinking through the graph", expanded=False):
                result = service.ask(prompt, history=history)
            st.markdown(result.answer)
            payload = {
                "cypher": result.cypher,
                "parameters": result.parameters,
                "reason": result.reason,
                "rows": result.rows,
            }
            with st.expander("Cypher"):
                st.code(result.cypher, language="cypher")
                if result.parameters:
                    st.json(result.parameters)
                if result.reason:
                    st.caption(result.reason)
            with st.expander("Rows"):
                st.dataframe(result.rows, use_container_width=True)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result.answer,
                    "result": payload,
                }
            )
        except CypherValidationError as exc:
            message = f"I blocked the generated Cypher because it was not read-only: {exc}"
            st.warning(message)
            st.session_state.messages.append({"role": "assistant", "content": message})
        except Exception as exc:
            message = f"Something went wrong while answering: {exc}"
            st.error(message)
            st.session_state.messages.append({"role": "assistant", "content": message})


if __name__ == "__main__":
    main()
