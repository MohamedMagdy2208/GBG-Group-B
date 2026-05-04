from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import (
    AirportLocationType,
    AuditSeverity,
    BarcodeLabelStatus,
    ChatRole,
    ClaimVerificationStatus,
    ConfidenceLevel,
    CustodyAction,
    FoundItemStatus,
    LostReportStatus,
    MatchStatus,
    NotificationChannel,
    NotificationStatus,
    RiskLevel,
    UserRole,
    WorkStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8)


class UserRead(ORMModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    is_disabled: bool = False
    mfa_enabled: bool = False
    locked_until: datetime | None = None
    created_at: datetime


class UserAdminCreate(UserCreate):
    role: UserRole = UserRole.staff


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: UserRole | None = None
    is_disabled: bool | None = None
    mfa_enabled: bool | None = None


class NotificationPreferencesUpdate(BaseModel):
    preferred_channel: str | None = None
    preferred_language: str | None = None
    consent: bool | None = None


class NotificationPreferencesRead(BaseModel):
    preferred_channel: str
    preferred_language: str
    notification_consent_at: datetime | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in_seconds: int | None = None
    user: UserRead


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=12)


class MFAVerifyRequest(BaseModel):
    code: str


class LostReportBase(BaseModel):
    item_title: str
    category: str | None = None
    raw_description: str
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    lost_location: str | None = None
    lost_datetime: datetime | None = None
    flight_number: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    proof_blob_url: str | None = None


class LostReportCreate(LostReportBase):
    pass


class LostReportUpdate(BaseModel):
    item_title: str | None = None
    category: str | None = None
    raw_description: str | None = None
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    lost_location: str | None = None
    lost_datetime: datetime | None = None
    flight_number: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    proof_blob_url: str | None = None
    status: LostReportStatus | None = None


class LostReportRead(ORMModel):
    id: int
    report_code: str
    passenger_id: int | None
    item_title: str
    category: str | None
    raw_description: str
    ai_clean_description: str | None
    ai_extracted_attributes_json: dict[str, Any]

    @field_validator("ai_extracted_attributes_json", mode="before")
    @classmethod
    def _strip_private_attrs(cls, value: Any) -> Any:
        return {key: item for key, item in (value or {}).items() if not str(key).startswith("_")}

    @field_validator("proof_blob_url", mode="after")
    @classmethod
    def _sign_proof_url(cls, value: Any) -> Any:
        return _sign_blob_url(value)
    brand: str | None
    model: str | None
    color: str | None
    lost_location: str | None
    lost_datetime: datetime | None
    flight_number: str | None
    contact_email: EmailStr | None
    contact_phone: str | None
    proof_blob_url: str | None
    embedding_vector_id: str | None
    search_document_id: str | None
    status: LostReportStatus
    created_at: datetime
    updated_at: datetime


class FoundItemBase(BaseModel):
    item_title: str
    category: str | None = None
    raw_description: str
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    found_location: str | None = None
    found_datetime: datetime | None = None
    storage_location: str | None = None
    risk_level: RiskLevel = RiskLevel.normal
    image_blob_url: str | None = None


class FoundItemCreate(FoundItemBase):
    pass


class FoundItemUpdate(BaseModel):
    item_title: str | None = None
    category: str | None = None
    raw_description: str | None = None
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    found_location: str | None = None
    found_datetime: datetime | None = None
    storage_location: str | None = None
    risk_level: RiskLevel | None = None
    image_blob_url: str | None = None
    status: FoundItemStatus | None = None


def _strip_private_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_private_keys(item) for key, item in value.items() if not str(key).startswith("_")}
    if isinstance(value, list):
        return [_strip_private_keys(item) for item in value]
    return value


def _sign_blob_url(value: Any) -> Any:
    """Convert a private Azure blob URL into a short-lived SAS URL the browser can fetch."""
    if not value:
        return value
    try:
        from app.services.azure_blob_service import azure_blob_service

        return azure_blob_service.secure_url_from_blob_url_sync(str(value))
    except Exception:
        return value


