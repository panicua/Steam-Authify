"""Programmatic Steam login via IAuthenticationService API.

Performs the modern JWT-based login flow:
1. Get RSA public key
2. Encrypt password with RSA
3. Begin auth session with credentials
4. Submit Steam Guard 2FA code (auto-generated from shared_secret)
5. Poll for session completion
6. Finalize login to get steamLoginSecure cookie
"""

import asyncio
import base64
import logging
import secrets
from dataclasses import dataclass

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

from app.services.steam_guard import generate_steam_guard_code

logger = logging.getLogger(__name__)

STEAM_API_BASE = "https://api.steampowered.com/IAuthenticationService"
STEAM_LOGIN_BASE = "https://login.steampowered.com"

# EAuthSessionGuardType enum
GUARD_TYPE_DEVICE_CODE = 3  # TOTP from mobile authenticator


class SteamLoginError(Exception):
    pass


class InvalidCredentialsError(SteamLoginError):
    pass


@dataclass
class SteamSession:
    steam_id: int
    session_id: str
    steam_login_secure: str


async def login(
    account_name: str,
    password: str,
    shared_secret: str,
) -> SteamSession:
    """Perform full Steam login and return session cookies.

    Args:
        account_name: Steam account username
        password: Steam account password (used only for this call, not stored)
        shared_secret: Base64-encoded shared secret for 2FA code generation

    Returns:
        SteamSession with session cookies

    Raises:
        InvalidCredentialsError: Wrong username/password
        SteamLoginError: Other Steam API errors
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        # Step 1: Get RSA public key
        rsa_resp = await client.get(
            f"{STEAM_API_BASE}/GetPasswordRSAPublicKey/v1",
            params={"account_name": account_name},
        )
        rsa_resp.raise_for_status()
        rsa_data = rsa_resp.json().get("response", {})

        if not rsa_data.get("publickey_mod"):
            raise SteamLoginError("Failed to get RSA key from Steam")

        # Step 2: Encrypt password with RSA
        encrypted_password = _encrypt_password(
            password,
            rsa_data["publickey_mod"],
            rsa_data["publickey_exp"],
        )
        timestamp = rsa_data["timestamp"]

        # Step 3: Begin auth session
        session_id = secrets.token_hex(12)

        begin_resp = await client.post(
            f"{STEAM_API_BASE}/BeginAuthSessionViaCredentials/v1",
            data={
                "account_name": account_name,
                "encrypted_password": encrypted_password,
                "encryption_timestamp": timestamp,
                "remember_login": "true",
                "persistence": "1",
                "website_id": "Community",
            },
        )

        if begin_resp.status_code == 401 or begin_resp.status_code == 403:
            raise InvalidCredentialsError("Invalid username or password")
        begin_resp.raise_for_status()
        begin_data = begin_resp.json().get("response", {})

        if not begin_data.get("client_id"):
            error_msg = begin_data.get("extended_error_message", "")
            logger.warning("BeginAuthSession failed: %s | full response: %s", error_msg, begin_data)
            raise InvalidCredentialsError(
                f"Invalid username or password{': ' + error_msg if error_msg else ''}"
            )

        client_id = begin_data["client_id"]
        request_id = begin_data["request_id"]
        steam_id = begin_data["steamid"]
        interval = begin_data.get("interval", 5.0)

        logger.info("Steam auth session started for %s (steam_id=%s)", account_name, steam_id)

        # Step 4: Submit Steam Guard code
        guard_code = generate_steam_guard_code(shared_secret)
        logger.info("Submitting 2FA code for %s", account_name)

        guard_resp = await client.post(
            f"{STEAM_API_BASE}/UpdateAuthSessionWithSteamGuardCode/v1",
            data={
                "client_id": str(client_id),
                "steamid": str(steam_id),
                "code": guard_code,
                "code_type": str(GUARD_TYPE_DEVICE_CODE),
            },
        )

        if guard_resp.status_code != 200:
            logger.error("2FA submission failed: status=%s body=%s", guard_resp.status_code, guard_resp.text)
            raise SteamLoginError(f"Steam Guard code rejected (HTTP {guard_resp.status_code})")

        guard_data = guard_resp.json()
        logger.info("2FA response: %s", guard_data)

        # Step 5: Poll for session status
        refresh_token = None
        access_token = None
        for attempt in range(10):
            await asyncio.sleep(interval)

            poll_resp = await client.post(
                f"{STEAM_API_BASE}/PollAuthSessionStatus/v1",
                data={
                    "client_id": str(client_id),
                    "request_id": str(request_id),
                },
            )
            poll_resp.raise_for_status()
            poll_data = poll_resp.json().get("response", {})

            logger.info("Poll attempt %d: keys=%s", attempt + 1, list(poll_data.keys()))

            if poll_data.get("refresh_token"):
                refresh_token = poll_data["refresh_token"]
                access_token = poll_data.get("access_token")
                break

            if poll_data.get("had_remote_interaction") is False and attempt > 2:
                logger.warning("No remote interaction after %d polls, may be stuck", attempt + 1)

        if not refresh_token:
            raise SteamLoginError("Login timed out waiting for Steam approval")

        logger.info("Got tokens for %s, finalizing login", account_name)

        # Step 6: Finalize login to get web cookies
        finalize_resp = await client.post(
            f"{STEAM_LOGIN_BASE}/jwt/finalizelogin",
            data={
                "nonce": refresh_token,
                "sessionid": session_id,
                "redir": "https://steamcommunity.com/login/home/?goto=",
            },
        )
        finalize_resp.raise_for_status()
        finalize_data = finalize_resp.json()

        logger.info("Finalize response keys: %s", list(finalize_data.keys()))

        # The steamLoginSecure cookie value is "steamid||jwt_access_token"
        # The access_token from PollAuthSessionStatus is the JWT we need
        if not access_token:
            raise SteamLoginError("No access token received from Steam")

        steam_login_secure = f"{steam_id}||{access_token}"
        logger.info("steamLoginSecure token length: %d", len(steam_login_secure))

        return SteamSession(
            steam_id=int(steam_id),
            session_id=session_id,
            steam_login_secure=steam_login_secure,
        )


def _encrypt_password(password: str, mod_hex: str, exp_hex: str) -> str:
    """Encrypt password with Steam's RSA public key."""
    mod = int(mod_hex, 16)
    exp = int(exp_hex, 16)

    public_numbers = RSAPublicNumbers(exp, mod)
    public_key = public_numbers.public_key(default_backend())

    encrypted = public_key.encrypt(
        password.encode("utf-8"),
        padding.PKCS1v15(),
    )
    return base64.b64encode(encrypted).decode("ascii")
