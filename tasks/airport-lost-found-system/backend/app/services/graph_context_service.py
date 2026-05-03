from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import mask_phone, mask_sensitive_text
from app.models import (
    AuditLog,
    BarcodeLabel,
    ClaimVerification,
    CustodyEvent,
    FoundItem,
    LostReport,
    MatchCandidate,
    User,
)
from app.services.azure_openai_service import azure_openai_service
from app.services.cache_service import cache_service


logger = logging.getLogger(__name__)


class GraphContextBuilder:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.evidence: list[str] = []
        self.risk_signals: list[str] = []

    def node(self, node_id: str, label: str, kind: str, properties: dict[str, Any] | None = None) -> str:
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "label": label,
                "type": kind,
                "properties": self._safe(properties or {}),
            }
        return node_id

    def edge(self, source: str, target: str, relationship: str, properties: dict[str, Any] | None = None) -> None:
        self.edges.append(
            {
                "source": source,
                "target": target,
                "relationship": relationship,
                "properties": self._safe(properties or {}),
            }
        )

    def graph(self, scope: str, entity_type: str, entity_id: int, retrieval_query: str) -> dict[str, Any]:
        nodes = list(self.nodes.values())[: self.settings.graph_rag_max_nodes]
        edges = self.edges[: self.settings.graph_rag_max_edges]
        return {
            "scope": scope,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "retrieval_query": retrieval_query,
            "provider": self.settings.graph_rag_provider,
            "nodes": nodes,
            "edges": edges,
            "evidence": self.evidence[:12],
            "risk_signals": self.risk_signals[:12],
            "provenance": {
                "source": "postgres",
                "node_count": len(nodes),
                "edge_count": len(edges),
                "generated_at": datetime.now(UTC).isoformat(),
            },
        }

    def add_report(self, report: LostReport) -> str:
        node_id = self.node(
            f"lost_report:{report.id}",
            report.item_title,
            "lost_report",
            {
                "report_code": report.report_code,
                "category": report.category,
                "color": report.color,
                "status": report.status.value,
                "lost_location": report.lost_location,
                "lost_datetime": report.lost_datetime,
                "flight_number": report.flight_number,
                "contact_phone": mask_phone(report.contact_phone),
                "contact_email_domain": _email_domain(report.contact_email),
            },
        )
        if report.passenger:
            passenger_id = self.node(
                f"user:{report.passenger.id}",
                report.passenger.name,
                "passenger",
                {"role": report.passenger.role.value, "phone": mask_phone(report.passenger.phone), "email_domain": _email_domain(report.passenger.email)},
            )
            self.edge(passenger_id, node_id, "REPORTED")
        self._add_category_location_flight(node_id, report.category, report.lost_location, report.flight_number, "LOST_AT")
        return node_id

    def add_found_item(self, item: FoundItem) -> str:
        node_id = self.node(
            f"found_item:{item.id}",
            item.item_title,
            "found_item",
            {
                "category": item.category,
                "color": item.color,
                "status": item.status.value,
                "risk_level": item.risk_level.value,
                "found_location": item.found_location,
                "found_datetime": item.found_datetime,
                "storage_location": item.storage_location,
                "vision_ocr_present": bool(item.vision_ocr_text),
            },
        )
        self._add_category_location_flight(node_id, item.category, item.found_location, None, "FOUND_AT")
        if item.storage_location:
            storage_id = self.node(f"storage:{_slug(item.storage_location)}", item.storage_location, "storage_location")
            self.edge(node_id, storage_id, "STORED_AT")
        if item.risk_level.value != "normal":
            self.risk_signals.append(f"Found item is marked {item.risk_level.value.replace('_', ' ')}.")
        return node_id

    def add_match(self, candidate: MatchCandidate) -> str:
        node_id = self.node(
            f"match:{candidate.id}",
            f"Match {candidate.id}",
            "match_candidate",
            {
                "score": candidate.match_score,
                "confidence": candidate.confidence_level.value,
                "status": candidate.status.value,
                "category_score": candidate.category_score,
                "color_score": candidate.color_score,
                "location_score": candidate.location_score,
                "time_score": candidate.time_score,
                "flight_score": candidate.flight_score,
                "unique_identifier_score": candidate.unique_identifier_score,
            },
        )
        lost_id = self.add_report(candidate.lost_report)
        found_id = self.add_found_item(candidate.found_item)
        self.edge(lost_id, node_id, "HAS_CANDIDATE")
        self.edge(node_id, found_id, "CANDIDATE_FOR")
        self._add_match_evidence(candidate)
        return node_id

    def add_claim(self, claim: ClaimVerification) -> str:
        node_id = self.node(
            f"claim:{claim.id}",
            f"Claim {claim.id}",
            "claim_verification",
            {
                "status": claim.status.value,
                "fraud_score": claim.fraud_score,
                "fraud_flags": claim.fraud_flags_json,
                "submitted_at": claim.submitted_at,
                "reviewed_at": claim.reviewed_at,
                "released_at": claim.released_at,
            },
        )
        self.edge(f"match:{claim.match_candidate_id}", node_id, "HAS_CLAIM_VERIFICATION")
        if claim.fraud_score >= self.settings.fraud_high_risk_threshold:
            self.risk_signals.append(f"Claim {claim.id} fraud score is {claim.fraud_score:.0f}/100.")
        for flag in claim.fraud_flags_json or []:
            self.risk_signals.append(str(flag))
        return node_id

    def add_custody(self, event: CustodyEvent) -> str:
        node_id = self.node(
            f"custody:{event.id}",
            event.action.value,
            "custody_event",
            {"action": event.action.value, "location": event.location, "timestamp": event.timestamp, "notes": event.notes},
        )
        self.edge(f"found_item:{event.found_item_id}", node_id, "HAS_CUSTODY_EVENT")
        if event.staff:
            staff_id = self.node(f"user:{event.staff.id}", event.staff.name, "staff", {"role": event.staff.role.value})
            self.edge(staff_id, node_id, "RECORDED")
        return node_id

    def add_label(self, label: BarcodeLabel) -> str:
        node_id = self.node(
            f"label:{label.id}",
            label.label_code,
            "qr_label",
            {"status": label.status.value, "scan_count": label.scan_count, "last_scanned_at": label.last_scanned_at},
        )
        self.edge(f"{label.entity_type}:{label.entity_id}", node_id, "HAS_QR_LABEL")
        if label.scan_count > 0:
            self.evidence.append(f"QR label {label.label_code} has been scanned {label.scan_count} time(s).")
        return node_id

    def add_audit(self, log: AuditLog) -> str:
        node_id = self.node(
            f"audit:{log.id}",
            log.action,
            "audit_log",
            {"action": log.action, "severity": log.severity.value, "actor_role": log.actor_role, "created_at": log.created_at},
        )
        if log.entity_type and log.entity_id:
            self.edge(f"{log.entity_type}:{log.entity_id}", node_id, "HAS_AUDIT_EVENT")
        if log.severity.value in {"warning", "critical"}:
            self.risk_signals.append(f"Audit event {log.action} has {log.severity.value} severity.")
        return node_id

    def _add_category_location_flight(self, source_id: str, category: str | None, location: str | None, flight: str | None, location_edge: str) -> None:
        if category:
            category_id = self.node(f"category:{_slug(category)}", category, "category")
            self.edge(source_id, category_id, "IN_CATEGORY")
        if location:
            location_id = self.node(f"location:{_slug(location)}", location, "airport_location")
            self.edge(source_id, location_id, location_edge)
        if flight:
            flight_id = self.node(f"flight:{_slug(flight)}", flight, "flight")
            self.edge(source_id, flight_id, "RELATED_FLIGHT")

    def _add_match_evidence(self, candidate: MatchCandidate) -> None:
        lost = candidate.lost_report
        found = candidate.found_item
        self.evidence.append(f"Hybrid/vector score contributed {candidate.azure_search_score:.0f}/100 to candidate {candidate.id}.")
        if _same(lost.category, found.category):
            self.evidence.append(f"Both records are in category {lost.category}.")
        else:
            self.risk_signals.append(f"Category differs: lost={lost.category or 'unknown'}, found={found.category or 'unknown'}.")
        if _same(lost.color, found.color):
            self.evidence.append(f"Both records mention color {lost.color}.")
        if _same(lost.lost_location, found.found_location):
            self.evidence.append(f"Lost and found locations both point to {lost.lost_location}.")
        if lost.flight_number and lost.flight_number == found.ai_extracted_attributes_json.get("flight_number"):
            self.evidence.append(f"Flight number {lost.flight_number} appears in both graph neighborhoods.")
        if candidate.unique_identifier_score > 0:
            self.evidence.append("Unique identifier evidence supports this candidate.")
        if candidate.unique_identifier_score < 0:
            self.risk_signals.append("Unique identifier evidence conflicts.")

    def _safe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: _safe_graph_value(value) for key, value in payload.items()}


