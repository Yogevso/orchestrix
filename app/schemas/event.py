from pydantic import BaseModel
from datetime import datetime


class EventIngest(BaseModel):
    source: str
    batch_id: str | None = None
    event_type: str
    severity: str | None = None
    payload: str | None = None
    timestamp: datetime | None = None


class EventOut(BaseModel):
    id: str
    tenant_id: str
    source: str
    batch_id: str | None
    event_type: str
    severity: str | None
    payload: str | None
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListParams(BaseModel):
    source: str | None = None
    event_type: str | None = None
    severity: str | None = None
    page: int = 1
    size: int = 20
