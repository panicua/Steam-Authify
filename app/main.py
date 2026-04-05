from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.limiter import limiter
from app.core.security import generate_api_key
from app.database import get_session
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreated


def create_app() -> FastAPI:
    application = FastAPI(
        title="Steam Auth API",
        version="1.0.0",
        debug=settings.DEBUG,
    )

    application.state.limiter = limiter

    @application.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
        )

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    from app.api.v1.router import v1_router

    application.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    # Startup validation
    missing = []
    if not settings.FERNET_KEY:
        missing.append("FERNET_KEY")
    if not settings.SECRET_KEY:
        missing.append("SECRET_KEY")
    if not settings.ADMIN_PASSWORD:
        missing.append("ADMIN_PASSWORD")
    if not settings.TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if missing:
        import sys
        print(f"FATAL: Required environment variables not set: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env_example to .env and fill in the required values.", file=sys.stderr)

    from app.admin.views import setup_admin

    setup_admin(application)

    @application.post(
        "/bootstrap/api-key",
        response_model=ApiKeyCreated,
        status_code=status.HTTP_201_CREATED,
        tags=["bootstrap"],
    )
    async def bootstrap_api_key(
        session: AsyncSession = Depends(get_session),
        x_bootstrap_token: str | None = Header(None),
    ):
        """Create the very first API key. Only works when no keys exist yet."""
        if settings.BOOTSTRAP_TOKEN:
            if not x_bootstrap_token or x_bootstrap_token != settings.BOOTSTRAP_TOKEN:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Invalid or missing bootstrap token",
                )

        count = await session.scalar(select(func.count(ApiKey.id)))
        if count and count > 0:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="API keys already exist. Use the authenticated endpoint instead.",
            )

        raw_key, key_prefix, key_hash = generate_api_key()
        api_key = ApiKey(label="bootstrap", key_hash=key_hash, key_prefix=key_prefix)
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)

        return ApiKeyCreated(
            id=api_key.id,
            label=api_key.label,
            key_prefix=api_key.key_prefix,
            raw_key=raw_key,
            created_at=api_key.created_at,
        )

    return application


app = create_app()
