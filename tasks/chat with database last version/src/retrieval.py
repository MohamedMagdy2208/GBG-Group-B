import hashlib
import json
import math

import streamlit as st
from langchain_openai import AzureOpenAIEmbeddings

from src.config import (
    AZURE_OPENAI_EMBEDDING_API_VERSION,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    FEWSHOT_TOP_K,
    USE_EMBEDDING_RETRIEVAL,
    require_env_vars,
)
from src.prompts import load_fewshots


def _example_text(example: dict[str, str]) -> str:
    return (
        f"Question: {example['naturalQuestion']}\n"
        f"SQL pattern: {example['sqlQuery']}"
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _fewshot_digest(examples: list[dict[str, str]]) -> str:
    payload = json.dumps(examples, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@st.cache_resource
def get_embedding_model():
    if not AZURE_OPENAI_EMBEDDING_DEPLOYMENT:
        raise RuntimeError(
            "USE_EMBEDDING_RETRIEVAL is enabled, but "
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT is not set."
        )

    env = require_env_vars("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")
    return AzureOpenAIEmbeddings(
        azure_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        azure_endpoint=env["AZURE_OPENAI_ENDPOINT"],
        api_key=env["AZURE_OPENAI_API_KEY"],
        api_version=AZURE_OPENAI_EMBEDDING_API_VERSION,
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    )


@st.cache_resource
def _build_fewshot_index(examples_digest: str):
    del examples_digest
    examples = load_fewshots()
    texts = [_example_text(example) for example in examples]
    vectors = get_embedding_model().embed_documents(texts)
    return list(zip(examples, vectors))


def select_relevant_fewshots(question: str) -> list[dict[str, str]]:
    examples = load_fewshots()
    if not USE_EMBEDDING_RETRIEVAL:
        return examples

    top_k = max(1, min(FEWSHOT_TOP_K, len(examples)))
    index = _build_fewshot_index(_fewshot_digest(examples))
    question_vector = get_embedding_model().embed_query(question)
    scored_examples = sorted(
        (
            (_cosine_similarity(question_vector, vector), example)
            for example, vector in index
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    return [example for _, example in scored_examples[:top_k]]
