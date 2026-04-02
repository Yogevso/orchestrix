from pydantic import BaseModel
from datetime import datetime


class AuditLogOut(BaseModel):
    id: str
    tenant_id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
