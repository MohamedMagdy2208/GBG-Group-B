from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any

from app.models.schemas import EntityType, RelationshipType


ALLOWED_ENTITY_TYPES: set[str] = {
    "Concept",
    "Actor",
    "Technology",
    "Outcome",
    "Risk",
    "Study",
    "Method",
    "Metric",
}

ALLOWED_RELATIONSHIP_TYPES: set[str] = {
    "IMPROVES",
    "INCREASES",
    "CAUSES",
    "RAISES",
    "USES",
    "INCLUDES",
    "STUDIES",
    "IDENTIFIES",
    "REPORTS",
    "RECOMMENDS",
    "ENABLES",
}

TYPE_PRIORITY: dict[str, int] = {
    "Concept": 0,
    "Actor": 2,
    "Technology": 4,
    "Outcome": 3,
    "Risk": 3,
    "Study": 4,
    "Method": 3,
    "Metric": 3,
}

CANONICAL_ALIASES = {
    "ai": "artificial intelligence",
    "a i": "artificial intelligence",
    "artificial intelligence ai": "artificial intelligence",
    "ai tools": "artificial intelligence tools",
    "ai based educational platforms": "ai-based educational platforms",
    "ai based education platforms": "ai-based educational platforms",
    "politehnica bucharest": "national university of science and technology politehnica bucharest",
    "students academic development": "student academic development",
    "academic dishonesty risks": "academic dishonesty",
}


class EntityNormalizer:
    """Normalizes names and relation labels into the app's small graph schema."""

    def normalize_name(self, name: str) -> str:
        value = name.strip().lower()
        value = value.replace("’", "'")
        value = re.sub(r"\((.*?)\)", r" \1 ", value)
        value = re.sub(r"[^a-z0-9%]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return CANONICAL_ALIASES.get(value, value)

    def display_name(self, name: str) -> str:
        canonical = self.normalize_name(name)
        if canonical == "artificial intelligence":
            return "Artificial Intelligence"
        if canonical == "ai-based educational platforms":
            return "AI-Based Educational Platforms"
        return " ".join(word.upper() if word in {"ai"} else word.capitalize() for word in canonical.split())

    def normalize_entity_type(self, value: str | None) -> EntityType:
        if not value:
            return "Concept"
        cleaned = value.strip().replace("_", " ").title().replace(" ", "")
        if cleaned in ALLOWED_ENTITY_TYPES:
            return cleaned  # type: ignore[return-value]
        return "Concept"

    def normalize_relationship_type(self, value: str | None) -> RelationshipType | None:
        if not value:
            return None
        cleaned = re.sub(r"[^A-Z_]+", "_", value.strip().upper()).strip("_")
        synonyms = {
            "ENABLE": "ENABLES",
            "ENABLED": "ENABLES",
            "IMPROVE": "IMPROVES",
            "IMPROVED": "IMPROVES",
            "RAISE": "RAISES",
            "USE": "USES",
            "USED": "USES",
            "REPORT": "REPORTS",
            "REPORTED": "REPORTS",
            "IDENTIFY": "IDENTIFIES",
            "IDENTIFIED": "IDENTIFIES",
            "RECOMMEND": "RECOMMENDS",
        }
        cleaned = synonyms.get(cleaned, cleaned)
        if cleaned in ALLOWED_RELATIONSHIP_TYPES:
            return cleaned  # type: ignore[return-value]
        return None

    def entity_id(self, entity_type: str, name: str) -> str:
        normalized = self.normalize_name(name)
        slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "entity"
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
        return f"entity:{slug}:{digest}"

    def relationship_id(
        self,
        source_entity_id: str,
        relationship_type: str,
        target_entity_id: str,
        evidence_chunk_id: str | None,
    ) -> str:
        key = "|".join([source_entity_id, relationship_type, target_entity_id, evidence_chunk_id or ""])
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
        return f"rel:{digest}"


def unique_strings(values: list[str]) -> list[str]:
    unique = OrderedDict()
    for value in values:
        cleaned = str(value).strip()
        if cleaned:
            unique[cleaned] = None
    return list(unique.keys())


def preferred_entity_type(current: str, incoming: str) -> EntityType:
    """Pick the more specific entity type when duplicate names disagree."""
    current_score = TYPE_PRIORITY.get(current, 0)
    incoming_score = TYPE_PRIORITY.get(incoming, 0)
    if incoming_score > current_score:
        return incoming  # type: ignore[return-value]
    return current  # type: ignore[return-value]


def coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return unique_strings([str(item) for item in value])
    return unique_strings([str(value)])


def coerce_int_list(value: Any, fallback: list[int] | None = None) -> list[int]:
    if value is None:
        return fallback or []
    values = value if isinstance(value, list) else [value]
    result: list[int] = []
    for item in values:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return sorted(set(result or (fallback or [])))


def coerce_float(value: Any, default: float = 0.75) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))
