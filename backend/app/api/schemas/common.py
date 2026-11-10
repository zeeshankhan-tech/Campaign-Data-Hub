"""Shared API schema helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, Field, PlainSerializer

DecimalStr = Annotated[
    Decimal,
    PlainSerializer(lambda v: format(v, "f"), return_type=str),
]
OptionalDecimalStr = Annotated[
    Optional[Decimal],
    PlainSerializer(lambda v: format(v, "f") if v is not None else None, return_type=Optional[str]),
]


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    total: int


class ErrorBody(BaseModel):
    detail: str
    code: str