class FoundItemRead(ORMModel):
    id: int
    item_title: str
    category: str | None
    raw_description: str
    ai_clean_description: str | None
    ai_extracted_attributes_json: dict[str, Any]
    vision_tags_json: list[Any]
    vision_ocr_text: str | None

    @field_validator("ai_extracted_attributes_json", mode="before")
    @classmethod
    def _strip_private_attrs(cls, value: Any) -> Any:
        return _strip_private_keys(value)

    @field_validator("image_blob_url", mode="after")
    @classmethod
    def _sign_image_url(cls, value: Any) -> Any:
        return _sign_blob_url(value)
    brand: str | None
    model: str | None
    color: str | None
    found_location: str | None
    found_datetime: datetime | None
    storage_location: str | None
    risk_level: RiskLevel
    image_blob_url: str | None
    embedding_vector_id: str | None
    search_document_id: str | None
    status: FoundItemStatus
    created_by_staff_id: int | None
    created_at: datetime
    updated_at: datetime


class MatchCandidateRead(ORMModel):
    id: int
    lost_report_id: int
    found_item_id: int
    match_score: float
    azure_search_score: float
    category_score: float
    text_score: float
    color_score: float
    location_score: float
    time_score: float
    flight_score: float
    unique_identifier_score: float
    confidence_level: ConfidenceLevel
    ai_match_summary: str | None
    evidence_spans_json: dict[str, Any] = Field(default_factory=dict)
    status: MatchStatus
    review_notes: str | None
    reviewed_by_staff_id: int | None
    created_at: datetime
    updated_at: datetime
    lost_report: LostReportRead | None = None
    found_item: FoundItemRead | None = None


class MatchActionRequest(BaseModel):
    review_notes: str | None = None


class ClaimVerificationCreate(BaseModel):
    verification_questions_json: list[str] | None = None


class ClaimEvidenceSubmit(BaseModel):
    contact: str
    passenger_answers_json: dict[str, Any] = Field(default_factory=dict)
    proof_blob_urls_json: list[str] = Field(default_factory=list)


class ClaimReviewRequest(BaseModel):
    review_notes: str | None = None
    release_checklist_json: dict[str, Any] = Field(default_factory=dict)


class ClaimReleaseRequest(BaseModel):
    released_to_name: str
    released_to_contact: str | None = None
    release_checklist_json: dict[str, Any] = Field(default_factory=dict)
    review_notes: str | None = None


class ClaimVerificationRead(ORMModel):
    id: int
    match_candidate_id: int
    lost_report_id: int
    found_item_id: int
    passenger_id: int | None
    status: ClaimVerificationStatus
    verification_questions_json: list[Any]
    passenger_answers_json: dict[str, Any]
    proof_blob_urls_json: list[Any]
    staff_review_notes: str | None
    fraud_score: float
    fraud_flags_json: list[Any]
    release_checklist_json: dict[str, Any]
    released_to_name: str | None
    released_to_contact_masked: str | None
    approved_by_staff_id: int | None
    released_by_staff_id: int | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    released_at: datetime | None
    created_at: datetime
    updated_at: datetime
    match_candidate: MatchCandidateRead | None = None


class FraudScoreResponse(BaseModel):
    match_candidate_id: int
    fraud_score: float
    fraud_flags: list[str]
    risk_level: RiskLevel
    release_blocked: bool


class CustodyEventCreate(BaseModel):
    action: CustodyAction
    location: str | None = None
    notes: str | None = None


class CustodyEventRead(ORMModel):
    id: int
    found_item_id: int
    action: CustodyAction
    staff_id: int | None
    location: str | None
    notes: str | None
    timestamp: datetime


class AirportLocationCreate(BaseModel):
    name: str
    type: AirportLocationType = AirportLocationType.other
    parent_location: str | None = None
    description: str | None = None


class AirportLocationRead(ORMModel):
    id: int
    name: str
    type: AirportLocationType
    parent_location: str | None
    description: str | None


class ItemCategoryCreate(BaseModel):
    name: str
    related_categories_json: list[str] = Field(default_factory=list)
    description: str | None = None


class ItemCategoryRead(ORMModel):
    id: int
    name: str
    related_categories_json: list[Any]
    description: str | None


class NotificationSendRequest(BaseModel):
    user_id: int | None = None
    lost_report_id: int | None = None
    match_candidate_id: int | None = None
    channel: NotificationChannel
    recipient: str
    message: str


class NotificationRead(ORMModel):
    id: int
    user_id: int | None
    lost_report_id: int | None
    match_candidate_id: int | None
    channel: NotificationChannel
    recipient: str
    message: str
    status: NotificationStatus
    created_at: datetime
    sent_at: datetime | None


