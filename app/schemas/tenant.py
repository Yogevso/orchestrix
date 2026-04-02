from pydantic import BaseModel, EmailStr
from datetime import datetime


class TenantCreate(BaseModel):
    name: str
    slug: str


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}
