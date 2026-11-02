import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# Tests intentionally require an isolated real PostgreSQL database.
os.environ.setdefault("DEVICE_API_KEY", "d" * 64)
os.environ.setdefault("DASHBOARD_API_KEY", "r" * 64)
if not os.environ.get("DATABASE_URL"):
    raise RuntimeError("Set DATABASE_URL to an isolated PostgreSQL TEST database")
from sqlalchemy.engine import make_url
if not make_url(os.environ["DATABASE_URL"]).database.endswith("_test"):
    raise RuntimeError("Safety guard: integration test database name must end in _test")
from app.main import app, limiter
from app.db import get_engine

@pytest.fixture(autouse=True)
def clean_database():
    with get_engine().begin() as db:
        db.execute(text("TRUNCATE readings RESTART IDENTITY"))
    limiter.count = 0

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def device_headers():
    return {"X-API-Key": os.environ["DEVICE_API_KEY"]}

@pytest.fixture
def reader_headers():
    return {"Authorization": "Bearer " + os.environ["DASHBOARD_API_KEY"]}