class FileUploadResponse(BaseModel):
    file_id: str
    url: str
    content_type: str
    size_bytes: int
    retention_expires_at: datetime | None = None
    malware_scan_status: str | None = None


class AITextRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    vector_id: str
    embedding: list[float]


class ImageAnalysisRequest(BaseModel):
    image_url: str


class ImageAnalysisResponse(BaseModel):
    caption: str
    tags: list[dict[str, Any]]
    ocr_text: str
    objects: list[dict[str, Any]]


class DescribeFromImageRequest(BaseModel):
    image_url: str


class DescribeFromImageResponse(BaseModel):
    item_title: str
    category: str | None = None
    raw_description: str
    brand: str | None = None
    color: str | None = None
    suggested_risk_level: RiskLevel = RiskLevel.normal
    confidence: float = 0.0
    vision_caption: str | None = None
    vision_tags: list[dict[str, Any]] = Field(default_factory=list)
    vision_ocr_text: str | None = None
    source: str = "ai"


class ChatSessionRead(ORMModel):
    id: int
    session_code: str
    lost_report_id: int | None
    verification_status: str
    current_state: str
    language: str
    voice_enabled: bool
    collected_data_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ChatSessionCreate(BaseModel):
    language: str = "en"
    voice_enabled: bool = False


class ChatMessageCreate(BaseModel):
    message_text: str
    language: str | None = None


class ChatMessageRead(ORMModel):
    id: int
    session_id: int
    role: ChatRole
    message_text: str
    structured_payload_json: dict[str, Any]
    created_at: datetime


class ChatResponse(BaseModel):
    session: ChatSessionRead
    assistant_message: ChatMessageRead
    suggested_actions: list[str] = Field(default_factory=list)


class ChatVerifyReportRequest(BaseModel):
    report_code: str
    contact: str
    language: str | None = None


class ChatSubmitLostReportRequest(BaseModel):
    data: dict[str, Any] | None = None


class ChatVoiceMessageRequest(BaseModel):
    transcript: str
    language: str = "en"
    confidence: float | None = None
    provider: str = "browser"


class AnalyticsSummary(BaseModel):
    open_lost_reports: int
    registered_found_items: int
    pending_matches: int
    high_confidence_matches: int
    released_items: int
    average_match_score: float


class BarcodeLabelRead(ORMModel):
    id: int
    label_code: str
    entity_type: str
    entity_id: int
    qr_payload: str
    status: BarcodeLabelStatus
    created_by_staff_id: int | None
    scan_count: int
    last_scanned_at: datetime | None
    created_at: datetime


class LabelScanRequest(BaseModel):
    label_code: str
    location: str | None = None
    notes: str | None = None


class LabelScanResponse(BaseModel):
    label: BarcodeLabelRead
    found_item: FoundItemRead | None = None
    custody_event: CustodyEventRead | None = None


class AuditLogRead(ORMModel):
    id: int
    actor_user_id: int | None
    actor_role: str | None
    action: str
    entity_type: str
    entity_id: str | None
    severity: AuditSeverity
    ip_address: str | None
    user_agent: str | None
    before_json: dict[str, Any]
    after_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime


class VoiceTokenResponse(BaseModel):
    provider: str
    enabled: bool
    token: str | None = None
    region: str | None = None
    endpoint: str | None = None
    expires_in_seconds: int | None = None
    voice_en: str | None = None
    voice_ar: str | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphContextResponse(BaseModel):
    scope: str
    entity_type: str
    entity_id: int
    retrieval_query: str
    provider: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    evidence: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    generated_summary: str
    provenance: dict[str, Any] = Field(default_factory=dict)


class GraphExplainRequest(BaseModel):
    question: str | None = None


class OutboxEventRead(ORMModel):
    id: int
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload_json: dict[str, Any]
    status: WorkStatus
    attempts: int
    max_attempts: int
    next_attempt_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class BackgroundJobRead(ORMModel):
    id: int
    job_type: str
    payload_json: dict[str, Any]
    status: WorkStatus
    attempts: int
    max_attempts: int
    next_run_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class DeepHealthResponse(BaseModel):
    status: str
    checks: dict[str, dict[str, Any]]


class DataRetentionRunResponse(BaseModel):
    status: str
    dry_run: bool
    scanned_tables: list[str]
    affected_records: int