class GraphContextService:
    async def match_context(self, db: Session, match_id: int, question: str | None = None) -> dict[str, Any]:
        cache_key = f"graph-context:match:{match_id}:{_digest(question or '')}"
        cached = await cache_service.get_json(cache_key)
        if cached:
            return cached
        candidate = (
            db.query(MatchCandidate)
            .options(
                joinedload(MatchCandidate.lost_report).joinedload(LostReport.passenger),
                joinedload(MatchCandidate.found_item).joinedload(FoundItem.custody_events).joinedload(CustodyEvent.staff),
            )
            .filter(MatchCandidate.id == match_id)
            .one_or_none()
        )
        if not candidate:
            raise ValueError("match_not_found")

        builder = GraphContextBuilder()
        builder.add_match(candidate)
        for claim in db.query(ClaimVerification).filter(ClaimVerification.match_candidate_id == match_id).all():
            builder.add_claim(claim)
        self._add_found_side_context(db, builder, candidate.found_item_id)
        self._add_report_side_context(db, builder, candidate.lost_report_id)
        context = builder.graph("match_neighborhood", "match_candidate", match_id, question or "Explain this match using graph evidence.")
        context["generated_summary"] = await self._safe_summary(context, question)
        await cache_service.set_json(cache_key, context, get_settings().graph_rag_context_ttl_seconds)
        return context

    async def found_item_context(self, db: Session, item_id: int, question: str | None = None) -> dict[str, Any]:
        item = db.get(FoundItem, item_id)
        if not item:
            raise ValueError("found_item_not_found")
        builder = GraphContextBuilder()
        builder.add_found_item(item)
        self._add_found_side_context(db, builder, item_id)
        for candidate in (
            db.query(MatchCandidate)
            .options(joinedload(MatchCandidate.lost_report), joinedload(MatchCandidate.found_item))
            .filter(MatchCandidate.found_item_id == item_id)
            .order_by(MatchCandidate.match_score.desc())
            .limit(8)
            .all()
        ):
            builder.add_match(candidate)
        context = builder.graph("found_item_neighborhood", "found_item", item_id, question or "Explain this found item graph.")
        context["generated_summary"] = await self._safe_summary(context, question)
        return context

    async def lost_report_context(self, db: Session, report_id: int, question: str | None = None) -> dict[str, Any]:
        report = (
            db.query(LostReport)
            .options(joinedload(LostReport.passenger))
            .filter(LostReport.id == report_id)
            .one_or_none()
        )
        if not report:
            raise ValueError("lost_report_not_found")
        builder = GraphContextBuilder()
        builder.add_report(report)
        self._add_report_side_context(db, builder, report_id)
        for candidate in (
            db.query(MatchCandidate)
            .options(joinedload(MatchCandidate.lost_report), joinedload(MatchCandidate.found_item))
            .filter(MatchCandidate.lost_report_id == report_id)
            .order_by(MatchCandidate.match_score.desc())
            .limit(8)
            .all()
        ):
            builder.add_match(candidate)
        context = builder.graph("lost_report_neighborhood", "lost_report", report_id, question or "Explain this lost report graph.")
        context["generated_summary"] = await self._safe_summary(context, question)
        return context

    async def _safe_summary(self, context: dict[str, Any], question: str | None = None) -> str:
        try:
            return await azure_openai_service.summarize_graph_context(context, question)
        except Exception:
            logger.exception("Graph RAG summary failed; using deterministic fallback", extra={"event": "graph_summary_fallback"})
            evidence = context.get("evidence") or []
            risks = context.get("risk_signals") or []
            summary = "Graph context is available for staff review."
            if evidence:
                summary += " Evidence: " + "; ".join(str(item) for item in evidence[:3]) + "."
            if risks:
                summary += " Risk signals: " + "; ".join(str(item) for item in risks[:3]) + "."
            return summary

    def _add_found_side_context(self, db: Session, builder: GraphContextBuilder, item_id: int) -> None:
        for event in (
            db.query(CustodyEvent)
            .options(joinedload(CustodyEvent.staff))
            .filter(CustodyEvent.found_item_id == item_id)
            .order_by(CustodyEvent.timestamp.asc())
            .limit(20)
            .all()
        ):
            builder.add_custody(event)
        for label in db.query(BarcodeLabel).filter(BarcodeLabel.entity_type == "found_item", BarcodeLabel.entity_id == item_id).limit(5).all():
            builder.add_label(label)
        for log in db.query(AuditLog).filter(AuditLog.entity_type == "found_item", AuditLog.entity_id == str(item_id)).order_by(AuditLog.created_at.desc()).limit(10).all():
            builder.add_audit(log)

    def _add_report_side_context(self, db: Session, builder: GraphContextBuilder, report_id: int) -> None:
        for claim in db.query(ClaimVerification).filter(ClaimVerification.lost_report_id == report_id).limit(8).all():
            builder.add_claim(claim)
        for log in db.query(AuditLog).filter(AuditLog.entity_type == "lost_report", AuditLog.entity_id == str(report_id)).order_by(AuditLog.created_at.desc()).limit(10).all():
            builder.add_audit(log)


def _same(left: str | None, right: str | None) -> bool:
    return bool(left and right and left.strip().lower() == right.strip().lower())


def _slug(value: str) -> str:
    return hashlib.sha1(value.strip().lower().encode("utf-8")).hexdigest()[:12]


def _digest(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.rsplit("@", 1)[-1].lower()


def _safe_graph_value(value: Any) -> Any:
    if isinstance(value, str):
        return mask_sensitive_text(value)
    if isinstance(value, list):
        return [_safe_graph_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _safe_graph_value(item) for key, item in value.items()}
    return value


graph_context_service = GraphContextService()
