import re
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
        image_score = self._image_score(lost, found)

        final = (
            azure_search_score * 0.25
            + category_score * 0.15
            + text_score * 0.10
            + color_score * 0.10
            + location_score * 0.10
            + time_score * 0.10
            + flight_score * 0.05
            + unique_identifier_score * 0.05
            + image_score * 0.10
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
            "image_score": round(image_score, 2),
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
        values = set()
        for value in raw:
            normalized = self._normalize_identifier(value)
            if normalized:
                values.add(normalized)
        return values

    def _normalize_identifier(self, value: Any) -> str | None:
        text = str(value or "").strip().lower()
        if not text or "[redacted]" in text:
            return None
        return "".join(character for character in text if character.isalnum())

    def _lost_text(self, lost: LostReport) -> str:
        return " ".join(filter(None, [lost.item_title, lost.raw_description, lost.ai_clean_description, lost.brand, lost.model]))

    def _found_text(self, found: FoundItem) -> str:
        return " ".join(
            filter(None, [found.item_title, found.raw_description, found.ai_clean_description, found.brand, found.model, found.vision_ocr_text])
        )

    def _found_flight(self, found: FoundItem) -> str | None:
        value = (found.ai_extracted_attributes_json or {}).get("flight_number")
        return str(value) if value else None

    def _image_score(self, lost: LostReport, found: FoundItem) -> float:
        """0-100 visual similarity from perceptual hash. 0 if either side has no image."""
        from app.services.image_similarity_service import image_similarity_service

        lost_phash = getattr(lost, "proof_phash", None)
        found_phash = getattr(found, "image_phash", None)
        if not lost_phash or not found_phash:
            return 0.0
        return image_similarity_service.phash_similarity(lost_phash, found_phash)

    def evidence_spans(self, lost: LostReport, found: FoundItem) -> dict[str, Any]:
        """Return human-readable spans showing why two records overlap.

        The shape is:
            {
              "lost":  {<facet>: [{"text": str, "start": int, "end": int}]},
              "found": {<facet>: [...]},
              "shared_terms": [str, ...],
              "category_match": bool,
              "color_match": bool,
              "location_match": bool,
              "flight_match": bool,
              "identifier_overlap": [str, ...],
            }
        """
        lost_text = self._lost_text(lost)
        found_text = self._found_text(found)
        spans: dict[str, Any] = {
            "lost": {},
            "found": {},
            "shared_terms": [],
            "category_match": False,
            "color_match": False,
            "location_match": False,
            "flight_match": False,
            "identifier_overlap": [],
        }
        if lost.category and found.category and lost.category.strip().lower() == found.category.strip().lower():
            spans["category_match"] = True
            spans["lost"]["category"] = self._find_spans(lost_text, lost.category)
            spans["found"]["category"] = self._find_spans(found_text, found.category)
        if lost.color and found.color and lost.color.strip().lower() == found.color.strip().lower():
            spans["color_match"] = True
            spans["lost"]["color"] = self._find_spans(lost_text, lost.color)
            spans["found"]["color"] = self._find_spans(found_text, found.color)
        if lost.lost_location and found.found_location and self._fuzzy_eq(lost.lost_location, found.found_location):
            spans["location_match"] = True
            spans["lost"]["location"] = self._find_spans(lost_text, lost.lost_location)
            spans["found"]["location"] = self._find_spans(found_text, found.found_location)
        found_flight = self._found_flight(found)
        if lost.flight_number and found_flight and lost.flight_number.strip().lower().replace(" ", "") == found_flight.strip().lower().replace(" ", ""):
            spans["flight_match"] = True
            spans["lost"]["flight"] = self._find_spans(lost_text, lost.flight_number)
            spans["found"]["flight"] = self._find_spans(found_text, found_flight)
        identifier_overlap = self._ids(lost.ai_extracted_attributes_json) & self._ids(found.ai_extracted_attributes_json)
        if identifier_overlap:
            spans["identifier_overlap"] = sorted(identifier_overlap)
            spans["lost"].setdefault("identifier", [])
            spans["found"].setdefault("identifier", [])
            for ident in identifier_overlap:
                spans["lost"]["identifier"].extend(self._find_spans(lost_text, ident))
                spans["found"]["identifier"].extend(self._find_spans(found_text, ident))
        shared = sorted(self._shared_terms(lost_text, found_text))[:10]
        spans["shared_terms"] = shared
        if shared:
            spans["lost"].setdefault("text", [])
            spans["found"].setdefault("text", [])
            for term in shared:
                spans["lost"]["text"].extend(self._find_spans(lost_text, term))
                spans["found"]["text"].extend(self._find_spans(found_text, term))
        return spans

    @staticmethod
    def _find_spans(haystack: str, needle: str | None, max_hits: int = 3) -> list[dict[str, int | str]]:
        if not haystack or not needle:
            return []
        results: list[dict[str, int | str]] = []
        try:
            pattern = re.compile(re.escape(needle.strip()), re.IGNORECASE)
        except re.error:
            return []
        for match in pattern.finditer(haystack):
            results.append({"text": match.group(0), "start": match.start(), "end": match.end()})
            if len(results) >= max_hits:
                break
        return results

    @staticmethod
    def _shared_terms(left: str, right: str) -> set[str]:
        stop = {
            "the", "a", "an", "and", "or", "of", "for", "with", "in", "on", "at", "to", "from",
            "is", "was", "by", "it", "this", "that", "these", "those", "be", "been",
        }
        left_tokens = {token for token in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", (left or "").lower()) if token not in stop}
        right_tokens = {token for token in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", (right or "").lower()) if token not in stop}
        return left_tokens & right_tokens

    @staticmethod
    def _fuzzy_eq(left: str, right: str) -> bool:
        return SequenceMatcher(None, left.strip().lower(), right.strip().lower()).ratio() >= 0.6


matching_engine = MatchingEngine()
