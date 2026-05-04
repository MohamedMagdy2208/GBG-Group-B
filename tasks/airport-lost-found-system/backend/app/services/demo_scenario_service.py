"""One-click end-to-end demo scenarios.

Each scenario seeds a passenger + lost report + found item, runs matching,
opens a claim, approves it and releases — emitting timeline events the
frontend can poll.

Demo data is tagged with `metadata_json["demo_run_id"]` so the cleanup
endpoint can roll back without affecting real records.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.api.utils import (
    add_custody_event,
    enrich_found_item,
    enrich_lost_report,
    invalidate_operational_caches,
    run_matching_for_lost_report,
)
from app.core.security import hash_password, mask_phone
from app.models import (
    AuditLog,
    AuditSeverity,
    BarcodeLabel,
    ChatMessage,
    ChatSession,
    ClaimVerification,
    ClaimVerificationStatus,
    CustodyAction,
    CustodyEvent,
    FoundItem,
    FoundItemStatus,
    LostReport,
    LostReportStatus,
    MatchCandidate,
    MatchStatus,
    Notification,
    RiskLevel,
    User,
    UserRole,
)
from app.services.audit_service import log_audit_event
from app.services.fraud_risk_service import fraud_risk_service


SCENARIOS: dict[str, dict[str, Any]] = {
    "lost_iphone_in_terminal_2": {
        "title": "Lost iPhone at Terminal 2",
        "summary": "Passenger reports a black iPhone 14 lost near gate B12. Staff registers a matching found item. Match flows to release.",
        "passenger": {
            "name": "Demo Passenger",
            "email_prefix": "demo.passenger",
            "phone": "+201111000001",
        },
        "lost_report": {
            "item_title": "Black iPhone 14",
            "category": "Phone",
            "color": "black",
            "raw_description": "Black iPhone 14 with a clear case. Last seen at gate B12 in Terminal 2 around 10am. Phone has a small crack on the top right.",
            "lost_location": "Terminal 2 Gate B12",
            "flight_number": "MS123",
            "lost_offset_minutes": -90,
        },
        "found_item": {
            "item_title": "Black smartphone with cracked screen",
            "category": "Phone",
            "color": "black",
            "raw_description": "Black smartphone with a clear case and a small crack in the top corner. Found near gate B12 by cleaning crew.",
            "found_location": "Terminal 2 Gate B12",
            "storage_location": "Lost & Found Office T2",
            "risk_level": RiskLevel.high_value,
            "found_offset_minutes": -45,
        },
    },
    "passport_at_security_checkpoint_a": {
        "title": "Passport at Security Checkpoint A",
        "summary": "Passenger reports a missing passport. Security finds one matching at checkpoint A. Manual verification required.",
        "passenger": {
            "name": "Demo Traveller",
            "email_prefix": "demo.traveller",
            "phone": "+201111000002",
        },
        "lost_report": {
            "item_title": "Egyptian passport",
            "category": "Passport",
            "color": "red",
            "raw_description": "Egyptian passport, red cover. Last had it at the security checkpoint A while removing belt.",
            "lost_location": "Security Checkpoint A",
            "flight_number": "MS456",
            "lost_offset_minutes": -120,
        },
        "found_item": {
            "item_title": "Red passport (Egypt)",
            "category": "Passport",
            "color": "red",
            "raw_description": "Egyptian passport found in tray at Security Checkpoint A. Owner not present.",
            "found_location": "Security Checkpoint A",
            "storage_location": "Security Office",
            "risk_level": RiskLevel.sensitive,
            "found_offset_minutes": -60,
        },
    },
    "gold_watch_high_value_release": {
        "title": "Gold watch high-value release",
        "summary": "Passenger reports a gold watch lost in the lounge. Found item registered with high-value tag. Demo highlights fraud-risk path.",
        "passenger": {
            "name": "Demo VIP",
            "email_prefix": "demo.vip",
            "phone": "+201111000003",
        },
        "lost_report": {
            "item_title": "Gold watch",
            "category": "Watch",
            "color": "gold",
            "raw_description": "Gold dress watch, leather strap. Left on table at the business lounge after coffee.",
            "lost_location": "Business Lounge T3",
            "flight_number": "MS789",
            "lost_offset_minutes": -180,
        },
        "found_item": {
            "item_title": "Gold wristwatch",
            "category": "Watch",
            "color": "gold",
            "raw_description": "Gold wristwatch with leather strap. Found on table by lounge staff.",
            "found_location": "Business Lounge T3",
            "storage_location": "Lost & Found Office T3",
            "risk_level": RiskLevel.high_value,
            "found_offset_minutes": -90,
        },
    },
}


@dataclass
class DemoEvent:
    step: int
    label: str
    payload: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class DemoRun:
    run_id: str
    scenario: str
    status: str = "running"
    events: list[DemoEvent] = field(default_factory=list)
    created_records: dict[str, list[int]] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str | None = None
    error: str | None = None

    def add(self, label: str, **payload: Any) -> None:
        self.events.append(DemoEvent(step=len(self.events) + 1, label=label, payload=payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario": self.scenario,
            "status": self.status,
            "events": [event.__dict__ for event in self.events],
            "created_records": self.created_records,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


class DemoScenarioService:
    def __init__(self) -> None:
        self._runs: dict[str, DemoRun] = {}
        self._lock = asyncio.Lock()

    def list_scenarios(self) -> list[dict[str, str]]:
        return [{"key": key, "title": scenario["title"], "summary": scenario["summary"]} for key, scenario in SCENARIOS.items()]

    def get_run(self, run_id: str) -> DemoRun | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        return [run.to_dict() for run in self._runs.values()]

    async def start(self, db: Session, scenario_key: str, actor: User) -> DemoRun:
        scenario = SCENARIOS.get(scenario_key)
        if not scenario:
            raise ValueError("unknown_scenario")
        async with self._lock:
            run_id = uuid4().hex[:10]
            run = DemoRun(run_id=run_id, scenario=scenario_key)
            self._runs[run_id] = run
        try:
            await self._execute(db, run, scenario, actor)
            run.status = "succeeded"
        except Exception as exc:  # pragma: no cover - exercised via integration
            run.status = "failed"
            run.error = str(exc)[:500]
            db.rollback()
            raise
        finally:
            run.finished_at = datetime.now(UTC).isoformat()
        return run

    def cleanup(self, db: Session, run_id: str) -> dict[str, Any]:
        run = self._runs.get(run_id)
        if not run:
            raise ValueError("run_not_found")
        deleted = self._delete_records(db, run)
        run.status = "cleaned"
        run.add("Cleanup complete", deleted=deleted)
        db.commit()
        return {"status": "ok", "run_id": run_id, "deleted": deleted}

    async def _execute(self, db: Session, run: DemoRun, scenario: dict[str, Any], actor: User) -> None:
        now = datetime.now(UTC)
        run.add("Scenario started", scenario=scenario["title"])

        passenger_cfg = scenario["passenger"]
        email = f"{passenger_cfg['email_prefix']}.{run.run_id}@demo.local"
        passenger = User(
            name=f"{passenger_cfg['name']} ({run.run_id})",
            email=email,
            phone=passenger_cfg["phone"],
            password_hash=hash_password("DemoPassenger1!"),
            role=UserRole.passenger,
        )
        db.add(passenger)
        db.flush()
        run.created_records.setdefault("users", []).append(passenger.id)
        run.add("Passenger created", user_id=passenger.id, email=email)

        report_cfg = scenario["lost_report"]
        report = LostReport(
            item_title=report_cfg["item_title"],
            category=report_cfg["category"],
            raw_description=report_cfg["raw_description"],
            color=report_cfg["color"],
            lost_location=report_cfg["lost_location"],
            lost_datetime=now + timedelta(minutes=report_cfg["lost_offset_minutes"]),
            flight_number=report_cfg["flight_number"],
            contact_email=email,
            contact_phone=passenger.phone,
            passenger_id=passenger.id,
        )
        db.add(report)
        await enrich_lost_report(db, report)
        db.flush()
        run.created_records.setdefault("lost_reports", []).append(report.id)
        run.add("Lost report submitted", lost_report_id=report.id, report_code=report.report_code)

        item_cfg = scenario["found_item"]
        item = FoundItem(
            item_title=item_cfg["item_title"],
            category=item_cfg["category"],
            raw_description=item_cfg["raw_description"],
            color=item_cfg["color"],
            found_location=item_cfg["found_location"],
            found_datetime=now + timedelta(minutes=item_cfg["found_offset_minutes"]),
            storage_location=item_cfg["storage_location"],
            risk_level=item_cfg["risk_level"],
            created_by_staff_id=actor.id,
        )
        db.add(item)
        await enrich_found_item(db, item)
        db.flush()
        run.created_records.setdefault("found_items", []).append(item.id)
        add_custody_event(db, item, CustodyAction.found, actor.id, item.found_location, "Demo registration")
        run.add("Found item registered", found_item_id=item.id, risk_level=item.risk_level.value)

        candidates = await run_matching_for_lost_report(db, report)
        run.created_records.setdefault("match_candidates", []).extend([candidate.id for candidate in candidates])
        if not candidates:
            run.add("No match candidates produced", lost_report_id=report.id)
            return
        candidate = max(candidates, key=lambda c: c.match_score)
        run.add(
            "Match candidate scored",
            match_candidate_id=candidate.id,
            match_score=candidate.match_score,
            confidence=candidate.confidence_level.value,
        )

        candidate.status = MatchStatus.approved
        candidate.reviewed_by_staff_id = actor.id
        candidate.review_notes = "Approved by demo simulator"
        item.status = FoundItemStatus.claimed
        add_custody_event(db, item, CustodyAction.claimed, actor.id, item.storage_location, "Demo match approved")
        log_audit_event(
            db,
            action="demo.match_approved",
            entity_type="match_candidate",
            entity_id=candidate.id,
            actor=actor,
            severity=AuditSeverity.info,
            metadata={"demo_run_id": run.run_id},
        )
        db.flush()
        run.add("Match approved by staff", match_candidate_id=candidate.id)

        risk = fraud_risk_service.score_match(db, candidate, contact=email, answers={"q1": "yes", "q2": "yes"})
        claim = ClaimVerification(
            match_candidate_id=candidate.id,
            lost_report_id=report.id,
            found_item_id=item.id,
            passenger_id=passenger.id,
            verification_questions_json=[
                "Describe a unique mark on the item.",
                "When did you last have it?",
                "Can you provide proof of ownership?",
            ],
            passenger_answers_json={
                "q1": "Small crack on the top corner, clear case",
                "q2": "Around 10am at gate B12",
                "q3": "I have the original purchase receipt",
            },
            fraud_score=risk["fraud_score"],
            fraud_flags_json=risk["fraud_flags"],
            status=ClaimVerificationStatus.blocked if risk["release_blocked"] else ClaimVerificationStatus.submitted,
            submitted_at=datetime.now(UTC),
        )
        db.add(claim)
        db.flush()
        run.created_records.setdefault("claim_verifications", []).append(claim.id)
        run.add("Claim verification opened", claim_verification_id=claim.id, fraud_score=claim.fraud_score, status=claim.status.value)

        if claim.status == ClaimVerificationStatus.blocked:
            run.add("Claim blocked by fraud rules — demo stops here for staff review", flags=claim.fraud_flags_json)
            db.commit()
            return

        claim.status = ClaimVerificationStatus.approved
        claim.staff_review_notes = "Approved by demo simulator"
        claim.release_checklist_json = {
            "identity_checked": True,
            "proof_checked": True,
            "passenger_signed": True,
            "custody_updated": True,
        }
        claim.approved_by_staff_id = actor.id
        claim.reviewed_at = datetime.now(UTC)
        db.flush()
        run.add("Claim approved", claim_verification_id=claim.id)

        claim.status = ClaimVerificationStatus.released
        claim.released_to_name = passenger.name
        claim.released_to_contact_masked = mask_phone(passenger.phone)
        claim.released_by_staff_id = actor.id
        claim.released_at = datetime.now(UTC)
        item.status = FoundItemStatus.released
        report.status = LostReportStatus.resolved
        add_custody_event(db, item, CustodyAction.released, actor.id, item.storage_location, f"Demo release — claim {claim.id}")
        log_audit_event(
            db,
            action="demo.item_released",
            entity_type="found_item",
            entity_id=item.id,
            actor=actor,
            severity=AuditSeverity.info,
            metadata={"demo_run_id": run.run_id, "claim_verification_id": claim.id},
        )
        db.commit()
        run.add("Item released to passenger", found_item_id=item.id, lost_report_id=report.id)
        await invalidate_operational_caches()

    def _delete_records(self, db: Session, run: DemoRun) -> dict[str, int]:
        deleted: dict[str, int] = {}
        for table_name, model in [
            ("custody_events", CustodyEvent),
            ("notifications", Notification),
            ("audit_logs", AuditLog),
            ("barcode_labels", BarcodeLabel),
            ("chat_messages", ChatMessage),
            ("chat_sessions", ChatSession),
        ]:
            ids = run.created_records.get(table_name, [])
            if ids:
                count = db.query(model).filter(model.id.in_(ids)).delete(synchronize_session=False)
                deleted[table_name] = int(count)
        for found_item_id in run.created_records.get("found_items", []):
            count = db.query(CustodyEvent).filter(CustodyEvent.found_item_id == found_item_id).delete(synchronize_session=False)
            deleted["custody_events"] = deleted.get("custody_events", 0) + int(count)
            db.query(BarcodeLabel).filter(BarcodeLabel.entity_type == "found_item", BarcodeLabel.entity_id == found_item_id).delete(synchronize_session=False)
        for claim_id in run.created_records.get("claim_verifications", []):
            db.query(ClaimVerification).filter(ClaimVerification.id == claim_id).delete(synchronize_session=False)
        deleted["claim_verifications"] = len(run.created_records.get("claim_verifications", []))
        for candidate_id in run.created_records.get("match_candidates", []):
            db.query(MatchCandidate).filter(MatchCandidate.id == candidate_id).delete(synchronize_session=False)
        deleted["match_candidates"] = len(run.created_records.get("match_candidates", []))
        for found_item_id in run.created_records.get("found_items", []):
            db.query(FoundItem).filter(FoundItem.id == found_item_id).delete(synchronize_session=False)
        deleted["found_items"] = len(run.created_records.get("found_items", []))
        for report_id in run.created_records.get("lost_reports", []):
            db.query(LostReport).filter(LostReport.id == report_id).delete(synchronize_session=False)
        deleted["lost_reports"] = len(run.created_records.get("lost_reports", []))
        for user_id in run.created_records.get("users", []):
            db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        deleted["users"] = len(run.created_records.get("users", []))
        return deleted


demo_scenario_service = DemoScenarioService()
