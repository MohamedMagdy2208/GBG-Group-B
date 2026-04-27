from datetime import UTC, datetime, timedelta
import random

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    AirportLocation,
    AirportLocationType,
    AuditLog,
    AuditSeverity,
    BarcodeLabel,
    ConfidenceLevel,
    ClaimVerification,
    ClaimVerificationStatus,
    CustodyAction,
    CustodyEvent,
    FoundItem,
    FoundItemStatus,
    ItemCategory,
    LostReport,
    LostReportStatus,
    MatchCandidate,
    Notification,
    NotificationChannel,
    NotificationStatus,
    RiskLevel,
    User,
    UserRole,
)
from app.services.matching_engine import matching_engine
from app.services.label_service import label_service


PASSWORD = "Password123!"


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            ensure_feature_seed(db)
            print("Base seed data already exists. Feature seed data checked.")
            return

        admin = User(name="Airport Admin", email="admin@airport-demo.com", phone="+201000000001", role=UserRole.admin, password_hash=hash_password(PASSWORD))
        staff = [
            User(name="Mona Staff", email="mona.staff@airport-demo.com", phone="+201000000010", role=UserRole.staff, password_hash=hash_password(PASSWORD)),
            User(name="Omar Staff", email="omar.staff@airport-demo.com", phone="+201000000011", role=UserRole.staff, password_hash=hash_password(PASSWORD)),
            User(name="Nadine Security", email="nadine.security@airport-demo.com", phone="+201000000012", role=UserRole.security, password_hash=hash_password(PASSWORD)),
        ]
        passengers = [
            User(name=f"Passenger {i}", email=f"passenger{i}@airport-demo.com", phone=f"+20100000010{i}", role=UserRole.passenger, password_hash=hash_password(PASSWORD))
            for i in range(1, 6)
        ]
        db.add_all([admin, *staff, *passengers])

        locations = [
            ("Terminal 1", AirportLocationType.terminal),
            ("Terminal 2", AirportLocationType.terminal),
            ("Terminal 3", AirportLocationType.terminal),
            ("Gate B7", AirportLocationType.gate),
            ("Gate C3", AirportLocationType.gate),
            ("Security Checkpoint A", AirportLocationType.security),
            ("Baggage Claim 2", AirportLocationType.baggage),
            ("Food Court", AirportLocationType.other),
            ("Lounge Area", AirportLocationType.lounge),
            ("Restroom Area", AirportLocationType.restroom),
        ]
        db.add_all([AirportLocation(name=name, type=kind, description=f"{name} airport area") for name, kind in locations])

        category_names = ["Phone", "Laptop", "Bag", "Wallet", "Passport", "ID Card", "Headphones", "Keys", "Watch", "Clothing"]
        db.add_all(
            [
                ItemCategory(name=name, related_categories_json=[name.lower()], description=f"{name} items handled by lost and found.")
                for name in category_names
            ]
        )
        db.commit()

        now = datetime.now(UTC)
        colors = ["black", "blue", "silver", "red", "brown", "white", "gray", "green"]
        found_items: list[FoundItem] = []
        lost_reports: list[LostReport] = []
        for i in range(20):
            category = category_names[i % len(category_names)]
            color = colors[i % len(colors)]
            location = locations[i % len(locations)][0]
            risk = RiskLevel.sensitive if category in {"Passport", "ID Card"} else RiskLevel.high_value if category in {"Phone", "Laptop", "Watch"} else RiskLevel.normal
            item = FoundItem(
                item_title=f"{color.title()} {category}",
                category=category,
                raw_description=f"{color.title()} {category.lower()} found near {location}. Demo serial SN{i:04d}.",
                ai_clean_description=f"{color.title()} {category.lower()} found near {location}.",
                ai_extracted_attributes_json={"item_type": category, "color": color, "unique_identifiers": [f"SN{i:04d}"] if i % 3 == 0 else []},
                vision_tags_json=[{"name": category.lower(), "confidence": 0.86}],
                vision_ocr_text=f"SN{i:04d}" if i % 3 == 0 else "",
                color=color,
                found_location=location,
                found_datetime=now - timedelta(hours=i + 1),
                storage_location=f"Shelf {chr(65 + (i % 5))}-{i + 1}",
                risk_level=risk,
                status=FoundItemStatus.registered,
                created_by_staff_id=staff[i % len(staff)].id,
                embedding_vector_id=f"seed-found-{i}",
                search_document_id=f"found-{i}",
            )
            found_items.append(item)
            db.add(item)

            passenger = passengers[i % len(passengers)]
            report = LostReport(
                passenger_id=passenger.id,
                item_title=f"Lost {color.title()} {category}",
                category=category,
                raw_description=f"I lost a {color} {category.lower()} around {location}. It may have serial SN{i:04d}.",
                ai_clean_description=f"Passenger lost a {color} {category.lower()} around {location}.",
                ai_extracted_attributes_json={"item_type": category, "color": color, "unique_identifiers": [f"SN{i:04d}"] if i % 3 == 0 else []},
                color=color,
                lost_location=location,
                lost_datetime=now - timedelta(hours=i + 3),
                flight_number=f"MS{100 + i}" if i % 4 == 0 else None,
                contact_email=passenger.email,
                contact_phone=passenger.phone,
                status=LostReportStatus.open,
                embedding_vector_id=f"seed-lost-{i}",
                search_document_id=f"lost-{i}",
            )
            lost_reports.append(report)
            db.add(report)
        db.commit()

        for item in found_items:
            db.add(CustodyEvent(found_item_id=item.id, action=CustodyAction.found, staff_id=item.created_by_staff_id, location=item.found_location, notes="Seeded item intake"))
            db.add(CustodyEvent(found_item_id=item.id, action=CustodyAction.stored, staff_id=item.created_by_staff_id, location=item.storage_location, notes="Stored for review"))

        seeded_candidates: list[MatchCandidate] = []
        for i in range(16):
            lost = lost_reports[i]
            found = found_items[i if i < 12 else random.randrange(0, len(found_items))]
            score = matching_engine.score(lost, found, azure_search_score=88 if i < 12 else 62)
            if score["confidence_level"] is None:
                continue
            candidate = MatchCandidate(
                lost_report_id=lost.id,
                found_item_id=found.id,
                match_score=score["match_score"],
                azure_search_score=score["azure_search_score"],
                category_score=score["category_score"],
                text_score=score["text_score"],
                color_score=score["color_score"],
                location_score=score["location_score"],
                time_score=score["time_score"],
                flight_score=score["flight_score"],
                unique_identifier_score=score["unique_identifier_score"],
                confidence_level=score["confidence_level"] or ConfidenceLevel.low,
                ai_match_summary="Seeded candidate. Staff must review evidence before release.",
            )
            db.add(candidate)
            seeded_candidates.append(candidate)
            lost.status = LostReportStatus.matched
            found.status = FoundItemStatus.matched

        db.commit()

        for item in found_items[:10]:
            label = BarcodeLabel(
                label_code=f"LF-SEED-{item.id:04d}",
                entity_type="found_item",
                entity_id=item.id,
                qr_payload=label_service.build_payload(f"LF-SEED-{item.id:04d}"),
                created_by_staff_id=item.created_by_staff_id,
            )
            db.add(label)

        for i, candidate in enumerate(seeded_candidates[:8]):
            risk_blocked = candidate.found_item.risk_level != RiskLevel.normal or candidate.match_score < 70
            claim = ClaimVerification(
                match_candidate_id=candidate.id,
                lost_report_id=candidate.lost_report_id,
                found_item_id=candidate.found_item_id,
                passenger_id=candidate.lost_report.passenger_id,
                status=ClaimVerificationStatus.blocked if risk_blocked else ClaimVerificationStatus.submitted,
                verification_questions_json=[
                    "Describe a unique detail or mark on the item.",
                    "Where and when did you last remember having it?",
                    "Can you provide proof such as a receipt, serial number, photo, or boarding pass?",
                ],
                passenger_answers_json={
                    "unique_detail": f"Demo answer for {candidate.lost_report.item_title}",
                    "last_seen": candidate.lost_report.lost_location,
                },
                fraud_score=75 if risk_blocked else 20 + i,
                fraud_flags_json=["Seeded high-value or sensitive item review"] if risk_blocked else ["Seeded normal claim"],
                release_checklist_json={"identity_checked": False, "proof_checked": False, "passenger_signed": False, "custody_updated": False},
            )
            db.add(claim)

        db.add(
            AuditLog(
                actor_user_id=admin.id,
                actor_role=admin.role.value,
                action="seed.audit.created",
                entity_type="system",
                severity=AuditSeverity.info,
                metadata_json={"note": "Seed audit record for admin dashboard"},
            )
        )

        db.add(
            Notification(
                user_id=passengers[0].id,
                lost_report_id=lost_reports[0].id,
                channel=NotificationChannel.email,
                recipient=passengers[0].email,
                message="Your lost item report has a possible match pending staff review.",
                status=NotificationStatus.sent,
                sent_at=now,
            )
        )
        db.commit()
        print("Seed data created.")
        print("Demo logins:")
        print("  admin@airport-demo.com / Password123!")
        print("  mona.staff@airport-demo.com / Password123!")
        print("  passenger1@airport-demo.com / Password123!")
    finally:
        db.close()


