"""Domain ORM models for ingestion persistence (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IngestionRun(Base):
    """One execution of the ingestion pipeline."""

    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    deliveries: Mapped[list[Delivery]] = relationship(back_populates="last_run")


class Delivery(Base):
    """One platform weekly delivery (resends share the same natural key)."""

    __tablename__ = "deliveries"
    __table_args__ = (UniqueConstraint("platform", "week_start", name="uq_deliveries_platform_week"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    source_filename: Mapped[Optional[str]] = mapped_column(String(255))
    content_checksum: Mapped[Optional[str]] = mapped_column(String(64))
    health: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    last_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id", ondelete="SET NULL")
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    last_run: Mapped[Optional[IngestionRun]] = relationship(back_populates="deliveries")
    metric_rows: Mapped[list[MetricRow]] = relationship(
        back_populates="delivery", cascade="all, delete-orphan"
    )
    rejected_rows: Mapped[list[RejectedRow]] = relationship(
        back_populates="delivery", cascade="all, delete-orphan"
    )
    quality_check_results: Mapped[list[QualityCheckResult]] = relationship(
        back_populates="delivery", cascade="all, delete-orphan"
    )


class MetricRow(Base):
    """Accepted canonical metric row."""

    __tablename__ = "metric_rows"
    __table_args__ = (
        UniqueConstraint("platform", "campaign", "date", name="uq_metric_rows_platform_campaign_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    campaign: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    spend_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    delivery: Mapped[Delivery] = relationship(back_populates="metric_rows")


class RejectedRow(Base):
    """Row rejected during parse/normalize with reason for traceability."""

    __tablename__ = "rejected_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_row_number: Mapped[Optional[int]] = mapped_column(Integer)
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    delivery: Mapped[Delivery] = relationship(back_populates="rejected_rows")


class QualityCheckResult(Base):
    """Persisted structured finding from one quality check execution."""

    __tablename__ = "quality_check_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
    )
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False
    )
    check_id: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    affected_entities: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    delivery: Mapped[Delivery] = relationship(back_populates="quality_check_results")
