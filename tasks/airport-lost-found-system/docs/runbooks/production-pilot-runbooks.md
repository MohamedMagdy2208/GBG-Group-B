# Production Pilot Runbooks

These runbooks are for the controlled Azure pilot. They assume Azure Container Apps, Azure Database for PostgreSQL, Azure Redis, Azure AI Search, Blob Storage, Communication Services, Key Vault, and Application Insights.

## Failed Search Indexing
1. Open Admin > Operations and filter outbox events for `failed` or `dead_letter`.
2. Confirm Azure AI Search health in `/health/ready/deep`.
3. Check Application Insights for `search_*` errors and the matching `x-request-id`.
4. Fix credentials, index schema, or service availability.
5. Retry the affected job or outbox event. If the index schema changed, run the backend startup path or restart the backend so `create_or_update_index` executes.
6. Re-run matching for the affected lost report or found item.

## Failed Notifications
1. Review `/admin/outbox` and `/notifications` for failed delivery records.
2. Verify Communication Services connection string and sender configuration in Key Vault.
3. Check ACS sender/domain reputation and SMS sender eligibility.
4. Retry after correcting configuration. Avoid resending manually if the passenger already received the message through another channel.
5. If delivery remains blocked, add an audit note and use staff-assisted contact.

## Stuck Jobs
1. Open Admin > Operations and inspect queue backlog, attempts, and `last_error`.
2. Check worker container logs for `worker_processed` and `worker_failed` events.
3. Verify Postgres and Redis are healthy in `/health/ready/deep`.
4. Restart the worker Container App revision.
5. Retry failed jobs from the Operations page. Dead-lettered jobs require staff/admin review before retry.

## Incident Triage
1. Capture the affected request ID from the UI response or API `x-request-id`.
2. Search Application Insights logs and traces by request ID.
3. Check current health: `/health/live`, `/health/ready`, and `/health/ready/deep`.
4. Review recent audit logs for auth, release, QR, claim, and admin actions.
5. If privacy exposure is suspected, disable affected accounts and rotate relevant Key Vault secrets.
6. Record the incident timeline, root cause, customer impact, and corrective action.

## Backup And Restore
1. Confirm PostgreSQL Flexible Server automated backups are enabled and retention matches airport policy.
2. Before risky changes, create a manual restore point or export.
3. Restore into a new staging database first.
4. Run Alembic migrations against the restored database.
5. Smoke test auth, lost report creation, matching, release workflow, Graph RAG, and analytics.
6. Promote connection strings through Key Vault only after validation.

## Rollback
1. Stop production promotion and keep the previous Container Apps revision active.
2. If a new revision is already receiving traffic, shift traffic back to the last healthy revision.
3. Do not downgrade database schema unless a tested downgrade is available and data impact is understood.
4. If the issue is schema-related, restore to staging and prepare a forward-fix migration.
5. Re-run CI gates, migration smoke tests, and API smoke checks before redeploying.

## Release Gate Checklist
- CI backend tests passed.
- Frontend production build passed.
- Docker build smoke tests passed.
- Alembic migration smoke test passed.
- `/health/ready/deep` is ready in staging.
- Seed data is disabled in production.
- Key Vault secrets are current.
- Staff/admin accounts are MFA-ready.
- Runbook owner and escalation channel are assigned.
