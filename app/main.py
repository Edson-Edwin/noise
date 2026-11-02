from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
import secrets
import threading
import time
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, get_engine
from app.models import Reading

log = logging.getLogger("noise_monitor")
STATIC = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app):
    get_settings()  # Fail closed if secrets or configuration are invalid.
    yield
    get_engine().dispose()

class ReadingBodyLimit:
    """Bound ingestion JSON before parsing, including chunked requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/readings":
            return await self.app(scope, receive, send)
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > 4096:
                return await JSONResponse({"detail": "Payload exceeds 4096 bytes"}, status_code=413)(scope, receive, send)
            chunks.append(body)
            if not message.get("more_body", False):
                break
        consumed = False
        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()
        await self.app(scope, replay, send)

app = FastAPI(title="Noise Monitor", version="1.0.0", docs_url=None, redoc_url=None,
              openapi_url=None, lifespan=lifespan)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.update({
        "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer", "Cache-Control": "no-store",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    })
    return response

@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    # Never log SQL parameters, connection strings, or credentials.
    log.error("database_operation_failed type=%s", type(exc).__name__)
    return JSONResponse({"detail": "Database temporarily unavailable"}, status_code=503)


def require_device(x_api_key: Annotated[str | None, Header()] = None):
    if not secrets.compare_digest((x_api_key or "").encode(), get_settings().device_api_key.get_secret_value().encode()):
        raise HTTPException(401, "Invalid device key")


def require_reader(authorization: Annotated[str | None, Header()] = None):
    expected = "Bearer " + get_settings().dashboard_api_key.get_secret_value()
    if not secrets.compare_digest((authorization or "").encode(), expected.encode()):
        raise HTTPException(401, "Invalid dashboard key", headers={"WWW-Authenticate": "Bearer"})


class IngestLimiter:
    # One worker / instance in the supplied deployment. No IP trust or unbounded map.
    def __init__(self):
        self.lock = threading.Lock()
        self.started = time.monotonic()
        self.count = 0

    def check(self):
        with self.lock:
            now = time.monotonic()
            if now - self.started >= 60:
                self.started, self.count = now, 0
            if self.count >= get_settings().ingest_per_minute:
                raise HTTPException(429, "Ingest rate exceeded", headers={"Retry-After": "60"})
            self.count += 1

limiter = IngestLimiter()
DB = Annotated[Session, Depends(get_db)]
Reader = Depends(require_reader)

class ReadingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: int = Field(strict=True, ge=0, le=4095)
    noisy: StrictBool
    event_id: UUID | None = None

class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_id: str
    event_id: UUID | None
    noise_score: int
    noisy: bool
    created_at: datetime

@app.get("/live")
def live():
    return {"status": "alive"}

@app.get("/health")
def health(db: DB):
    # Check both connectivity and schema readiness.
    db.execute(select(Reading.id).limit(1))
    revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    if revision != "0001":
        raise HTTPException(503, "Schema is not ready")
    return {"status": "ok"}

@app.post("/readings", response_model=ReadingOut, status_code=201, dependencies=[Depends(require_device)])
def create_reading(payload: ReadingIn, response: Response, db: DB):
    limiter.check()
    values = {"noise_score": payload.score, "noisy": payload.noisy,
              "event_id": payload.event_id, "device_id": get_settings().device_id}
    statement = insert(Reading).values(**values).on_conflict_do_nothing(
        constraint="uq_device_event").returning(Reading)
    row = db.execute(statement).scalar_one_or_none()
    if row is None:
        row = db.execute(select(Reading).where(Reading.device_id == values["device_id"],
                                               Reading.event_id == payload.event_id)).scalar_one()
        if row.noise_score != payload.score or row.noisy != payload.noisy:
            raise HTTPException(409, "Event ID already exists with different data")
        response.status_code = 200
    result = ReadingOut.model_validate(row)
    db.commit()
    return result

@app.get("/readings", dependencies=[Reader])
def readings(db: DB, limit: Annotated[int, Query(ge=1, le=500)] = 100,
             before_id: Annotated[int | None, Query(ge=1)] = None):
    statement = select(Reading).order_by(Reading.id.desc()).limit(limit + 1)
    if before_id is not None:
        statement = statement.where(Reading.id < before_id)
    rows = db.execute(statement).scalars().all()
    return {"items": [ReadingOut.model_validate(row) for row in rows[:limit]],
            "next_cursor": rows[limit - 1].id if len(rows) > limit else None}

@app.get("/summary", dependencies=[Reader])
def summary(db: DB, minutes: Annotated[int, Query(ge=5, le=1440)] = 60):
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes)
    # Keep the chart bounded to ~120 buckets, even over 24 hours.
    width = max(30, minutes * 60 // 120)
    bucket = (func.floor(func.extract("epoch", Reading.created_at) / width) * width).label("bucket")
    where = Reading.created_at >= start
    count, average, peak, noisy_count = db.execute(select(
        func.count(), func.avg(Reading.noise_score), func.max(Reading.noise_score),
        func.count().filter(Reading.noisy)).where(where)).one()
    chart = db.execute(select(bucket, func.avg(Reading.noise_score), func.max(Reading.noise_score))
                       .where(where).group_by(bucket).order_by(bucket)).all()
    latest = db.execute(select(Reading).order_by(Reading.id.desc()).limit(1)).scalar_one_or_none()
    return {"device_id": get_settings().device_id, "minutes": minutes,
            "server_time": now, "stale_after_seconds": get_settings().stale_after_seconds,
            "count": count, "average": round(float(average), 1) if average is not None else None,
            "peak": peak, "noisy_count": noisy_count,
            "latest": ReadingOut.model_validate(latest) if latest else None,
            "series": [{"timestamp": datetime.fromtimestamp(float(t), timezone.utc),
                        "average": round(float(a), 1), "peak": p} for t, a, p in chart]}

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")

app.add_middleware(ReadingBodyLimit)

app.mount("/static", StaticFiles(directory=STATIC), name="static")
