from datetime import datetime
from uuid import UUID
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class Reading(Base):
    __tablename__ = "readings"
    __table_args__ = (
        CheckConstraint("noise_score BETWEEN 0 AND 4095", name="valid_score"),
        UniqueConstraint("device_id", "event_id", name="uq_device_event"),
        Index("ix_readings_created_at", "created_at"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(48), nullable=False)
    event_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    noise_score: Mapped[int] = mapped_column(Integer, nullable=False)
    noisy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
