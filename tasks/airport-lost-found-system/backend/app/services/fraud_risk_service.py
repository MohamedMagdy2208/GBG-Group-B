from __future__ import annotations

from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    ClaimVerification,
    ClaimVerificationStatus,
    FoundItem,
    LostReport,
    MatchCandidate,
    RiskLevel,
)


class FraudRiskService:
    def score_match(
        self,
        db: Session,
        candidate: MatchCandidate,
        contact: str | None = None,
        answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        report = candidate.lost_report
        item = candidate.found_item
        score = 0
        flags: list[str] = []

        if candidate.match_score < 70:
            score += 20
            flags.append("Medium or low match confidence requires stronger evidence.")
        if item.risk_level in {RiskLevel.high_value, RiskLevel.sensitive, RiskLevel.dangerous}:
            score += {"high_value": 20, "sensitive": 25, "dangerous": 35}[item.risk_level.value]
            flags.append(f"{item.risk_level.value.replace('_', ' ').title()} item requires manual verification.")
        if contact and not self._contact_matches(report, contact):
            score += 35
            flags.append("Provided contact does not match the lost report contact.")

        identifier_score, identifier_flags = self._identifier_risk(report, item)
        score += identifier_score
        flags.extend(identifier_flags)

        rejected_claims = (
            db.query(ClaimVerification)
            .filter(
                ClaimVerification.lost_report_id == report.id,
                ClaimVerification.status.in_([ClaimVerificationStatus.rejected, ClaimVerificationStatus.blocked]),
            )
            .count()
        )
        if rejected_claims:
            score += min(30, rejected_claims * 10)
            flags.append("Previous rejected or blocked claim attempts exist for this report.")

        if answers is not None and len([value for value in answers.values() if str(value).strip()]) < 2:
            score += 10
            flags.append("Passenger evidence answers are incomplete.")

        velocity_score, velocity_flags = self._velocity_risk(db, report)
        score += velocity_score
        flags.extend(velocity_flags)

        ip_score, ip_flags = self._ip_risk(db, report)
        score += ip_score
        flags.extend(ip_flags)

        answer_score, answer_flags = self._answer_quality_risk(answers, item)
        score += answer_score
        flags.extend(answer_flags)

        score = max(0, min(100, score))
        return {
            "fraud_score": float(score),
            "fraud_flags": flags,
            "risk_level": item.risk_level,
            "release_blocked": score >= get_settings().fraud_high_risk_threshold or item.risk_level != RiskLevel.normal,
        }

    def _identifier_risk(self, report: LostReport, item: FoundItem) -> tuple[int, list[str]]:
        lost_ids = self._identifiers(report.ai_extracted_attributes_json)
        found_ids = self._identifiers(item.ai_extracted_attributes_json)
        if not lost_ids or not found_ids:
            return 0, []
        if lost_ids & found_ids:
            return -15, ["Unique identifier overlap reduces fraud risk."]
        return 40, ["Unique identifiers conflict between the lost report and found item."]

    def _identifiers(self, attrs: dict[str, Any] | None) -> set[str]:
        if not attrs:
            return set()
        values = attrs.get("unique_identifiers") or attrs.get("unique_identifier") or []
        if isinstance(values, str):
            values = [values]
        return {str(value).strip().lower() for value in values if str(value).strip()}

    def _contact_matches(self, report: LostReport, contact: str) -> bool:
        normalized = contact.strip().lower()
        report_values = {
            (report.contact_email or "").lower(),
            (report.contact_phone or "").lower(),
        }
        return normalized in report_values

    def _velocity_risk(self, db: Session, report: LostReport) -> tuple[int, list[str]]:
        if not report.passenger_id:
            return 0, []
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        count = (
            db.query(LostReport.id)
            .filter(LostReport.passenger_id == report.passenger_id, LostReport.created_at >= cutoff)
            .count()
        )
        if count >= 5:
            return 20, ["Passenger filed 5+ reports in the last 24h — velocity risk."]
        if count >= 3:
            return 10, ["Passenger filed 3+ reports in the last 24h."]
        return 0, []

    def _ip_risk(self, db: Session, report: LostReport) -> tuple[int, list[str]]:
        ip = (report.created_from_ip or "").strip()
        if not ip:
            return 0, []
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        distinct_passengers = (
            db.query(LostReport.passenger_id)
            .filter(LostReport.created_from_ip == ip, LostReport.created_at >= cutoff)
            .distinct()
            .count()
        )
        if distinct_passengers >= 3:
            return 25, ["Multiple distinct passengers filed reports from the same IP in 24h."]
        return 0, []

    def _answer_quality_risk(self, answers: dict[str, Any] | None, item: FoundItem) -> tuple[int, list[str]]:
        if not answers:
            return 0, []
        expected_lists = (item.ai_extracted_attributes_json or {}).get("_verification_keys") or []
        if not expected_lists:
            return 0, []
        # Flatten ordered answers in the same order they were generated.
        ordered = list(answers.values())
        if not ordered:
            return 0, []
        max_pairs = min(len(ordered), len(expected_lists))
        if max_pairs == 0:
            return 0, []
        match_score = 0.0
        for idx in range(max_pairs):
            answer_text = str(ordered[idx] or "").lower()
            keywords = [str(kw).lower() for kw in (expected_lists[idx] or []) if kw]
            if not keywords:
                continue
            best = max(SequenceMatcher(None, answer_text, kw).ratio() for kw in keywords)
            keyword_hit = any(kw and kw in answer_text for kw in keywords)
            match_score += 1 if keyword_hit else best
        avg = match_score / max_pairs if max_pairs else 0
        if avg < 0.25:
            return 15, ["Passenger answers do not match staff-only expected keywords."]
        if avg < 0.5:
            return 5, ["Passenger answers only partially match expected keywords."]
        return -5, ["Passenger answers strongly match staff-only expected keywords."]


fraud_risk_service = FraudRiskService()
