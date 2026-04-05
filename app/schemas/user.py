from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    telegram_id: int | None = None
    role: str
    is_active: bool
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    telegram_photo_url: str | None = None
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
