"""Streamlit entrypoint for the chat-with-database RAG application."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.config.settings import get_settings
from src.database.client import build_database_manager
from src.services.rag_pipeline import ChatWithDatabaseService


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "csv"


@st.cache_resource(show_spinner=False)
def get_service() -> ChatWithDatabaseService:
    """Create the service object once per Streamlit session."""

    settings = get_settings()
    if not settings.vector_store_path.is_absolute():
        settings.vector_store_path = PROJECT_ROOT / settings.vector_store_path
    db = build_database_manager(settings)
    return ChatWithDatabaseService(settings=settings, db=db, data_dir=DATA_DIR)


def render_sidebar(service: ChatWithDatabaseService) -> None:
    """Render setup and maintenance actions."""

    st.sidebar.title("Project Controls")
    st.sidebar.write("Use these actions to initialize the database and rebuild retrieval assets.")

    if st.sidebar.button("Health Check"):
        try:
            service.db.healthcheck()
            st.sidebar.success("Database connection succeeded.")
        except Exception as error:
            st.sidebar.error(f"Database health check failed: {error}")

    if st.sidebar.button("Initialize Database"):
        try:
            result = service.ensure_bootstrap(replace_existing=False)
            st.sidebar.success(f"Initialization result: {result['status']}")
        except Exception as error:
            st.sidebar.error(f"Initialization failed: {error}")

    if st.sidebar.button("Rebuild Knowledge Base"):
        try:
            service.refresh_knowledge_base()
            st.sidebar.success("Vector store rebuilt successfully.")
        except Exception as error:
            st.sidebar.error(f"Knowledge base rebuild failed: {error}")


def render_response(response) -> None:
    """Render the answer payload in the main content area."""

    if response.error:
        st.error(response.error)
    st.markdown(response.answer)
    if response.sql:
        with st.expander("Generated SQL", expanded=False):
            st.code(response.sql, language="sql")
    if response.rows:
        with st.expander("Query Results", expanded=True):
            st.dataframe(response.rows, use_container_width=True)
    if response.sources:
        with st.expander("Retrieved Sources", expanded=False):
            for source in response.sources:
                st.markdown(f"**{source.kind}: {source.title}**")
                st.caption(source.snippet)


def main() -> None:
    """Run the Streamlit application."""

    st.set_page_config(page_title="Chat with Database RAG", page_icon=":bar_chart:", layout="wide")
    st.title("Chat with Database RAG")
    st.write(
        "Ask business questions about the music-store dataset. "
        "The app retrieves schema context, generates PostgreSQL, executes it, and explains the result."
    )

    service = get_service()
    render_sidebar(service)

    if "history" not in st.session_state:
        st.session_state.history = []

    for item in st.session_state.history:
        with st.chat_message(item["role"]):
            if item["role"] == "assistant":
                render_response(item["payload"])
            else:
                st.markdown(item["content"])

    user_question = st.chat_input("Ask a business question about customers, sales, tracks, artists, or invoices.")
    if user_question:
        st.session_state.history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking through the schema and querying the database..."):
                response = service.answer_question(user_question)
            render_response(response)
        st.session_state.history.append({"role": "assistant", "payload": response})


if __name__ == "__main__":
    main()

