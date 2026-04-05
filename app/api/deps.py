from dataclasses import dataclass

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_api_key
from app.database import get_session
from app.models.api_key import ApiKey
from app.models.user import User

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class Actor:
    """Unified representation of who is making the request."""
    type: str  # "api_key" or "user"
    api_key: ApiKey | None = None
    user: User | None = None

    @property
    def id_str(self) -> str:
        if self.type == "api_key" and self.api_key:
            return f"api_key:{self.api_key.label}"
        if self.type == "user" and self.user:
            return f"user:{self.user.id}"
        return "unknown"

    @property
    def role(self) -> str:
        if self.type == "api_key":
            return "admin"
        if self.user:
            return self.user.role
        return "user"

    @property
    def user_id(self) -> int | None:
        if self.user:
            return self.user.id
        return None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


async def get_current_actor(
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> Actor:
    """Resolve the current actor from either API key or JWT Bearer token."""
    if api_key:
        key_hash = hash_api_key(api_key)
        result = await session.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        )
        found = result.scalar_one_or_none()
        if found:
            return Actor(type="api_key", api_key=found)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    if bearer:
        from app.core.jwt import decode_access_token
        import jwt as pyjwt

        try:
            payload = decode_access_token(bearer.credentials)
        except pyjwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except pyjwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user_id = int(payload["sub"])
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is pending approval",
            )
        return Actor(type="user", user=user)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication (API key or Bearer token)",
    )


def require_admin(actor: Actor = Depends(get_current_actor)) -> Actor:
    if not actor.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return actor


def require_active_user(actor: Actor = Depends(get_current_actor)) -> Actor:
    return actor
