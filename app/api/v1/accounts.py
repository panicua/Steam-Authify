import base64
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Actor, require_active_user
from app.core.audit import record_audit
from app.core.limiter import limiter
from app.core.redis import get_redis
from app.core.security import decrypt_value, encrypt_value
from app.database import get_session
from app.models.steam_account import SteamAccount
from app.schemas.steam_account import (
    SteamAccountCreate,
    SteamAccountRead,
    SteamGuardCode,
    SteamGuardGenerateRequest,
)
from app.services.steam_guard import generate_steam_guard_code, parse_mafile, time_remaining

router = APIRouter(prefix="/accounts", tags=["steam-accounts"])

MAX_MAFILE_SIZE = 1_048_576  # 1 MB


def _account_to_read(account: SteamAccount) -> SteamAccountRead:
    return SteamAccountRead(
        id=account.id,
        account_name=account.account_name,
        steam_id=account.steam_id,
        has_identity_secret=account.identity_secret_encrypted is not None,
        has_device_id=account.device_id is not None,
        has_session=account.steam_session_encrypted is not None,
        serial_number=account.serial_number,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


async def _check_duplicate(
    session: AsyncSession,
    user_id: int,
    account_name: str,
    steam_id: int | None,
) -> None:
    conditions = [SteamAccount.account_name == account_name]
    if steam_id is not None:
        conditions.append(SteamAccount.steam_id == steam_id)
    existing = await session.execute(
        select(SteamAccount.account_name).where(
            SteamAccount.user_id == user_id,
            or_(*conditions),
        ).limit(1)
    )
    row = existing.first()
    if row:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account '{row[0]}' is already added",
        )


def _validate_shared_secret(shared_secret: str) -> None:
    try:
        decoded = base64.b64decode(shared_secret)
        if len(decoded) == 0:
            raise ValueError
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shared_secret: must be a valid base64-encoded string",
        )


@router.post("", response_model=SteamAccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: SteamAccountCreate,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    _validate_shared_secret(data.shared_secret)
    await _check_duplicate(session, actor.user_id, data.account_name, data.steam_id)

    account = SteamAccount(
        user_id=actor.user_id,
        account_name=data.account_name,
        steam_id=data.steam_id,
        shared_secret_encrypted=encrypt_value(data.shared_secret),
        identity_secret_encrypted=encrypt_value(data.identity_secret) if data.identity_secret else None,
        device_id=data.device_id,
        serial_number=data.serial_number,
        revocation_code_encrypted=encrypt_value(data.revocation_code) if data.revocation_code else None,
    )
    session.add(account)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account '{data.account_name}' is already added",
        )

    await record_audit(
        session,
        actor_type=actor.type,
        actor_id=actor.id_str,
        entity_type="steam_account",
        entity_id=account.id,
        action="create",
        payload={"account_name": data.account_name},
    )
    await session.commit()
    await session.refresh(account)

    return _account_to_read(account)


@router.post("/upload", response_model=SteamAccountRead, status_code=status.HTTP_201_CREATED)
async def upload_mafile(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    content = await file.read(MAX_MAFILE_SIZE + 1)
    if len(content) > MAX_MAFILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_MAFILE_SIZE // 1024} KB",
        )
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid .maFile: must be valid JSON",
        )

    parsed = parse_mafile(data)
    if not parsed.get("shared_secret"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid .maFile: missing shared_secret field",
        )
    if not parsed.get("account_name"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid .maFile: missing account_name field",
        )

    _validate_shared_secret(parsed["shared_secret"])
    await _check_duplicate(
        session, actor.user_id, parsed["account_name"], parsed.get("steam_id")
    )

    account = SteamAccount(
        user_id=actor.user_id,
        account_name=parsed["account_name"],
        steam_id=parsed.get("steam_id"),
        shared_secret_encrypted=encrypt_value(parsed["shared_secret"]),
        identity_secret_encrypted=encrypt_value(parsed["identity_secret"]) if parsed.get("identity_secret") else None,
        device_id=parsed.get("device_id"),
        serial_number=parsed.get("serial_number"),
        revocation_code_encrypted=encrypt_value(parsed["revocation_code"]) if parsed.get("revocation_code") else None,
    )
    session.add(account)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account '{parsed['account_name']}' is already added",
        )

    await record_audit(
        session,
        actor_type=actor.type,
        actor_id=actor.id_str,
        entity_type="steam_account",
        entity_id=account.id,
        action="create",
        payload={"account_name": parsed["account_name"], "source": "mafile_upload"},
    )
    await session.commit()
    await session.refresh(account)

    return _account_to_read(account)


@router.get("", response_model=list[SteamAccountRead])
async def list_accounts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    result = await session.execute(
        select(SteamAccount)
        .where(SteamAccount.user_id == actor.user_id)
        .order_by(SteamAccount.id)
        .offset(offset).limit(limit)
    )
    return [_account_to_read(a) for a in result.scalars().all()]


@router.get("/{account_id}", response_model=SteamAccountRead)
async def get_account(
    account_id: int,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    account = await session.get(SteamAccount, account_id)
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found")
    if account.user_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _account_to_read(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    account = await session.get(SteamAccount, account_id)
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found")
    if account.user_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")

    await record_audit(
        session,
        actor_type=actor.type,
        actor_id=actor.id_str,
        entity_type="steam_account",
        entity_id=account_id,
        action="delete",
        payload={"account_name": account.account_name},
    )
    await session.delete(account)
    await session.commit()


@router.get("/{account_id}/code", response_model=SteamGuardCode)
@limiter.limit("30/minute")
async def get_code(
    request: Request,
    account_id: int,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    account = await session.get(SteamAccount, account_id)
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found")
    if account.user_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")

    now = int(time.time())
    time_chunk = now // 30
    expires_in = 30 - (now % 30)

    # Check Redis cache
    r = await get_redis()
    cache_key = f"steam_code:{account_id}:{time_chunk}"
    cached = await r.get(cache_key)
    if cached:
        return SteamGuardCode(code=cached, expires_in=expires_in)

    # Generate and cache
    shared_secret = decrypt_value(account.shared_secret_encrypted)
    code = generate_steam_guard_code(shared_secret, timestamp=now)
    await r.set(cache_key, code, ex=expires_in)

    return SteamGuardCode(code=code, expires_in=expires_in)


@router.post("/generate", response_model=SteamGuardCode)
@limiter.limit("30/minute")
async def generate_code(
    request: Request,
    data: SteamGuardGenerateRequest,
    _actor: Actor = Depends(require_active_user),
):
    _validate_shared_secret(data.shared_secret)
    code = generate_steam_guard_code(data.shared_secret)
    return SteamGuardCode(code=code, expires_in=time_remaining())
