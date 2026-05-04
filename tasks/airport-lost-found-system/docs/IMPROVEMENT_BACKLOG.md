# IMPROVEMENT_BACKLOG — AI-Powered Airport Lost & Found

> Product-engineer pass. Companion to [`docs/CODEBASE_MAP.md`](./CODEBASE_MAP.md) and [`docs/ARCHITECTURE_REVIEW.md`](./ARCHITECTURE_REVIEW.md).
> Each item has been verified against the current code — nothing here is already shipped.
> Sort key: `(wow × impact) / effort`, descending.

| # | Title | Bucket | Wow | Effort | Score |
|---|---|---|:-:|:-:|:-:|
| 1 | One-click "Run Demo Scenario" simulator | C | 9 | 1.5d | high |
| 2 | Confidence Explainer — highlighted spans + image regions | C | 10 | 3d | high |
| 3 | LLM re-ranker on top-20 hybrid candidates | B | 8 | 1d | high |
| 4 | Smart Question Generator (vision-aware verification questions) | B | 9 | 2d | high |
| 5 | Photo-only lost report (CLIP-style image-to-image search) | B | 9 | 3d | high |
| 6 | Graph RAG visualization (force-directed, in-app) | C | 8 | 3d | high |
| 7 | Bilingual chatbot prompt overhaul + streaming responses | A+B | 7 | 1d | high |
| 8 | Full Arabic RTL polish for staff UI | A | 6 | 3h | high |
| 9 | Empty states + first-run onboarding tour for staff | A | 6 | 3h | high |
| 10 | Loading skeletons + optimistic mutations on review pages | A | 5 | 3h | high |
| 11 | Form-level validation + better error messages on lost-report intake | A | 4 | 2h | med |
| 12 | Accessibility pass (focus traps, labels, alt text, keyboard) | A | 5 | 3h | med |
| 13 | "Auto-fill from photo" Generate button on found-item form | A | 7 | 2h | med |
| 14 | Notification preferences + bilingual templates + outbox auto-fire | B | 7 | 2d | med |
| 15 | Bulk staff actions (approve N, batch import found items via CSV) | B | 6 | 2d | med |
| 16 | Stronger fraud signals (velocity, device, photo-recency) | B | 7 | 2d | med |
| 17 | Real Azure end-to-end test against ephemeral resources | B | 5 | 2d | med |
| 18 | Mobile-first staff PWA with offline QR scan queue | C | 9 | 5d | med |
| 19 | WhatsApp Business API intake | C | 9 | 5d | med |
| 20 | CCTV-frame ingestion stub (still upload → detect → found-item) | C | 8 | 4d | med |
| 21 | Courier handover / cross-terminal release flow | C | 7 | 5d | low |
| 22 | Voice-first Arabic intake polish (barge-in, Azure Speech end-to-end) | C | 7 | 4d | low |
| 23 | Embedded Power BI / streaming analytics dashboard | C | 6 | 5d | low |

Below: each item with the same level of detail (title, bucket, benefit, sketch, risks, effort, wow score).

---

### 1. One-click "Run Demo Scenario" simulator — Bucket C, Wow 9, Effort 1.5d

**User-visible benefit**: A teacher / judge / pilot stakeholder clicks one button and the system seeds a fresh passenger, creates a found item with a real image, runs the AI pipeline live, scores a match, opens the claim flow, and ends with a release — in under 90 seconds, on stage.

**Implementation sketch**
- New endpoint `POST /admin/demo/scenarios/{name}` in a new [`backend/app/api/demo.py`](../backend/app/api/demo.py); guarded by `require_admin` AND `settings.environment != "production"`.
- New service `services/demo_scenario_service.py` with named scenarios (`lost_iphone_in_terminal_2`, `passport_at_security_checkpoint_a`, `gold_watch_high_value_release`).
- Each scenario: create user → POST lost report (real text + sample image bundled in `backend/app/scripts/demo_assets/`) → wait for matching job → approve match → open ClaimVerification → submit evidence → release.
- New page `frontend/src/pages/DemoConsole.tsx` (admin route `/admin/demo`) with three big buttons + live event timeline (poll `/admin/demo/scenarios/{run_id}/events` every 1s).
- Reset endpoint `DELETE /admin/demo/scenarios/{run_id}` rolls back the seeded rows by ID list captured during the run.

