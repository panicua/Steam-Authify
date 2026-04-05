from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SteamAccountCreate(BaseModel):
    account_name: str = Field(min_length=1, max_length=100)
    shared_secret: str = Field(min_length=1)
    identity_secret: str | None = None
    device_id: str | None = None
    serial_number: str | None = None
    revocation_code: str | None = None
    steam_id: int | None = None


class SteamAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_name: str
    steam_id: int | None = None
    has_identity_secret: bool
    has_device_id: bool
    has_session: bool = False
    serial_number: str | None = None
    created_at: datetime
    updated_at: datetime


class SteamGuardCode(BaseModel):
    code: str
    expires_in: int


class SteamGuardGenerateRequest(BaseModel):
    shared_secret: str = Field(min_length=1)
