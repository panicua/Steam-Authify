import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def _get_secret() -> str:
    return settings.JWT_SECRET_KEY or settings.SECRET_KEY


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, _get_secret(), algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, _get_secret(), algorithms=[settings.JWT_ALGORITHM])


def verify_telegram_login(data: dict) -> bool:
    """Verify Telegram Login Widget data using the bot token.

    See: https://core.telegram.org/widgets/login#checking-authorization
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return False

    check_hash = data.get("hash", "")
    # Build the check string from all fields except "hash", sorted alphabetically
    filtered = {k: v for k, v in data.items() if k != "hash" and v is not None}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(filtered.items()))

    # Secret key is SHA256 of the bot token
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, check_hash):
        return False

    # Check auth_date is not too old (allow 1 day)
    auth_date = int(data.get("auth_date", 0))
    now = int(datetime.now(timezone.utc).timestamp())
    if now - auth_date > 86400:
        return False

    return True