**Risks / dependencies**
- Must run end-to-end in <30s on local mode; Azure mode will be 2-3× slower because of inline AI calls (see `ARCHITECTURE_REVIEW` §7a). Time the scenarios and surface a "running step 3/8" progress bar.
- Demo data must be tagged (`demo_run_id` in `metadata_json`) so cleanup is idempotent.

---

### 2. Confidence Explainer — highlighted spans + image regions — Bucket C, Wow 10, Effort 3d

**User-visible benefit**: When staff open a match, the lost-report description and the found-item description are shown side-by-side with the *exact words* that contributed to each sub-score highlighted in matching colors. The found-item photo shows bounding boxes around the Vision objects/OCR text that the matcher used. Decision support, not just decision output.

**Implementation sketch**
- Extend [`matching_engine.py`](../backend/app/services/matching_engine.py) `score()` to return `evidence_spans: {category: [...], color: [...], text: [(start,end), ...], identifier: [...]}` alongside the existing breakdown.
- Persist on `MatchCandidate` as new column `evidence_spans_json` (Alembic migration `0004_evidence_spans.py`).
- Have [`api/utils.upsert_match_candidate`](../backend/app/api/utils.py) store it.
- Frontend: replace [`ScoreBreakdown.tsx`](../frontend/src/components/ScoreBreakdown.tsx) with `MatchEvidencePanel.tsx`. Render two `<pre>` blocks with `<mark className="bg-amber-200">` wrappers for matched substrings.
- For images: render `<img>` over a `<canvas>` and draw rectangles from `vision_tags_json` bounding boxes (already returned by `analyze_uploaded_item_image` but currently discarded — see [`azure_vision_service.py:35-38`](../backend/app/services/azure_vision_service.py); we throw away `obj.bounding_box`).
- Add the explainer to `MatchReviewPage.tsx` and `LostReportDetailPage.tsx`.

**Risks / dependencies**
- Need to keep the bounding-box format from the Azure SDK; ensure the local mock returns a comparable structure.
- Span merging is fiddly when the same word appears in multiple categories — pick one color by precedence (`identifier > color > category > text`).

---

### 3. LLM re-ranker on top-20 hybrid candidates — Bucket B, Wow 8, Effort 1d

**User-visible benefit**: Match precision jumps materially with no Search index changes. The matcher fetches top 20 from Azure Search hybrid + rule recall, then asks a single OpenAI call to rerank by "which is most likely to be the same item, considering category, brand, color, location, time, and unique markings".

**Implementation sketch**
- New method `azure_openai_service.rerank_candidates(query: dict, candidates: list[dict]) -> list[(id, score, reason)]`. JSON mode, deterministic `temperature=0`, FAST route. Single batched prompt with all 20 candidates.
- Modify [`api/utils.run_matching_for_lost_report`](../backend/app/api/utils.py:214) to:
  1. Pull top 20 from Azure Search instead of 10.
  2. Call rerank with the lost-report attributes + 20 short candidate descriptors.
  3. Use the reranker's score as a *replacement* for `azure_search_score` (still 30% weight).
  4. Cache reranker output by `(lost_report_id, candidate_ids_hash)` for 1h.
- Local-mode fallback: skip rerank, return original ordering.

**Risks / dependencies**
- One extra OpenAI call per matching event. With caching it's ~free for reruns.
- Watch context length — keep candidate descriptors to ~80 tokens each (≤2000 total).
- Need a labelled benchmark to prove improvement; reuse the seed data + add 10 hard cases.

---

### 4. Smart Question Generator for claim verification — Bucket B, Wow 9, Effort 2d

