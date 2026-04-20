from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ConfigurationError, Settings, get_settings
from app.services.azure_openai_client import AzureOpenAIService
from app.services.graph_store import Neo4jGraphStore
from app.services.hybrid_retriever import HybridRetriever
from app.services.pipeline import IngestionPipeline
from app.services.vector_store import AzureEmbeddingProvider, ChromaVectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


def main() -> None:
    st.set_page_config(page_title="Graph RAG PDF Chat", page_icon="G", layout="wide")
    settings = get_settings()

    st.title("Graph RAG PDF Chat")
    st.caption("Build a Neo4j knowledge graph, index PDF chunks, and ask grounded questions.")

    selected_pdf = _sidebar(settings)
    source_pdf = selected_pdf.name if selected_pdf else None

    chat_tab, evidence_tab, entities_tab, relationships_tab, summary_tab = st.tabs(
        ["Chat", "Retrieved Evidence", "Extracted Entities", "Extracted Relationships", "Graph Summary"]
    )

    with chat_tab:
        _render_ingestion(settings, selected_pdf)
        _render_chat(settings, source_pdf)

    with evidence_tab:
        _render_last_evidence()

    with entities_tab:
        _render_entities(settings, source_pdf)

    with relationships_tab:
        _render_relationships(settings, source_pdf)

    with summary_tab:
        _render_summary(settings, source_pdf)
        _render_intermediate_files(settings)


def _sidebar(settings: Settings) -> Path | None:
    st.sidebar.header("Setup")
    _status_line("Azure GPT-4o", settings.azure_chat_configured)
    _status_line("Azure embeddings", settings.azure_embeddings_configured)
    _status_line("Neo4j env vars", settings.neo4j_configured)
    if not (settings.azure_chat_configured and settings.azure_embeddings_configured and settings.neo4j_configured):
        st.sidebar.info("Copy `.env.example` to `.env`, fill Azure values, then run Neo4j and ingestion.")

    st.sidebar.divider()
    st.sidebar.subheader("PDF")
    options: list[Path] = []
    if settings.sample_pdf_path.exists():
        options.append(settings.sample_pdf_path)

    upload = st.sidebar.file_uploader("Upload another PDF", type=["pdf"])
    uploaded_path: Path | None = None
    if upload is not None:
        upload_dir = settings.data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        uploaded_path = upload_dir / upload.name
        uploaded_path.write_bytes(upload.getbuffer())
        options.insert(0, uploaded_path)

    if not options:
        st.sidebar.warning("No PDF found. Add a PDF or set SAMPLE_PDF_PATH.")
        return None

    labels = [path.name for path in options]
    selected_label = st.sidebar.selectbox("PDF to use", labels, index=0)
    return options[labels.index(selected_label)]


def _render_ingestion(settings: Settings, pdf_path: Path | None) -> None:
    st.subheader("Ingestion")
    if pdf_path is None:
        st.info("Choose or upload a PDF to begin.")
        return

    left, right = st.columns([2, 1])
    with left:
        st.write(f"Selected PDF: `{pdf_path.name}`")
        st.caption("Ingestion writes raw text, chunks, extraction JSON, Neo4j records, and Chroma vectors.")
    with right:
        rebuild = st.checkbox("Rebuild this PDF", value=False)

    if st.button("Ingest selected PDF", type="primary", use_container_width=True):
        try:
            with st.status("Running ingestion pipeline...", expanded=True) as status:
                st.write("Parsing PDF and preserving page metadata")
                pipeline = IngestionPipeline(settings)
                result = pipeline.run(pdf_path, rebuild=rebuild)
                st.write(f"Saved raw text: `{result.raw_path}`")
                st.write(f"Saved chunks: `{result.chunks_path}`")
                st.write(f"Saved graph extraction JSON: `{result.extractions_path}`")
                st.write(f"Chunks: {len(result.chunks)}")
                st.write(
                    "Extracted entities: "
                    f"{sum(len(item.entities) for item in result.extractions)}"
                )
                st.write(
                    "Extracted relationships: "
                    f"{sum(len(item.relationships) for item in result.extractions)}"
                )
                status.update(label="Ingestion complete", state="complete")
            st.success("PDF is ready for hybrid graph + vector chat.")
        except ConfigurationError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.exception(exc)


