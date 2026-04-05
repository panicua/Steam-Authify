import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Actor, require_active_user
from app.core.audit import record_audit
from app.core.limiter import limiter
from app.core.redis import get_redis
from app.core.security import decrypt_value, encrypt_value
from app.database import get_session
from app.models.steam_account import SteamAccount
from app.schemas.confirmation import (
    ConfirmationActionRequest,
    ConfirmationActionResponse,
    ConfirmationItem,
    ConfirmationListResponse,
    ConfirmationResult,
    SessionLoginRequest,
    SessionStatusResponse,
)
from app.services.steam_confirmations import (
    SessionExpiredError,
    SteamConfirmationError,
    fetch_confirmations,
    respond_to_confirmation,
    validate_session,
)
from app.services.steam_login import (
    InvalidCredentialsError,
    SteamLoginError,
    login as steam_login,
)

router = APIRouter(prefix="/accounts", tags=["confirmations"])


async def _get_account_with_access(
    account_id: int,
    session: AsyncSession,
    actor: Actor,
) -> SteamAccount:
    account = await session.get(SteamAccount, account_id)
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not actor.is_admin and account.user_id != actor.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")
    return account


def _get_session_cookies(account: SteamAccount) -> dict:
    if not account.steam_session_encrypted:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="No active Steam session. Please log in first.",
        )
    raw = decrypt_value(account.steam_session_encrypted)
    return json.loads(raw)


def _require_trade_ready(account: SteamAccount) -> None:
    if not account.identity_secret_encrypted:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Account is missing identity_secret (not trade-ready)",
        )
    if not account.steam_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Account is missing steam_id (required for confirmations)",
        )
    if not account.device_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Account is missing device_id (required for confirmations)",
        )


# --- Session endpoints ---


@router.post("/{account_id}/session/login")
@limiter.limit("5/minute")
async def session_login(
    request: Request,
    account_id: int,
    data: SessionLoginRequest,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    account = await _get_account_with_access(account_id, session, actor)

    shared_secret = decrypt_value(account.shared_secret_encrypted)

    try:
        steam_session = await steam_login(
            account_name=account.account_name,
            password=data.password,
            shared_secret=shared_secret,
        )
    except InvalidCredentialsError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid Steam password")
    except SteamLoginError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Steam login failed: {e}")

    # Store session cookies encrypted
    session_data = json.dumps({
        "sessionid": steam_session.session_id,
        "steamLoginSecure": steam_session.steam_login_secure,
    })
    account.steam_session_encrypted = encrypt_value(session_data)
    account.session_expires_at = None  # We don't know exact expiry

    # Update steam_id if not already set
    if not account.steam_id:
        account.steam_id = steam_session.steam_id

    await record_audit(
        session,
        actor_type=actor.type,
        actor_id=actor.id_str,
        entity_type="steam_account",
        entity_id=account.id,
        action="session_login",
        payload={"account_name": account.account_name},
    )
    await session.commit()

    return {"detail": "Steam session active", "steam_id": steam_session.steam_id}


@router.post("/{account_id}/session/logout", status_code=status.HTTP_204_NO_CONTENT)
async def session_logout(
    account_id: int,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    account = await _get_account_with_access(account_id, session, actor)
    account.steam_session_encrypted = None
    account.session_expires_at = None
    await session.commit()


@router.get("/{account_id}/session/status", response_model=SessionStatusResponse)
@limiter.limit("30/minute")
async def session_status(
    request: Request,
    account_id: int,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    account = await _get_account_with_access(account_id, session, actor)

    if not account.steam_session_encrypted:
        return SessionStatusResponse(has_session=False)

    cookies = json.loads(decrypt_value(account.steam_session_encrypted))
    is_valid = await validate_session(account.steam_id, cookies)

    if not is_valid:
        # Clear expired session
        account.steam_session_encrypted = None
        account.session_expires_at = None
        await session.commit()

    return SessionStatusResponse(
        has_session=is_valid,
        is_valid=is_valid,
        expires_at=account.session_expires_at,
    )


# --- Confirmation endpoints ---


@router.get("/{account_id}/confirmations", response_model=ConfirmationListResponse)
@limiter.limit("10/minute")
async def get_confirmations(
    request: Request,
    account_id: int,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    account = await _get_account_with_access(account_id, session, actor)
    _require_trade_ready(account)
    cookies = _get_session_cookies(account)

    # Check Redis cache
    r = await get_redis()
    cache_key = f"confirmations:{account_id}"
    cached = await r.get(cache_key)
    if cached:
        items = [ConfirmationItem(**c) for c in json.loads(cached)]
        return ConfirmationListResponse(
            account_id=account.id,
            account_name=account.account_name,
            confirmations=items,
            fetched_at=datetime.now(timezone.utc),
        )

    identity_secret = decrypt_value(account.identity_secret_encrypted)

    try:
        confs = await fetch_confirmations(
            identity_secret=identity_secret,
            device_id=account.device_id,
            steam_id=account.steam_id,
            session_cookies=cookies,
        )
    except SessionExpiredError:
        account.steam_session_encrypted = None
        await session.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Steam session expired. Please log in again.",
        )
    except SteamConfirmationError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(e))

    items = [
        ConfirmationItem(
            id=c.id,
            nonce=c.nonce,
            type=c.type,
            type_name=c.type_name,
            creator_id=c.creator_id,
            headline=c.headline,
            summary=c.summary,
            icon=c.icon,
            created_at=c.created_at,
        )
        for c in confs
    ]

    # Cache for 15 seconds
    await r.set(cache_key, json.dumps([i.model_dump(mode="json") for i in items]), ex=15)

    return ConfirmationListResponse(
        account_id=account.id,
        account_name=account.account_name,
        confirmations=items,
        fetched_at=datetime.now(timezone.utc),
    )


@router.post("/{account_id}/confirmations/{conf_id}/accept")
@limiter.limit("10/minute")
async def accept_confirmation(
    request: Request,
    account_id: int,
    conf_id: str,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    return await _handle_single_action(account_id, conf_id, "accept", session, actor)


@router.post("/{account_id}/confirmations/{conf_id}/decline")
@limiter.limit("10/minute")
async def decline_confirmation(
    request: Request,
    account_id: int,
    conf_id: str,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    return await _handle_single_action(account_id, conf_id, "decline", session, actor)


async def _handle_single_action(
    account_id: int,
    conf_id: str,
    action: str,
    session: AsyncSession,
    actor: Actor,
) -> dict:
    account = await _get_account_with_access(account_id, session, actor)
    _require_trade_ready(account)
    cookies = _get_session_cookies(account)
    identity_secret = decrypt_value(account.identity_secret_encrypted)

    # Look up the nonce from cached confirmations
    r = await get_redis()
    cache_key = f"confirmations:{account_id}"
    cached = await r.get(cache_key)

    conf_nonce = None
    if cached:
        for c in json.loads(cached):
            if c["id"] == conf_id:
                conf_nonce = c["nonce"]
                break

    if not conf_nonce:
        # Fetch fresh to get the nonce
        try:
            confs = await fetch_confirmations(
                identity_secret=identity_secret,
                device_id=account.device_id,
                steam_id=account.steam_id,
                session_cookies=cookies,
            )
        except SessionExpiredError:
            account.steam_session_encrypted = None
            await session.commit()
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="Steam session expired. Please log in again.",
            )
        except SteamConfirmationError as e:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(e))

        for c in confs:
            if c.id == conf_id:
                conf_nonce = c.nonce
                break

    if not conf_nonce:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Confirmation not found (may have already been handled)",
        )

    try:
        success = await respond_to_confirmation(
            identity_secret=identity_secret,
            device_id=account.device_id,
            steam_id=account.steam_id,
            session_cookies=cookies,
            conf_id=conf_id,
            conf_nonce=conf_nonce,
            action=action,
        )
    except SessionExpiredError:
        account.steam_session_encrypted = None
        await session.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Steam session expired. Please log in again.",
        )
    except SteamConfirmationError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(e))

    if success:
        # Invalidate cache
        await r.delete(cache_key)

        await record_audit(
            session,
            actor_type=actor.type,
            actor_id=actor.id_str,
            entity_type="confirmation",
            entity_id=None,
            action=f"confirmation_{action}",
            payload={
                "account_id": account_id,
                "account_name": account.account_name,
                "confirmation_id": conf_id,
            },
        )
        await session.commit()

    return {"success": success, "confirmation_id": conf_id, "action": action}


