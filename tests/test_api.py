from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4
import pytest
from sqlalchemy import text
from app.config import Settings
from app.db import get_engine
from app.main import limiter
from scripts.retention import prune


def test_health_and_public_shell(client):
    assert client.get("/live").json() == {"status": "alive"}
    assert client.get("/health").json() == {"status": "ok"}
    page = client.get("/")
    assert page.status_code == 200
    assert "Monitor sound levels and noisy readings in your library" in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert page.headers["cache-control"] == "no-store"
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/docs").status_code == 404


def test_credentials_are_scoped(client, device_headers, reader_headers):
    assert client.post("/readings", json={"score": 10, "noisy": False}).status_code == 401
    assert client.get("/readings").status_code == 401
    assert client.get("/summary").status_code == 401
    assert client.get("/readings", headers=device_headers).status_code == 401
    assert client.post("/readings", json={"score": 10, "noisy": False}, headers=reader_headers).status_code == 401


@pytest.mark.parametrize("payload", [
    {"score": -1, "noisy": False}, {"score": 4096, "noisy": True},
    {"score": 1.5, "noisy": False}, {"score": True, "noisy": True},
    {"score": "12", "noisy": False}, {"score": 5, "noisy": "false"},
    {"score": 5}, {"score": 5, "noisy": False, "device_id": "spoof"},
    {"score": 5, "noisy": False, "event_id": "not-a-uuid"},
])
def test_payload_validation(client, device_headers, payload):
    assert client.post("/readings", json=payload, headers=device_headers).status_code == 422


def test_store_and_retrieve(client, device_headers, reader_headers):
    response = client.post("/readings", json={"score": 0, "noisy": False}, headers=device_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["noise_score"] == 0 and data["device_id"] == "esp32-01"
    assert datetime.fromisoformat(data["created_at"]).tzinfo is not None
    assert client.get("/readings", headers=reader_headers).json()["items"] == [data]


def test_idempotency_and_conflict(client, device_headers, reader_headers):
    payload = {"score": 120, "noisy": True, "event_id": str(uuid4())}
    first = client.post("/readings", json=payload, headers=device_headers)
    again = client.post("/readings", json=payload, headers=device_headers)
    assert first.status_code == 201 and again.status_code == 200
    assert first.json() == again.json()
    payload["score"] = 200
    assert client.post("/readings", json=payload, headers=device_headers).status_code == 409
    assert len(client.get("/readings", headers=reader_headers).json()["items"]) == 1


def test_concurrent_retry_deduplicates(client, device_headers, reader_headers):
    payload = {"score": 1, "noisy": False, "event_id": str(uuid4())}
    with ThreadPoolExecutor(max_workers=5) as pool:
        codes = list(pool.map(lambda _: client.post("/readings", json=payload, headers=device_headers).status_code, range(5)))
    assert sorted(codes) == [200, 200, 200, 200, 201]
    assert len(client.get("/readings", headers=reader_headers).json()["items"]) == 1


def test_pagination_and_summary(client, device_headers, reader_headers):
    for score in [100, 200, 300]:
        client.post("/readings", json={"score": score, "noisy": score >= 200}, headers=device_headers)
    first = client.get("/readings?limit=2", headers=reader_headers).json()
    assert [r["noise_score"] for r in first["items"]] == [300, 200]
    second = client.get(f'/readings?limit=2&before_id={first["next_cursor"]}', headers=reader_headers).json()
    assert [r["noise_score"] for r in second["items"]] == [100]
    assert second["next_cursor"] is None
    stats = client.get("/summary?minutes=60", headers=reader_headers).json()
    assert stats["count"] == 3 and stats["average"] == 200 and stats["peak"] == 300
    assert stats["noisy_count"] == 2 and len(stats["series"]) >= 1


def test_empty_and_range_validation(client, reader_headers):
    data = client.get("/summary", headers=reader_headers).json()
    assert data["latest"] is None and data["average"] is None and data["series"] == []
    for path in ["/summary?minutes=0", "/summary?minutes=1441", "/readings?limit=501", "/readings?before_id=-1"]:
        assert client.get(path, headers=reader_headers).status_code == 422


def test_ingest_rate_limit(client, device_headers):
    limiter.count = 120
    result = client.post("/readings", json={"score": 1, "noisy": False}, headers=device_headers)
    assert result.status_code == 429 and result.headers["retry-after"] == "60"


def test_retention_preserves_recent(client, device_headers):
    for score in [1, 2]:
        client.post("/readings", json={"score": score, "noisy": False}, headers=device_headers)
    with get_engine().begin() as db:
        db.execute(text("UPDATE readings SET created_at=now()-interval '31 days' WHERE id=1"))
    prune()
    with get_engine().connect() as db:
        assert db.execute(text("SELECT id FROM readings")).scalars().all() == [2]


def test_invalid_configuration_fails_closed():
    with pytest.raises(ValueError):
        Settings(device_api_key="short")
    with pytest.raises(ValueError):
        Settings(device_api_key="a" * 64, dashboard_api_key="a" * 64)


def test_large_and_chunked_payloads_rejected(client, device_headers):
    headers = {**device_headers, "Content-Type": "application/json"}
    assert client.post("/readings", content=b"x" * 5000, headers=headers).status_code == 413
    assert client.post("/readings", content=iter([b"x" * 3000, b"y" * 3000]), headers=headers).status_code == 413