**User-visible benefit**: When a claim is opened, the verification questions aren't generic ("describe a unique mark") — they're targeted at things the *staff* can see in the photo and OCR but the *passenger* should know without seeing the item. "There is text printed on the back of the device — what does it say?" "There is a sticker on the laptop lid — what color?" "The passport has a visa stamp — from which country?"

**Implementation sketch**
- Replace `_default_questions()` at [`claim_verifications.py:354-360`](../backend/app/api/claim_verifications.py) with a call to a new `azure_openai_service.generate_verification_questions(found_item_attrs, vision_tags, ocr_text)` method (REASONING route).
- Prompt: "Generate 3 verification questions a passenger would only know if they truly own this item. Use the item attributes, vision tags, and OCR text below. Do NOT ask anything visible from a generic photo of this category. Do NOT reveal serial numbers in the question text."
- Cache by `found_item.id + version_of(vision_tags+ocr)`.
- Persist the *answers*' similarity score on `ClaimVerification.passenger_answers_json[answer_quality_score]` (computed via `text_similarity` against the expected answer the LLM also produced privately, never shown).
- Add `answer_quality_score` to fraud signals.

**Risks / dependencies**
- The "expected answer" must never be returned to the passenger; store it in a *staff-only* sub-payload.
- Risk of asking unanswerable questions — instruct the LLM to mark each question with `confidence` and only show questions ≥0.7.
- Connects directly to bucket B item #16 (fraud signals).

---

### 5. Photo-only lost report (image-to-image search) — Bucket B, Wow 9, Effort 3d

**User-visible benefit**: A passenger uploads a photo of a *similar* item ("a phone like mine") instead of describing it; the system finds visually similar found items.

**Implementation sketch**
- New service `services/image_embedding_service.py`. Two providers:
  - Azure mode: call Azure AI Vision Image Retrieval (vectorize-image API) — returns 1024-d embedding. Endpoint already configured under `AZURE_AI_VISION_*`.
  - Local mode: stub returns a hash-bag vector of the file bytes (not real similarity, just a placeholder).
- Add `image_vector_id` + `image_embedding_blob_url` columns to `LostReport` and `FoundItem` (Alembic `0005_image_embeddings.py`).
- Extend `azure_search_service` to add a second vector field `image_vector` to the Search index (separate from `content_vector`).
- New endpoint `POST /lost-reports/photo-only` (public, rate-limited) — accepts a single file upload, no description required; creates a `LostReport` with placeholder text and an `image_vector_id`, then runs matching with image-vector-only.
- New SPA page `/lost-report-photo` with a single big upload control.

