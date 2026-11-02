# API reference

Base URL: your Render HTTPS origin. Local Docker testing uses `http://localhost:8000`.

| Method | Path | Authentication | Result |
| --- | --- | --- | --- |
| GET | `/live` | None | Process liveness |
| GET | `/health` | None | Database + migration readiness; 503 on failure |
| POST | `/readings` | `X-API-Key: DEVICE_API_KEY` | 201 new reading; 200 identical retry |
| GET | `/readings?limit=100&before_id=123` | `Authorization: Bearer DASHBOARD_API_KEY` | Newest-first items and next cursor |
| GET | `/summary?minutes=60` | Same dashboard authorization | Aggregate counts, average, peak, latest and chart buckets |
| GET | `/` | Public page shell | Dashboard login; no reading data until authorized |

## Create a reading

```json
{"score":120,"noisy":true,"event_id":"f4e2e672-ce6b-4eb9-a85c-1456b5fa933c"}
```

`score` must be an integer 0–4095. `noisy` must be a JSON boolean and represents the hardware's threshold/hysteresis result. The server stores this status rather than applying a potentially different threshold. Unknown fields are rejected. `event_id` is an optional UUID for legacy compatibility; the supplied firmware always sends it. Device identity is assigned by the server's `DEVICE_ID`, not accepted from a request.

Response:

```json
{"id":1,"device_id":"esp32-01","event_id":"f4e2e672-ce6b-4eb9-a85c-1456b5fa933c","noise_score":120,"noisy":true,"created_at":"2026-11-02T06:00:00Z"}
```

This is an illustrative response. `created_at` is the server receipt timestamp in UTC. A duplicate UUID with changed score/status returns 409. Missing UUIDs allow independent inserts.

Pagination limit is 1–500 (default 100). Pass `next_cursor` as `before_id` for the next page; `null` means no more rows. Summary windows are 5–1440 minutes and use at most approximately 121 time buckets. Dashboard CSV exports only rows currently displayed, not the full database. Loading older rows pauses automatic refresh for 30 seconds.

Request body limit: 4096 bytes. Authenticated ingest limit: 120 attempts/minute for the single configured device. Rate limit state is per process; supplied deployment is one worker/instance. Before horizontal scaling or adding devices, introduce per-device persisted credentials and a shared limiter. The service does not provide user management or a distributed edge abuse filter.

Responses: 401 invalid credentials, 409 conflicting event, 413 body too large, 422 invalid JSON schema/query, 429 rate limit (Retry-After), 503 unavailable database. Interactive API documentation is disabled in the deployed app. The dashboard calls same-origin endpoints; permissive CORS is not enabled.
