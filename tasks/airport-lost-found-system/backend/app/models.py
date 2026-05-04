from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class UserRole(StrEnum):
    passenger = "passenger"
    staff = "staff"
    admin = "admin"
    security = "security"


class LostReportStatus(StrEnum):
    open = "open"
    matched = "matched"
    rejected = "rejected"
    resolved = "resolved"


class FoundItemStatus(StrEnum):
    registered = "registered"
    matched = "matched"
    claimed = "claimed"
    released = "released"
    disposed = "disposed"


class RiskLevel(StrEnum):
    normal = "normal"
    high_value = "high_value"
    sensitive = "sensitive"
    dangerous = "dangerous"


class MatchStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    needs_more_info = "needs_more_info"


class ConfidenceLevel(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class CustodyAction(StrEnum):
    found = "found"
    stored = "stored"
    moved = "moved"
    matched = "matched"
    claimed = "claimed"
    released = "released"
    disposed = "disposed"
    note = "note"


class AirportLocationType(StrEnum):
    terminal = "terminal"
    gate = "gate"
    lounge = "lounge"
    security = "security"
    restroom = "restroom"
    baggage = "baggage"
    aircraft = "aircraft"
    other = "other"


class NotificationChannel(StrEnum):
    email = "email"
    sms = "sms"


class NotificationStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class ChatRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ClaimVerificationStatus(StrEnum):
    pending = "pending"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"
    released = "released"
    blocked = "blocked"


class BarcodeLabelStatus(StrEnum):
    active = "active"
    revoked = "revoked"


class AuditSeverity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


class WorkStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    dead_letter = "dead_letter"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), default=UserRole.passenger)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preferred_channel: Mapped[str] = mapped_column(String(16), default="email")
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    notification_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lost_reports: Mapped[list["LostReport"]] = relationship(back_populates="passenger")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_revoked", "user_id", "revoked_at"),
        Index("ix_refresh_tokens_token_hash", "token_hash", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_hash", "token_hash", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (Index("ix_idempotency_scope_key", "scope", "key", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(120))
    key: Mapped[str] = mapped_column(String(160))
    request_hash: Mapped[str] = mapped_column(String(128))
    response_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("ix_outbox_events_status_next", "status", "next_attempt_at"),
        Index("ix_outbox_events_aggregate", "aggregate_type", "aggregate_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120))
    aggregate_type: Mapped[str] = mapped_column(String(80))
    aggregate_id: Mapped[str] = mapped_column(String(80))
    payload_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    status: Mapped[WorkStatus] = mapped_column(Enum(WorkStatus, native_enum=False), default=WorkStatus.pending)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    __table_args__ = (Index("ix_background_jobs_status_next", "status", "next_run_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(120))
    payload_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    status: Mapped[WorkStatus] = mapped_column(Enum(WorkStatus, native_enum=False), default=WorkStatus.pending)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LostReport(Base):
    __tablename__ = "lost_reports"
    __table_args__ = (
        Index("ix_lost_reports_status_category", "status", "category"),
        Index("ix_lost_reports_lost_datetime", "lost_datetime"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    report_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: f"LR-{uuid4().hex[:8].upper()}")
    passenger_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    item_title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    raw_description: Mapped[str] = mapped_column(Text)
    ai_clean_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_extracted_attributes_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lost_location: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    lost_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proof_blob_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding_vector_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    search_document_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    proof_phash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    image_vector_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[LostReportStatus] = mapped_column(Enum(LostReportStatus, native_enum=False), default=LostReportStatus.open)
    created_from_ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    passenger: Mapped[User | None] = relationship(back_populates="lost_reports")
    match_candidates: Mapped[list["MatchCandidate"]] = relationship(back_populates="lost_report", cascade="all, delete-orphan")


class FoundItem(Base):
    __tablename__ = "found_items"
    __table_args__ = (
        Index("ix_found_items_status_category", "status", "category"),
        Index("ix_found_items_found_datetime", "found_datetime"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    raw_description: Mapped[str] = mapped_column(Text)
    ai_clean_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_extracted_attributes_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    vision_tags_json: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    vision_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(80), nullable=True)
    found_location: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    found_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    storage_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel, native_enum=False), default=RiskLevel.normal)
    image_blob_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding_vector_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    search_document_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    image_phash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    image_vector_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[FoundItemStatus] = mapped_column(Enum(FoundItemStatus, native_enum=False), default=FoundItemStatus.registered)
    created_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator: Mapped[User | None] = relationship()
    match_candidates: Mapped[list["MatchCandidate"]] = relationship(back_populates="found_item", cascade="all, delete-orphan")
    custody_events: Mapped[list["CustodyEvent"]] = relationship(back_populates="found_item", cascade="all, delete-orphan")


class MatchCandidate(Base):
    __tablename__ = "match_candidates"
    __table_args__ = (
        Index("ix_match_candidates_status_score", "status", "match_score"),
        Index("uq_match_pair", "lost_report_id", "found_item_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lost_report_id: Mapped[int] = mapped_column(ForeignKey("lost_reports.id"))
    found_item_id: Mapped[int] = mapped_column(ForeignKey("found_items.id"))
    match_score: Mapped[float] = mapped_column(Float)
    azure_search_score: Mapped[float] = mapped_column(Float, default=0)
    category_score: Mapped[float] = mapped_column(Float, default=0)
    text_score: Mapped[float] = mapped_column(Float, default=0)
    color_score: Mapped[float] = mapped_column(Float, default=0)
    location_score: Mapped[float] = mapped_column(Float, default=0)
    time_score: Mapped[float] = mapped_column(Float, default=0)
    flight_score: Mapped[float] = mapped_column(Float, default=0)
    unique_identifier_score: Mapped[float] = mapped_column(Float, default=0)
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(Enum(ConfidenceLevel, native_enum=False))
    ai_match_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_spans_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus, native_enum=False), default=MatchStatus.pending)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lost_report: Mapped[LostReport] = relationship(back_populates="match_candidates")
    found_item: Mapped[FoundItem] = relationship(back_populates="match_candidates")
    reviewer: Mapped[User | None] = relationship()
    claim_verifications: Mapped[list["ClaimVerification"]] = relationship(back_populates="match_candidate", cascade="all, delete-orphan")


class ClaimVerification(Base):
    __tablename__ = "claim_verifications"
    __table_args__ = (
        Index("ix_claim_verifications_status_score", "status", "fraud_score"),
        Index("ix_claim_verifications_match", "match_candidate_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_candidate_id: Mapped[int] = mapped_column(ForeignKey("match_candidates.id"), unique=True)
    lost_report_id: Mapped[int] = mapped_column(ForeignKey("lost_reports.id"))
    found_item_id: Mapped[int] = mapped_column(ForeignKey("found_items.id"))
    passenger_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[ClaimVerificationStatus] = mapped_column(
        Enum(ClaimVerificationStatus, native_enum=False),
        default=ClaimVerificationStatus.pending,
    )
    verification_questions_json: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    passenger_answers_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    proof_blob_urls_json: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    staff_review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    fraud_score: Mapped[float] = mapped_column(Float, default=0)
    fraud_flags_json: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    release_checklist_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    released_to_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    released_to_contact_masked: Mapped[str | None] = mapped_column(String(80), nullable=True)
    approved_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    released_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    match_candidate: Mapped[MatchCandidate] = relationship(back_populates="claim_verifications")
    lost_report: Mapped[LostReport] = relationship()
    found_item: Mapped[FoundItem] = relationship()
    passenger: Mapped[User | None] = relationship(foreign_keys=[passenger_id])
    approver: Mapped[User | None] = relationship(foreign_keys=[approved_by_staff_id])
    releaser: Mapped[User | None] = relationship(foreign_keys=[released_by_staff_id])


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    found_item_id: Mapped[int] = mapped_column(ForeignKey("found_items.id"))
    action: Mapped[CustodyAction] = mapped_column(Enum(CustodyAction, native_enum=False))
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    found_item: Mapped[FoundItem] = relationship(back_populates="custody_events")
    staff: Mapped[User | None] = relationship()


class BarcodeLabel(Base):
    __tablename__ = "barcode_labels"
    __table_args__ = (
        Index("ix_barcode_labels_entity", "entity_type", "entity_id"),
        Index("ix_barcode_labels_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    label_code: Mapped[str] = mapped_column(String(48), unique=True, index=True, default=lambda: f"LF-{uuid4().hex[:10].upper()}")
    entity_type: Mapped[str] = mapped_column(String(40), default="found_item")
    entity_id: Mapped[int] = mapped_column(Integer)
    qr_payload: Mapped[str] = mapped_column(Text)
    status: Mapped[BarcodeLabelStatus] = mapped_column(Enum(BarcodeLabelStatus, native_enum=False), default=BarcodeLabelStatus.active)
    created_by_staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scan_count: Mapped[int] = mapped_column(Integer, default=0)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator: Mapped[User | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    severity: Mapped[AuditSeverity] = mapped_column(Enum(AuditSeverity, native_enum=False), default=AuditSeverity.info)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    before_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    after_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    metadata_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    actor: Mapped[User | None] = relationship()


class AirportLocation(Base):
    __tablename__ = "airport_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    type: Mapped[AirportLocationType] = mapped_column(Enum(AirportLocationType, native_enum=False), default=AirportLocationType.other)
    parent_location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ItemCategory(Base):
    __tablename__ = "item_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    related_categories_json: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    lost_report_id: Mapped[int | None] = mapped_column(ForeignKey("lost_reports.id"), nullable=True)
    match_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("match_candidates.id"), nullable=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel, native_enum=False))
    recipient: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus, native_enum=False), default=NotificationStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship()
    lost_report: Mapped[LostReport | None] = relationship()
    match_candidate: Mapped[MatchCandidate | None] = relationship()


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: f"CHAT-{uuid4().hex[:10].upper()}")
    passenger_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    lost_report_id: Mapped[int | None] = mapped_column(ForeignKey("lost_reports.id"), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(40), default="unverified")
    current_state: Mapped[str] = mapped_column(String(80), default="greeting")
    language: Mapped[str] = mapped_column(String(12), default="en")
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    collected_data_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    passenger: Mapped[User | None] = relationship()
    lost_report: Mapped[LostReport | None] = relationship()
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"))
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole, native_enum=False))
    message_text: Mapped[str] = mapped_column(Text)
    structured_payload_json: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="messages")