**Risks / dependencies**
- Azure AI Vision Image Retrieval is a separate SKU — confirm it's enabled on the existing resource, otherwise add `AZURE_AI_VISION_VECTORIZE_*` as a separate config block.
- Image vectors are slow to generate; do it in a `BackgroundJob` and surface "we're searching" UI (closes loop with #14).

---

### 6. Graph RAG visualization in-app — Bucket C, Wow 8, Effort 3d

**User-visible benefit**: Staff click "Show graph" on any match and see a force-directed graph of the report ↔ candidate ↔ found item ↔ custody events ↔ claims ↔ audit ↔ QR scans, with risk-signal nodes highlighted red. They can pan/zoom and click any node to navigate. The Graph RAG service already returns this exact shape — it's just rendered as JSON today.

**Implementation sketch**
- Add `cytoscape` (vanilla, no React wrapper, ~120kb) or `reactflow`.
- New component `components/GraphCanvas.tsx` that renders nodes/edges from `/graph-rag/matches/{id}` ([`graph_rag.py`](../backend/app/api/graph_rag.py)).
- Color by node type (lost_report=blue, found_item=green, claim=amber, audit=gray, custody=teal, risk=red).
- Edge labels visible on hover.
- Add a "Graph" tab to `MatchReviewPage.tsx`, `LostReportDetailPage.tsx`, `FoundItemDetailPage.tsx`.
- Show `risk_signals` as a side panel with severity badges.

**Risks / dependencies**
- 80 nodes / 140 edges fit easily but the layout can take a half-second; show a spinner.
- Graph caching is already in place ([`graph_context_service.py:249-273`](../backend/app/services/graph_context_service.py)).

---

### 7. Bilingual chatbot prompt overhaul + streaming responses — Bucket A+B, Wow 7, Effort 1d

**User-visible benefit**: The chatbot today asks generic follow-ups and answers in one big chunk. Replace with a tighter prompt that knows airport context (terminals, gates, baggage claim, common items, common Arabic phrasings) and stream the response token-by-token so the UI feels alive.

**Implementation sketch**
- Rewrite `generate_passenger_follow_up_questions` system prompt at [`azure_openai_service.py:457-470`](../backend/app/services/azure_openai_service.py): add airport-specific examples, make the JSON schema explicit, instruct to detect language.
- Replace the deterministic Arabic localisation in [`chat.py:332-341`](../backend/app/api/chat.py) (which is a giant `if`-chain) with: ask the LLM in Arabic when `language=="ar"`, give it a system prompt translated to Arabic.
- Add streaming endpoint `POST /chat/sessions/{id}/messages/stream` returning `text/event-stream`. Wrap `client.chat.completions.create(stream=True)`. Frontend reads with `fetch` + `ReadableStream`.
- Update `ChatPage.tsx` to render incrementally.
- Add 5 golden test transcripts in `backend/tests/test_chatbot_intake.py` covering EN+AR each (currently zero chatbot tests).

**Risks / dependencies**
- Streaming + voice (TTS) doesn't compose cleanly — disable TTS while streaming, speak the final message.
- Token budget: keep stream chunks short.

---

### 8. Full Arabic RTL polish for staff UI — Bucket A, Wow 6, Effort 3h

**User-visible benefit**: Today only `ChatPage` reacts to language. The staff UI is LTR-only; Arabic-speaking staff cannot use the dashboard naturally. RTL with mirrored sidebar and proper Arabic typography.

**Implementation sketch**
- Add `dir` attribute to `<html>` based on stored language preference.
- Add a language toggle to `Shell.tsx` header. Persist in `localStorage`.
- Tailwind: turn on RTL plugin (`tailwindcss-rtl` or use logical properties) — replace `mr-/ml-` with `me-/ms-` site-wide (sed pass).
- Translate the 30-ish UI strings in `Shell`, `PageHeader`, `ProtectedRoute`, dashboards, button labels. Add a tiny `i18n.ts` with two dictionaries; no `react-i18next` needed for ~50 strings.
- Test focus order in RTL mode (Tab should move right-to-left).

**Risks / dependencies**
- Charts in `AnalyticsDashboard` use horizontal bars — verify they don't get mirrored awkwardly.
- The matching evidence panel from #2 will need RTL highlighting too.

---

### 9. Empty states + first-run onboarding tour for staff — Bucket A, Wow 6, Effort 3h

**User-visible benefit**: A new staff member logs in to a clean DB and sees "0" everywhere with no guidance. Add empty-state cards with a CTA: "Add your first found item", "Run matching to populate the queue", "Generate a QR label".

**Implementation sketch**
- Add `EmptyState.tsx` component (icon + title + description + CTA button + optional link to runbook).
- Wire into `StaffDashboard.tsx`, `FoundItemListPage.tsx`, `LostReportListPage.tsx`, `MatchReviewPage.tsx`, `ClaimVerificationPage.tsx`, `AuditLogsPage.tsx` when their query returns `[]`.
- Add a 4-step tour (intro.js or a hand-rolled `<Tour />`) keyed off `localStorage.tourSeen` for the first staff session.
- Steps: "1. Register a found item → 2. Run matching → 3. Review match → 4. Approve and release".

**Risks / dependencies**
- Tour libraries are visually heavy; hand-rolling is fine for 4 steps.

---

### 10. Loading skeletons + optimistic mutations on review pages — Bucket A, Wow 5, Effort 3h

**User-visible benefit**: Today every navigation shows the previous page until the query resolves, then snaps. Add proper skeletons and make approve/reject feel instant.

**Implementation sketch**
- Add `Skeleton.tsx` (animated bg-slate-200 div).
- Wire into `MatchReviewPage`, `ClaimVerificationPage`, `FoundItemDetailPage`, `LostReportDetailPage`, `AnalyticsDashboard`, `AdminOperationsPage` — show skeletons when `isLoading && !data`.
- For approve/reject mutations in `MatchReviewPage`: use TanStack `onMutate` to optimistically set status, with `onError` rollback. Same for the release flow.
- Add a global `<Toast />` that surfaces success/error from mutations (today errors are silent or hidden in `mutation.error`).

**Risks / dependencies**
- Optimistic update on release is risky because release has many cascading effects — limit to approve/reject, not release.

---

### 11. Form-level validation + better error messages on lost-report intake — Bucket A, Wow 4, Effort 2h

**User-visible benefit**: Today [`LostReportForm.tsx`](../frontend/src/pages/LostReportForm.tsx) silently lets you submit with bad email format, future date, or missing contact (the backend allows zero contact info but then the chatbot status check fails forever). Validate inline and explain.

**Implementation sketch**
- Add a require-at-least-one-contact rule: `contact_email` OR `contact_phone` must be set; show inline error before submit.
- Date validation: `lost_date` cannot be more than 90 days ago (airport policy).
- Email regex on `contact_email` (HTML5 already does this but with bad messages — replace with custom `<p className="text-rose-600">`).
- Phone format check: international format `+\d{1,3}\d{6,12}`.
- Show error count + scroll-to-first-error on submit.
- Same pass on [`AddFoundItemPage.tsx`](../frontend/src/pages/AddFoundItemPage.tsx) for found-datetime sanity.

**Risks / dependencies**
- Backend allows reports without contact (chatbot path); keep this lenient on backend, strict on the form.

---

### 12. Accessibility pass — focus traps, labels, alt text, keyboard nav — Bucket A, Wow 5, Effort 3h

**User-visible benefit**: A staff member using a screen reader, or a passenger on keyboard only, can complete the lost-report flow. Important for an airport: passengers using assistive tech are a real cohort.

**Implementation sketch**
- Add `<label>` to every `<input>`/`<select>` (today most use `placeholder` only; placeholder is not accessible name) — sweep `frontend/src/pages/`.
- `alt` on the QR image in `FoundItemDetailPage.tsx` and the photo preview in `AddFoundItemPage.tsx`.
- Modal/dialog focus trap on the release-checklist modal in `MatchReviewPage`/`ClaimVerificationPage`.
- Skip-to-content link in `Shell.tsx`.
- Keyboard support for the QR scanner page: pressing Enter in the manual input triggers scan; Escape stops the camera.
- Run `axe-core` once locally and fix the top 10 violations.

**Risks / dependencies**
- None.

---

### 13. "Auto-fill from photo" Generate button on found-item form — Bucket A, Wow 7, Effort 2h

**User-visible benefit**: Staff upload a photo, click "Generate description", and the form pre-fills `category`, `color`, `brand`, `raw_description`, `vision_tags` based on a single Vision + OpenAI round-trip. Saves ~30 seconds per item across thousands of items per week.

**Implementation sketch**
- Add a button "Generate from photo" next to the file input in [`AddFoundItemPage.tsx`](../frontend/src/pages/AddFoundItemPage.tsx), disabled until a file is selected.
- New endpoint `POST /ai/describe-from-image` (staff-only) — accepts `image_url` (after upload), returns `{category, color, brand, raw_description, suggested_risk_level, confidence}`.
- Backend: chain `azure_vision_service.analyze_uploaded_item_image` → `azure_openai_service` (FAST route, prompt: "From these vision tags, OCR text, and caption, return JSON with category, brand, color, raw_description, suggested_risk_level. Be conservative.").
- On the frontend, fill the form fields with the result; mark the description with a small ✨ badge so staff know it was AI-generated and can edit before saving.

**Risks / dependencies**
- Add a small "Edit before saving" reminder banner — staff should not blindly trust AI output.
- The team's spec mentions a "Generate" button that fills the *wrong* values — this is the rewrite.

---

### 14. Notification preferences + bilingual templates + outbox auto-fire — Bucket B, Wow 7, Effort 2d

**User-visible benefit**: When a high-confidence match appears for a passenger's lost report, they automatically get an email (or SMS, per their preference) in their preferred language. Today this is manual.

**Implementation sketch**
- Add columns to `User`: `preferred_channel` (email/sms/none), `preferred_language` (en/ar). Migration `0004_user_notification_prefs.py`.
- In [`worker_service._run_job`](../backend/app/services/worker_service.py:79), add an `event_type` dispatch table. Handle `match_candidate.upserted` → if `confidence_level == high`, look up the lost report's contact + preferred channel, render a localised template, call `notification_service.send_notification`.
- Move template rendering into a new `services/notification_template_service.py` with EN+AR Jinja-style templates.
- Add a passenger preferences page `/account/preferences` (low priority — for the demo, default to "email-en" and just let it fire).
- Optional opt-out: add `notification_consent_at` so the system doesn't spam without consent.

**Risks / dependencies**
- This finally implements the long-promised outbox consumer (see ARCHITECTURE_REVIEW §5b).
- Throttle per passenger to avoid email-storms when matching reruns.

---

### 15. Bulk staff actions — Bucket B, Wow 6, Effort 2d

**User-visible benefit**: Staff can select 10 found items in the list and approve/reject/move-to-storage in one go; admins can CSV-import 200 found items at season change.

**Implementation sketch**
- Frontend: add row checkboxes to `FoundItemListPage`, `LostReportListPage`, `MatchReviewPage`. Sticky bottom action bar when ≥1 selected.
- New endpoints `POST /found-items/bulk/move`, `POST /matches/bulk/approve`, `POST /matches/bulk/reject` — accept `{ids, action_payload}`. Reuse single-action service methods in a loop with one transaction.
- Admin-only `POST /admin/found-items/import-csv` — multipart CSV upload, parse, validate, batch-insert with one outbox event per row. Returns row-by-row success/failure list.
- Audit log per bulk action with `metadata.bulk_count`.

**Risks / dependencies**
- Bulk approve at scale needs batching of Azure Search reindex calls (see ARCHITECTURE_REVIEW §7b).

---

### 16. Stronger fraud signals — Bucket B, Wow 7, Effort 2d

**User-visible benefit**: Catch scammers who claim items they don't own. Today fraud is rule-based with 5 weak signals; add behavioral and content signals.

**Implementation sketch**
- Add to [`fraud_risk_service.score_match`](../backend/app/services/fraud_risk_service.py:12):
  - **Velocity**: same passenger filing N reports in the last 24h (read from DB).
  - **Device/IP fingerprint**: log IP + UA on each `LostReport.create` (new column `created_from_ip`); flag if >3 reports from one IP for different identities.
  - **Photo recency**: if claim proof was uploaded *after* the found-item photo was indexed, that's expected — but flag if the proof image's EXIF date is after the lost_datetime.
  - **Answer-quality score** from #4.
  - **Identifier confidence**: down-weight unique-identifier matches that came purely from LLM extraction (not in raw text).
- Persist score components on `ClaimVerification.fraud_flags_json` with sub-scores so staff see the breakdown.
- Add a Fraud Detail card to `ClaimVerificationPage.tsx`.

**Risks / dependencies**
- EXIF parsing needs `Pillow` — already a transitive dep of Vision SDK.
- Don't auto-block on these — feed into the existing `release_blocked` rule.

---

### 17. Real Azure end-to-end test against ephemeral resources — Bucket B, Wow 5, Effort 2d

**User-visible benefit**: Catches "works locally, breaks in Azure" regressions before deploy. Currently zero tests exercise the Azure adapters with real SDK mocks or recorded responses.

**Implementation sketch**
- Add `pytest-vcr` or `vcrpy` to `requirements-dev.txt`.
- New `backend/tests/integration/test_azure_pipeline.py`:
  - **Test 1**: full lost-report flow with `USE_AZURE_SERVICES=true` against a recorded cassette of OpenAI + Search + Blob responses. Asserts the indexed document shape, the embedding length, the Search query body.
  - **Test 2**: end-to-end matching with fixed seed text — asserts top match is the planted candidate.
  - **Test 3**: release flow with idempotency-key replay — asserts second call returns same row, no duplicate audit log.
  - **Test 4**: Vision OCR happy path — uses a checked-in test image of a label.
- New CI job `azure-integration` runs only on `main` against ephemeral resources; cassettes used on PRs.

**Risks / dependencies**
- VCR cassettes need re-recording when SDK versions change; pin `azure-*` versions tightly.
- Don't put real keys in cassettes — use the SDK's test mode where it injects fake auth.

---

### 18. Mobile-first staff PWA with offline QR scan queue — Bucket C, Wow 9, Effort 5d

**User-visible benefit**: A staff member roaming the airport with a phone can scan QR labels even in a dead-WiFi zone (gates, baggage holds), and scans sync when connectivity returns.

**Implementation sketch**
- Add `vite-plugin-pwa` to the frontend.
- Service worker: cache app shell + last 200 found-item summaries.
- IndexedDB queue for `/labels/scan` POSTs when offline; replay when `online` event fires.
- Frontend: detect viewport, swap to mobile shell with bigger tap targets, sticky bottom nav (Dashboard / Scan / Items / Matches).
- Backend: ensure `/labels/scan` is idempotent on `(label_code, staff_id, ts_bucket)` so replayed scans don't double-count.
- Add manifest.json + icons for "install to home screen".

**Risks / dependencies**
- The web BarcodeDetector API is Chromium-only — Safari needs `@zxing/browser` fallback.
- Privacy: cached found-item summaries must not include passenger PII.

---

### 19. WhatsApp Business API intake — Bucket C, Wow 9, Effort 5d

**User-visible benefit**: A passenger messages the airport's WhatsApp number with "I lost a black backpack at gate B12" and a photo, and the system creates a lost report, runs matching, and replies with the report code — entirely in WhatsApp.

**Implementation sketch**
- Use Azure Communication Services Advanced Messaging (WhatsApp channel) — already in the dependency set (`azure-communication-email`, `azure-communication-sms`); add `azure-communication-messages`.
- New endpoint `POST /webhooks/whatsapp` — receives WhatsApp delivery events, validates signature.
- Reuse the chatbot session machinery: each WhatsApp number maps to a `ChatSession` with `channel="whatsapp"` (new column).
- New dispatcher `services/whatsapp_intake_service.py` that turns inbound messages into chat messages, runs the existing `_handle_message`, and sends the assistant reply back via ACS Messages API.
- Photo attachments → forward to `azure_blob_service.upload_file` then attach to the lost report as proof.

**Risks / dependencies**
- WhatsApp Business approval takes weeks — do it in sandbox mode for the demo.
- Compliance: WhatsApp 24-hour session window; outside that, only template messages allowed.

---

### 20. CCTV-frame ingestion stub — Bucket C, Wow 8, Effort 4d

**User-visible benefit**: Security staff upload a still frame from a terminal CCTV that shows an unattended item; the system runs detection, crops the item, and creates a found-item placeholder with the location pre-filled.

**Implementation sketch**
- New page `/staff/cctv-ingest` (staff role).
- Endpoint `POST /found-items/from-cctv-frame` — accepts image + camera_id + timestamp.
- Backend pipeline: Azure Vision detection → for each `Object` with confidence ≥0.6 and category in {bag, phone, laptop, suitcase, document}, crop, upload as separate blob, create a `FoundItem` with `storage_location="Pending pickup"`, `risk_level="normal"` (or sensitive if Vision detects "passport"), and tag `metadata={"source": "cctv", "camera_id": ..., "frame_url": ...}`.
- The location is mapped from `camera_id` via a new `airport_cameras` table seeded with terminal/gate per camera.
- Audit log severity = warning (CCTV feeds are sensitive).

**Risks / dependencies**
- Privacy-heavy: CCTV stills may contain people; the displayed image must blur faces. Use Azure Vision face-detection bounding boxes + a server-side blur step.
- Demo asset: pre-record a short MP4 of an "unattended" item and ship a frame extractor.

---

### 21. Courier handover / cross-terminal release flow — Bucket C, Wow 7, Effort 5d

**User-visible benefit**: Item is found at Terminal 3 but the passenger is at Terminal 1; staff create a courier task that another staff member at T1 picks up, with custody chain preserved.

**Implementation sketch**
- New entity `CourierTask` (`from_storage_location`, `to_storage_location`, `assigned_to_staff_id`, `status: requested|in_transit|delivered|cancelled`, `qr_label_id`, timestamps).
- New endpoint `POST /found-items/{id}/courier-tasks`.
- New page `/staff/courier-tasks` showing the staff member's open tasks.
- QR scan at hand-off creates two custody events (`moved` from + `moved` to) and writes audit logs with `severity=warning` for high-value items.
- Notification on assignment via existing notification service.

**Risks / dependencies**
- Touches custody chain — add tests for the multi-event sequence.
- Need a way to print the QR label on a thermal printer; out of scope, but the SVG endpoint exists.

---

### 22. Voice-first Arabic intake polish — Bucket C, Wow 7, Effort 4d

**User-visible benefit**: A passenger walks up to a kiosk and speaks "فقدت حقيبتي السوداء عند البوابة B12 منذ ساعة" — the system transcribes, fills the report, asks one Arabic follow-up by voice, and confirms.

**Implementation sketch**
- Switch [`speech_service.client_token`](../backend/app/services/speech_service.py:14) default to `azure` when keys are present (today defaults to `browser`).
- Frontend: replace browser SpeechRecognition with Azure Speech SDK in the kiosk mode (better Arabic accuracy).
- Add barge-in: user can interrupt the TTS by speaking.
- Add a "kiosk mode" route `/kiosk` with full-screen layout, Arabic-first UI.
- End-of-utterance detection: Azure Speech's `recognized` events fire on pauses; chain into `_handle_message` automatically.

**Risks / dependencies**
- Browser audio requires HTTPS + permission grant.
- Test with native Arabic speakers — `ar-EG` voice may not match local dialect.

---

### 23. Embedded Power BI / streaming analytics dashboard — Bucket C, Wow 6, Effort 5d

**User-visible benefit**: Operations management gets a Power BI dashboard with claim resolution times, fraud scores by terminal, AI cost over time, and high-loss-areas heatmap.

**Implementation sketch**
- Stand up an Azure Stream Analytics job consuming from an Event Hub.
- Add a new `services/analytics_publisher_service.py` that publishes to Event Hub on each `match.approved`, `item.released`, `claim.rejected` outbox event (closes loop with #14).
- Power BI workspace + dataset + report; embed via Power BI Embedded SDK in `AnalyticsDashboard.tsx` (admin-only).
- Add `POWERBI_*` config block.

**Risks / dependencies**
- Power BI Embedded has licensing cost — confirm the academy's Azure subscription includes it.
- A simpler ROI is to ship a static drill-down dashboard in the SPA first.

---

## Top 8 (chat summary)

| # | Title | Bucket | Wow |
|---|---|:--:|:--:|
| 1 | Confidence Explainer (highlighted spans + image regions) | C | 10 |
| 2 | One-click "Run Demo Scenario" simulator | C | 9 |
| 3 | Smart Question Generator for claim verification | B | 9 |
| 4 | Photo-only lost report (image-to-image) | B | 9 |
| 5 | Mobile-first staff PWA with offline QR scan queue | C | 9 |
| 6 | LLM re-ranker on top-20 hybrid candidates | B | 8 |
| 7 | Graph RAG visualization in-app | C | 8 |
| 8 | "Auto-fill from photo" Generate button on found-item form | A | 7 |