def ensure_feature_seed(db) -> None:
    staff_user = db.query(User).filter(User.role.in_([UserRole.staff, UserRole.admin, UserRole.security])).first()
    if db.query(BarcodeLabel).count() == 0:
        for item in db.query(FoundItem).limit(10).all():
            label_code = f"LF-SEED-{item.id:04d}"
            db.add(
                BarcodeLabel(
                    label_code=label_code,
                    entity_type="found_item",
                    entity_id=item.id,
                    qr_payload=label_service.build_payload(label_code),
                    created_by_staff_id=staff_user.id if staff_user else item.created_by_staff_id,
                )
            )

    if db.query(ClaimVerification).count() == 0:
        for i, candidate in enumerate(db.query(MatchCandidate).limit(8).all()):
            risk_blocked = candidate.found_item.risk_level != RiskLevel.normal or candidate.match_score < 70
            db.add(
                ClaimVerification(
                    match_candidate_id=candidate.id,
                    lost_report_id=candidate.lost_report_id,
                    found_item_id=candidate.found_item_id,
                    passenger_id=candidate.lost_report.passenger_id,
                    status=ClaimVerificationStatus.blocked if risk_blocked else ClaimVerificationStatus.submitted,
                    verification_questions_json=[
                        "Describe a unique detail or mark on the item.",
                        "Where and when did you last remember having it?",
                        "Can you provide proof such as a receipt, serial number, photo, or boarding pass?",
                    ],
                    passenger_answers_json={
                        "unique_detail": f"Demo answer for {candidate.lost_report.item_title}",
                        "last_seen": candidate.lost_report.lost_location,
                    },
                    fraud_score=75 if risk_blocked else 20 + i,
                    fraud_flags_json=["Seeded high-value or sensitive item review"] if risk_blocked else ["Seeded normal claim"],
                    release_checklist_json={"identity_checked": False, "proof_checked": False, "passenger_signed": False, "custody_updated": False},
                )
            )

    if db.query(AuditLog).count() == 0:
        db.add(
            AuditLog(
                actor_user_id=staff_user.id if staff_user else None,
                actor_role=staff_user.role.value if staff_user else None,
                action="seed.audit.created",
                entity_type="system",
                severity=AuditSeverity.info,
                metadata_json={"note": "Seed audit record for admin dashboard"},
            )
        )
    db.commit()


if __name__ == "__main__":
    main()