def _render_chat(settings: Settings, source_pdf: str | None) -> None:
    st.subheader("Ask the paper")
    _render_sample_questions()
    for message in st.session_state.get("messages", []):
        st.chat_message(message["role"]).write(message["content"])

    question = st.chat_input("Ask about AI, academic performance, risks, methods, or statistics")
    if not question:
        question = st.session_state.pop("pending_question", None)
    if not question:
        return

    st.session_state.setdefault("messages", []).append({"role": "user", "content": question})
    st.chat_message("user").write(question)
    try:
        llm = AzureOpenAIService(settings)
        graph_store = Neo4jGraphStore(settings)
        vector_store = ChromaVectorStore(settings, AzureEmbeddingProvider(llm))
        try:
            retriever = HybridRetriever(settings, llm, graph_store, vector_store)
            result = retriever.answer(question, source_pdf=source_pdf)
        finally:
            graph_store.close()

        st.session_state["last_answer"] = result.to_dict()
        st.session_state["messages"].append({"role": "assistant", "content": result.answer})
        st.chat_message("assistant").write(result.answer)
    except ConfigurationError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.exception(exc)


def _render_last_evidence() -> None:
    result = st.session_state.get("last_answer")
    if not result:
        st.info("Ask a question to see retrieved text chunks and graph evidence.")
        return

    st.subheader("Last answer")
    st.write(result.get("answer", ""))

    st.subheader("Detected entities and concepts")
    st.write(result.get("detected_entities", []))

    st.subheader("Text chunks")
    text_evidence = result.get("text_evidence", [])
    if text_evidence:
        for item in text_evidence:
            with st.expander(
                f"{item['chunk_id']} | pages {item.get('page_numbers')} | score {item.get('score')}"
            ):
                st.write(item.get("text", ""))
    else:
        st.info("No text chunks retrieved.")

    st.subheader("Graph evidence")
    graph_evidence = result.get("graph_evidence", [])
    if graph_evidence:
        st.dataframe(graph_evidence, use_container_width=True)
    else:
        st.info("No graph evidence retrieved.")


def _render_entities(settings: Settings, source_pdf: str | None) -> None:
    st.subheader("Extracted entities")
    rows = _safe_graph_call(settings, lambda store: store.list_entities(source_pdf=source_pdf))
    if rows is None:
        rows = _entities_from_latest_json(settings)
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No entities available yet.")


def _render_relationships(settings: Settings, source_pdf: str | None) -> None:
    st.subheader("Extracted relationships")
    rows = _safe_graph_call(settings, lambda store: store.list_relationships(source_pdf=source_pdf))
    if rows is None:
        rows = _relationships_from_latest_json(settings)
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No relationships available yet.")


def _render_summary(settings: Settings, source_pdf: str | None) -> None:
    st.subheader("Graph build status")
    summary = _safe_graph_call(settings, lambda store: store.summary(source_pdf=source_pdf))
    if summary:
        cols = st.columns(4)
        for col, (label, value) in zip(cols, summary.items()):
            col.metric(label.replace("_", " ").title(), value)
    else:
        st.info("Neo4j summary is unavailable until Neo4j is configured and ingestion has run.")


def _render_intermediate_files(settings: Settings) -> None:
    st.subheader("Intermediate JSON")
    files = sorted(settings.raw_dir.glob("*.json")) + sorted(settings.processed_dir.glob("*.json"))
    if not files:
        st.info("No intermediate files written yet.")
        return
    for path in files[-8:]:
        st.write(f"`{path.relative_to(settings.project_root)}`")


def _safe_graph_call(settings: Settings, callback):
    try:
        store = Neo4jGraphStore(settings)
        try:
            return callback(store)
        finally:
            store.close()
    except Exception:
        return None


def _entities_from_latest_json(settings: Settings) -> list[dict[str, Any]]:
    payload = _latest_extraction_payload(settings)
    rows: list[dict[str, Any]] = []
    for extraction in payload:
        rows.extend(extraction.get("entities", []))
    return rows


def _relationships_from_latest_json(settings: Settings) -> list[dict[str, Any]]:
    payload = _latest_extraction_payload(settings)
    rows: list[dict[str, Any]] = []
    for extraction in payload:
        rows.extend(extraction.get("relationships", []))
    return rows


def _latest_extraction_payload(settings: Settings) -> list[dict[str, Any]]:
    files = sorted(settings.processed_dir.glob("*_extractions.json"), key=lambda path: path.stat().st_mtime)
    if not files:
        return []
    return json.loads(files[-1].read_text(encoding="utf-8"))


def _status_line(label: str, ok: bool) -> None:
    if ok:
        st.sidebar.success(f"{label}: OK")
    else:
        st.sidebar.warning(f"{label}: missing")


def _render_sample_questions() -> None:
    questions = [
        "How does AI affect academic performance?",
        "What risks does the paper identify?",
        "What percentage of students use virtual assistants?",
        "What methods did the study use?",
    ]
    cols = st.columns(4)
    for col, question in zip(cols, questions):
        if col.button(question, use_container_width=True):
            st.session_state["pending_question"] = question


if __name__ == "__main__":
    main()
