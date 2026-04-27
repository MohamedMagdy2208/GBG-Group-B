from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from app.models import ConfidenceLevel, FoundItem, LostReport


class MatchingEngine:
    def score(self, lost: LostReport, found: FoundItem, azure_search_score: float = 0) -> dict[str, Any]:
        category_score = self._category_score(lost.category, found.category)
        text_score = self._text_score(self._lost_text(lost), self._found_text(found))
        color_score = self._exact_score(lost.color, found.color)
        location_score = self._text_score(lost.lost_location or "", found.found_location or "")
        time_score = self._time_score(lost.lost_datetime, found.found_datetime)
        flight_score = self._exact_score(lost.flight_number, self._found_flight(found))
        unique_identifier_score, identifier_conflict = self._identifier_score(
            lost.ai_extracted_attributes_json,
            found.ai_extracted_attributes_json,
        )

        final = (
            azure_search_score * 0.30
            + category_score * 0.15
            + text_score * 0.15
            + color_score * 0.10
            + location_score * 0.10
            + time_score * 0.10
            + flight_score * 0.05
            + unique_identifier_score * 0.05
        )

        unique_exact = unique_identifier_score == 100
        if unique_exact:
            final = max(final, 90)
        if identifier_conflict:
            final = min(final, 35)
        if category_score < 30 and not unique_exact:
            final = min(final, 60)
        if found.risk_level.value in {"high_value", "sensitive", "dangerous"}:
            final = min(final, 95)

        final = round(max(0, min(100, final)), 2)
        confidence = self.confidence_for_score(final)
        return {
            "match_score": final,
            "azure_search_score": round(azure_search_score, 2),
            "category_score": round(category_score, 2),
            "text_score": round(text_score, 2),
            "color_score": round(color_score, 2),
            "location_score": round(location_score, 2),
            "time_score": round(time_score, 2),
            "flight_score": round(flight_score, 2),
            "unique_identifier_score": round(unique_identifier_score, 2),
            "confidence_level": confidence,
            "identifier_conflict": identifier_conflict,
            "manual_approval_required": found.risk_level.value in {"high_value", "sensitive", "dangerous"},
        }

    def confidence_for_score(self, score: float) -> ConfidenceLevel | None:
        if score >= 85:
            return ConfidenceLevel.high
        if score >= 70:
            return ConfidenceLevel.medium
        if score >= 50:
            return ConfidenceLevel.low
        return None

    def _category_score(self, left: str | None, right: str | None) -> float:
        if not left or not right:
            return 50
        if left.strip().lower() == right.strip().lower():
            return 100
        return 20

    def _exact_score(self, left: str | None, right: str | None) -> float:
        if not left or not right:
            return 0
        return 100 if left.strip().lower().replace(" ", "") == right.strip().lower().replace(" ", "") else 0

    def _text_score(self, left: str, right: str) -> float:
        if not left or not right:
            return 0
        return SequenceMatcher(None, left.lower(), right.lower()).ratio() * 100

    def _time_score(self, lost_at: datetime | None, found_at: datetime | None) -> float:
        if not lost_at or not found_at:
            return 50
        delta_hours = (found_at - lost_at).total_seconds() / 3600
        if delta_hours < 0:
            return 20
        if delta_hours <= 6:
            return 100
        if delta_hours <= 24:
            return 80
        if delta_hours <= 72:
            return 55
        return 25

    def _identifier_score(self, lost_attrs: dict[str, Any] | None, found_attrs: dict[str, Any] | None) -> tuple[float, bool]:
        lost_ids = self._ids(lost_attrs)
        found_ids = self._ids(found_attrs)
        if not lost_ids or not found_ids:
            return 0, False
        if lost_ids & found_ids:
            return 100, False
        return 0, True

    def _ids(self, attrs: dict[str, Any] | None) -> set[str]:
        raw = (attrs or {}).get("unique_identifiers") or []
        if isinstance(raw, str):
            raw = [raw]
        return {str(value).strip().lower() for value in raw if value}

    def _lost_text(self, lost: LostReport) -> str:
        return " ".join(filter(None, [lost.item_title, lost.raw_description, lost.ai_clean_description, lost.brand, lost.model]))

    def _found_text(self, found: FoundItem) -> str:
        return " ".join(
            filter(None, [found.item_title, found.raw_description, found.ai_clean_description, found.brand, found.model, found.vision_ocr_text])
        )

    def _found_flight(self, found: FoundItem) -> str | None:
        value = (found.ai_extracted_attributes_json or {}).get("flight_number")
        return str(value) if value else None


matching_engine = MatchingEngine()
