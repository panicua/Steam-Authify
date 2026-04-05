from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Actor, get_current_actor
from app.core.tokens import create_access_token, verify_telegram_login
from app.core.limiter import limiter
from app.database import get_session
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramLoginData(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class AuthResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    user_id: int
    role: str
    is_active: bool


@router.post("/telegram", response_model=AuthResponse)
@limiter.limit("10/minute")
async def telegram_login(
    request: Request,
    data: TelegramLoginData,
    session: AsyncSession = Depends(get_session),
):
    login_data = data.model_dump()
    if not verify_telegram_login(login_data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication data",
        )

    result = await session.execute(
        select(User).where(User.telegram_id == data.id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        username = data.username or f"tg_{data.id}"
        existing = await session.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            username = f"tg_{data.id}"

        user = User(
            username=username,
            telegram_id=data.id,
            telegram_username=data.username,
            telegram_first_name=data.first_name,
            telegram_photo_url=data.photo_url,
            role="user",
            is_active=False,
        )
        session.add(user)
    else:
        user.telegram_username = data.username
        user.telegram_first_name = data.first_name
        user.telegram_photo_url = data.photo_url

    await session.commit()

    if not user.is_active:
        return AuthResponse(
            user_id=user.id,
            role=user.role,
            is_active=False,
        )

    token = create_access_token(user.id, user.role)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        role=user.role,
        is_active=True,
    )


class MeResponse(BaseModel):
    id: int
    username: str
    telegram_id: int | None = None
    role: str
    is_active: bool
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    telegram_photo_url: str | None = None


@router.get("/me", response_model=MeResponse)
async def get_me(actor: Actor = Depends(get_current_actor)):
    if actor.type == "api_key":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for user auth only, not API keys",
        )
    return actor.user