@router.post("/{account_id}/confirmations/batch", response_model=ConfirmationActionResponse)
@limiter.limit("5/minute")
async def batch_action(
    request: Request,
    account_id: int,
    data: ConfirmationActionRequest,
    session: AsyncSession = Depends(get_session),
    actor: Actor = Depends(require_active_user),
):
    account = await _get_account_with_access(account_id, session, actor)
    _require_trade_ready(account)
    cookies = _get_session_cookies(account)
    identity_secret = decrypt_value(account.identity_secret_encrypted)

    # Fetch current confirmations to get nonces
    try:
        confs = await fetch_confirmations(
            identity_secret=identity_secret,
            device_id=account.device_id,
            steam_id=account.steam_id,
            session_cookies=cookies,
        )
    except SessionExpiredError:
        account.steam_session_encrypted = None
        await session.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Steam session expired. Please log in again.",
        )
    except SteamConfirmationError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(e))

    conf_map = {c.id: c.nonce for c in confs}
    results = []

    for conf_id in data.confirmation_ids:
        nonce = conf_map.get(conf_id)
        if not nonce:
            results.append(ConfirmationResult(
                id=conf_id,
                success=False,
                error="Confirmation not found (may have already been handled)",
            ))
            continue

        try:
            success = await respond_to_confirmation(
                identity_secret=identity_secret,
                device_id=account.device_id,
                steam_id=account.steam_id,
                session_cookies=cookies,
                conf_id=conf_id,
                conf_nonce=nonce,
                action=data.action,
            )
            results.append(ConfirmationResult(id=conf_id, success=success))

            if success:
                await record_audit(
                    session,
                    actor_type=actor.type,
                    actor_id=actor.id_str,
                    entity_type="confirmation",
                    entity_id=None,
                    action=f"confirmation_{data.action}",
                    payload={
                        "account_id": account_id,
                        "account_name": account.account_name,
                        "confirmation_id": conf_id,
                        "batch": True,
                    },
                )
        except SessionExpiredError:
            account.steam_session_encrypted = None
            await session.commit()
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="Steam session expired. Please log in again.",
            )
        except SteamConfirmationError as e:
            results.append(ConfirmationResult(id=conf_id, success=False, error=str(e)))

    # Invalidate cache
    r = await get_redis()
    await r.delete(f"confirmations:{account_id}")
    await session.commit()

    return ConfirmationActionResponse(results=results)
