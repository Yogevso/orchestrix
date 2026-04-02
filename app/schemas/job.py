from typing import Generic, TypeVar

from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class JobCreate(BaseModel):
    type: str
    payload: str | None = None
    source: str | None = None


class JobOut(BaseModel):
    id: str
    tenant_id: str
    type: str
    status: str
    payload: str | None
    source: str | None
    retry_count: int
    created_by: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class JobListParams(BaseModel):
    status: str | None = None
    type: str | None = None
    source: str | None = None
    page: int = 1
    size: int = 20
