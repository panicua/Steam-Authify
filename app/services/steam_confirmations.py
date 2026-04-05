import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.services.steam_guard import generate_confirmation_key

STEAM_MOBILECONF_URL = "https://steamcommunity.com/mobileconf"

CONFIRMATION_TYPE_NAMES = {
    1: "Generic",
    2: "Trade",
    3: "Market Listing",
    5: "Phone Change",
    6: "Account Recovery",
}


@dataclass
class Confirmation:
    id: str
    nonce: str
    type: int
    type_name: str
    creator_id: str
    headline: str
    summary: list[str]
    icon: str | None = None
    created_at: datetime | None = None


def _build_conf_params(
    identity_secret: str,
    device_id: str,
    steam_id: int,
    tag: str,
    timestamp: int | None = None,
) -> dict:
    if timestamp is None:
        timestamp = int(time.time())
    key = generate_confirmation_key(identity_secret, tag, timestamp)
    return {
        "p": device_id,
        "a": str(steam_id),
        "k": key,
        "t": str(timestamp),
        "m": "react",
        "tag": tag,
    }


def _build_cookies(steam_id: int, session_cookies: dict) -> dict:
    cookies = {
        "steamLoginSecure": session_cookies["steamLoginSecure"],
    }
    if "sessionid" in session_cookies:
        cookies["sessionid"] = session_cookies["sessionid"]
    return cookies


async def fetch_confirmations(
    identity_secret: str,
    device_id: str,
    steam_id: int,
    session_cookies: dict,
) -> list[Confirmation]:
    params = _build_conf_params(identity_secret, device_id, steam_id, "conf")
    cookies = _build_cookies(steam_id, session_cookies)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{STEAM_MOBILECONF_URL}/getlist",
            params=params,
            cookies=cookies,
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"},
        )
        resp.raise_for_status()
        data = resp.json()

    if not data.get("success"):
        if data.get("needauth") or data.get("needsauth"):
            raise SessionExpiredError("Steam session expired, please log in again")
        raise SteamConfirmationError(data.get("message", "Failed to fetch confirmations"))

    confirmations = []
    for conf in data.get("conf", []):
        conf_type = conf.get("type", 1)
        confirmations.append(Confirmation(
            id=str(conf["id"]),
            nonce=str(conf["nonce"]),
            type=conf_type,
            type_name=CONFIRMATION_TYPE_NAMES.get(conf_type, "Unknown"),
            creator_id=str(conf.get("creator_id", "")),
            headline=conf.get("headline", ""),
            summary=conf.get("summary", []),
            icon=conf.get("icon"),
            created_at=datetime.fromtimestamp(conf["creation_time"], tz=timezone.utc)
            if conf.get("creation_time")
            else None,
        ))

    return confirmations


async def respond_to_confirmation(
    identity_secret: str,
    device_id: str,
    steam_id: int,
    session_cookies: dict,
    conf_id: str,
    conf_nonce: str,
    action: str,
) -> bool:
    tag = "allow" if action == "accept" else "cancel"
    op = "allow" if action == "accept" else "cancel"

    params = _build_conf_params(identity_secret, device_id, steam_id, tag)
    params["op"] = op
    params["cid"] = conf_id
    params["ck"] = conf_nonce
    cookies = _build_cookies(steam_id, session_cookies)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{STEAM_MOBILECONF_URL}/ajaxop",
            params=params,
            cookies=cookies,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"https://steamcommunity.com/mobileconf/details/{conf_id}",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if not data.get("success"):
        if data.get("needauth") or data.get("needsauth"):
            raise SessionExpiredError("Steam session expired, please log in again")
        return False

    return True


async def validate_session(steam_id: int, session_cookies: dict) -> bool:
    cookies = _build_cookies(steam_id, session_cookies)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://steamcommunity.com/profiles/{steam_id}",
                cookies=cookies,
                headers={"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"},
                follow_redirects=False,
            )
            # If we get redirected to login page, session is invalid
            if resp.status_code in (301, 302):
                location = resp.headers.get("location", "")
                if "login" in location.lower():
                    return False
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


class SteamConfirmationError(Exception):
    pass


class SessionExpiredError(SteamConfirmationError):
    pass
