import base64
import hashlib
import hmac
import struct
import time

STEAM_ALPHABET = "23456789BCDFGHJKMNPQRTVWXY"


def generate_steam_guard_code(shared_secret: str, timestamp: int | None = None) -> str:
    """Generate a Steam Guard TOTP code.

    Args:
        shared_secret: Base64-encoded shared secret from .maFile
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        5-character Steam Guard code
    """
    if timestamp is None:
        timestamp = int(time.time())

    time_chunk = timestamp // 30
    time_bytes = struct.pack(">Q", time_chunk)

    secret_bytes = base64.b64decode(shared_secret)
    hmac_hash = hmac.new(secret_bytes, time_bytes, hashlib.sha1).digest()

    offset = hmac_hash[19] & 0x0F
    code_int = struct.unpack(">I", hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF

    code_chars = []
    for _ in range(5):
        code_chars.append(STEAM_ALPHABET[code_int % len(STEAM_ALPHABET)])
        code_int //= len(STEAM_ALPHABET)

    return "".join(code_chars)


def time_remaining() -> int:
    """Seconds remaining until the current code expires."""
    return 30 - (int(time.time()) % 30)


def generate_confirmation_key(identity_secret: str, tag: str, timestamp: int | None = None) -> str:
    """Generate a confirmation key for Steam trade confirmations.

    Args:
        identity_secret: Base64-encoded identity secret from .maFile
        tag: Operation tag - "conf" (list), "details", "allow" (accept), "cancel" (decline)
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Base64-encoded confirmation key
    """
    if timestamp is None:
        timestamp = int(time.time())

    buffer = struct.pack(">Q", timestamp)
    buffer += tag.encode("ascii")

    secret_bytes = base64.b64decode(identity_secret)
    mac = hmac.new(secret_bytes, buffer, hashlib.sha1).digest()
    return base64.b64encode(mac).decode("ascii")


def parse_mafile(data: dict) -> dict:
    """Extract relevant fields from a .maFile JSON structure.

    Returns a dict with keys matching SteamAccountCreate schema fields.
    """
    session = data.get("Session", {})

    result = {
        "account_name": data.get("account_name", ""),
        "shared_secret": data.get("shared_secret", ""),
        "identity_secret": data.get("identity_secret"),
        "device_id": data.get("device_id"),
        "serial_number": data.get("serial_number"),
        "revocation_code": data.get("revocation_code"),
        "steam_id": session.get("SteamID") if session else None,
    }

    return result
