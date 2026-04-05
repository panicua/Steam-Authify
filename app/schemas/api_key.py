from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApiKeyCreate(BaseModel):
    label: str


class ApiKeyCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    key_prefix: str
    raw_key: str
    created_at: datetime


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    key_prefix: str
    is_active: bool
    created_at: datetime
