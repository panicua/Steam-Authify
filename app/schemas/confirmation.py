from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConfirmationItem(BaseModel):
    id: str
    nonce: str
    type: int
    type_name: str
    creator_id: str
    headline: str
    summary: list[str] = []
    icon: str | None = None
    created_at: datetime | None = None


class ConfirmationListResponse(BaseModel):
    account_id: int
    account_name: str
    confirmations: list[ConfirmationItem]
    fetched_at: datetime


class ConfirmationActionRequest(BaseModel):
    confirmation_ids: list[str] = Field(min_length=1)
    action: Literal["accept", "decline"]


class ConfirmationResult(BaseModel):
    id: str
    success: bool
    error: str | None = None


class ConfirmationActionResponse(BaseModel):
    results: list[ConfirmationResult]


class SessionLoginRequest(BaseModel):
    password: str = Field(min_length=1)


class SessionStatusResponse(BaseModel):
    has_session: bool
    is_valid: bool | None = None
    expires_at: datetime | None = None
