# Verification report

Prepared 2 November 2026. The library sound monitoring dashboard has been redesigned with a white theme, plain labels, workspace navigation, a compact summary, noise history, pause/resume controls and a device setup dialog.

## Passed

- 20 integration tests against an isolated PostgreSQL 17 database: authentication scope, schema validation, persistence, timestamp timezone, concurrent retry deduplication, event conflicts, pagination, aggregates, retention, rate limits, request size limits and unsafe configuration rejection.
- Docker image build and Compose startup: migration completes before API/retention services, database and API health checks pass, runtime UID is 10001.
- Real HTTP ingestion/retrieval and idempotent retry smoke test in a disposable local environment before cleanup.
- Backup restored into a separate test database; 181 synthetic test rows restored successfully before cleanup. App restart preserved data.
- Runtime Python dependency audit: no known vulnerabilities reported at audit time. This does not cover OS packages or guarantee absence of vulnerabilities.
- Render Blueprint validated against Render's published JSON schema. No account-side deployment was attempted.
- Browser checks: redesigned login, authenticated empty state, pause/resume, setup dialog and a 390px mobile layout. No horizontal page overflow in that mobile check.
- History pagination, range selection and CSV download were exercised before the redesign; their API integration is retained. The redesigned CSV button is disabled when there are no real readings to export.
- JavaScript syntax check passed after the responsive chart update.
- Preview and restore-test reading tables cleared. Preview SQL count is zero. No seeds or simulator are included in the delivered application.

## Still requires verification

- ESP32 compile: official Core 3.3.12 package downloads repeatedly stopped before installation completed, so firmware compilation was not verified in this environment. Use Arduino IDE Verify before uploading.
- Physical ESP32 upload, wiring, sensor threshold, buzzer behavior, Wi-Fi reconnects and end-to-end HTTPS uploads must be tested with the actual board.
- The real Render hostname and root CA certificate cannot be configured until the user connects the GitHub repository to Render and deploys.
- Render billing, provisioning, public HTTPS, production backups and cloud recovery have not been tested. The source and deployment configuration are prepared; the project is not hosted in the cloud yet.
- No load/soak test or multi-device operation is claimed. The application targets one device and one web worker.

The test runner emits a Starlette warning that its httpx integration is deprecated. All tests pass; this warning affects the development test client, not the production HTTP service.

The local review instance runs at http://localhost:18080 with a separate temporary environment. Production credentials must be generated during deployment. Do not reuse test credentials.

No CI/CD workflow is included. Deployment is manual.
