export type Role = "passenger" | "staff" | "admin" | "security";

export type User = {
  id: number;
  name: string;
  email: string;
  phone?: string | null;
  role: Role;
  is_disabled?: boolean;
  mfa_enabled?: boolean;
  locked_until?: string | null;
  created_at: string;
};

export type LostReport = {
  id: number;
  report_code: string;
  passenger_id?: number | null;
  item_title: string;
  category?: string | null;
  raw_description: string;
  ai_clean_description?: string | null;
  brand?: string | null;
  model?: string | null;
  color?: string | null;
  lost_location?: string | null;
  lost_datetime?: string | null;
  flight_number?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  proof_blob_url?: string | null;
  status: "open" | "matched" | "rejected" | "resolved";
  created_at: string;
  updated_at: string;
};

export type FoundItem = {
  id: number;
  item_title: string;
  category?: string | null;
  raw_description: string;
  ai_clean_description?: string | null;
  vision_tags_json: Array<Record<string, unknown>>;
  vision_ocr_text?: string | null;
  brand?: string | null;
  model?: string | null;
  color?: string | null;
  found_location?: string | null;
  found_datetime?: string | null;
  storage_location?: string | null;
  risk_level: "normal" | "high_value" | "sensitive" | "dangerous";
  image_blob_url?: string | null;
  status: "registered" | "matched" | "claimed" | "released" | "disposed";
  created_at: string;
  updated_at: string;
};

export type EvidenceSpan = { text: string; start: number; end: number };

export type EvidenceFacet = "category" | "color" | "location" | "flight" | "identifier" | "text";

export type EvidenceSpans = {
  lost?: Partial<Record<EvidenceFacet, EvidenceSpan[]>>;
  found?: Partial<Record<EvidenceFacet, EvidenceSpan[]>>;
  shared_terms?: string[];
  category_match?: boolean;
  color_match?: boolean;
  location_match?: boolean;
  flight_match?: boolean;
  identifier_overlap?: string[];
};

export type MatchCandidate = {
  id: number;
  lost_report_id: number;
  found_item_id: number;
  match_score: number;
  azure_search_score: number;
  category_score: number;
  text_score: number;
  color_score: number;
  location_score: number;
  time_score: number;
  flight_score: number;
  unique_identifier_score: number;
  confidence_level: "high" | "medium" | "low";
  ai_match_summary?: string | null;
  evidence_spans_json?: EvidenceSpans;
  status: "pending" | "approved" | "rejected" | "needs_more_info";
  review_notes?: string | null;
  lost_report?: LostReport | null;
  found_item?: FoundItem | null;
};

export type ClaimVerification = {
  id: number;
  match_candidate_id: number;
  lost_report_id: number;
  found_item_id: number;
  passenger_id?: number | null;
  status: "pending" | "submitted" | "approved" | "rejected" | "released" | "blocked";
  verification_questions_json: unknown[];
  passenger_answers_json: Record<string, unknown>;
  proof_blob_urls_json: unknown[];
  staff_review_notes?: string | null;
  fraud_score: number;
  fraud_flags_json: unknown[];
  release_checklist_json: Record<string, unknown>;
  released_to_name?: string | null;
  released_to_contact_masked?: string | null;
  approved_by_staff_id?: number | null;
  released_by_staff_id?: number | null;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  released_at?: string | null;
  created_at: string;
  updated_at: string;
  match_candidate?: MatchCandidate | null;
};

export type BarcodeLabel = {
  id: number;
  label_code: string;
  entity_type: string;
  entity_id: number;
  qr_payload: string;
  status: "active" | "revoked";
  created_by_staff_id?: number | null;
  scan_count: number;
  last_scanned_at?: string | null;
  created_at: string;
};

export type LabelScanResponse = {
  label: BarcodeLabel;
  found_item?: FoundItem | null;
};

export type AuditLog = {
  id: number;
  actor_user_id?: number | null;
  actor_role?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  severity: "info" | "warning" | "critical";
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type FraudRiskAnalytics = {
  total_claims: number;
  high_risk_claims: number;
  blocked_claims: number;
  average_fraud_score: number;
  recent: Array<{ id: number; match_candidate_id: number; status: string; fraud_score: number; fraud_flags: string[] }>;
};

export type GraphNode = {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
};

export type GraphEdge = {
  source: string;
  target: string;
  relationship: string;
  properties: Record<string, unknown>;
};

export type GraphContext = {
  scope: string;
  entity_type: string;
  entity_id: number;
  retrieval_query: string;
  provider: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  evidence: string[];
  risk_signals: string[];
  generated_summary: string;
  provenance: Record<string, unknown>;
};

export type AnalyticsSummary = {
  open_lost_reports: number;
  registered_found_items: number;
  pending_matches: number;
  high_confidence_matches: number;
  released_items: number;
  average_match_score: number;
};

export type ChatSession = {
  id: number;
  session_code: string;
  verification_status: string;
  current_state: string;
  language: string;
  voice_enabled: boolean;
  collected_data_json: Record<string, unknown>;
};

export type ChatMessage = {
  id: number;
  session_id: number;
  role: "user" | "assistant" | "system";
  message_text: string;
  structured_payload_json: Record<string, unknown>;
  created_at: string;
};

export type WorkStatus = "pending" | "processing" | "succeeded" | "failed" | "dead_letter";

export type BackgroundJob = {
  id: number;
  job_type: string;
  payload_json: Record<string, unknown>;
  status: WorkStatus;
  attempts: number;
  max_attempts: number;
  next_run_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
};

export type OutboxEvent = {
  id: number;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  payload_json: Record<string, unknown>;
  status: WorkStatus;
  attempts: number;
  max_attempts: number;
  next_attempt_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
};

export type DeepHealth = {
  status: string;
  checks: Record<string, Record<string, unknown>>;
};

export type ProviderStatus = {
  environment: string;
  use_azure_services: boolean;
  cache_backend: string;
  voice_provider: string;
  graph_rag_provider: string;
  azure: {
    openai_configured: boolean;
    openai_routes?: Record<string, string | null>;
    search_configured: boolean;
    blob_configured: boolean;
    vision_configured: boolean;
    communication_configured: boolean;
    application_insights_configured: boolean;
  };
};
