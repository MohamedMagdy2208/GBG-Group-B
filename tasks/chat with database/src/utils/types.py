"""Shared dataclasses used by the Streamlit app and the service layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceItem:
    """A small snippet that explains what evidence supported an answer."""

    kind: str
    title: str
    snippet: str


@dataclass(slots=True)
class QueryResponse:
    """Normalized response object rendered by the UI."""

    answer: str
    sql: str | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    sources: list[SourceItem] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class RetrievalDocument:
    """A text payload that can be embedded and retrieved later."""

    doc_id: str
    title: str
    kind: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

