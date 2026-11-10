"""Ingestion trigger/status API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IngestionCreateRequest(BaseModel):
    data_dir: Optional[str] = Field(
        default=None,
        description="Optional absolute/relative path to assessment data dir. Defaults to configured ASSESSMENT_DATA_DIR.",
    )


class IngestionCreateResponse(BaseModel):
    id: UUID
    status: str
    accepted_total: int
    rejected_total: int
    summary: dict[str, Any]


class IngestionStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    summary: Optional[dict[str, Any]] = None
