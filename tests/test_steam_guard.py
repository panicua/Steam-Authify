import json

from app.services.steam_guard import (
    STEAM_ALPHABET,
    generate_confirmation_key,
    generate_steam_guard_code,
    parse_mafile,
    time_remaining,
)

# Fake test data — NOT real credentials
SAMPLE_SECRET = "dGVzdFNlY3JldEZvclVuaXRUZXN0cw=="  # base64("testSecretForUnitTests")

SAMPLE_MAFILE = {
    "shared_secret": "dGVzdFNlY3JldEZvclVuaXRUZXN0cw==",
    "serial_number": "1234567890123456789",
    "revocation_code": "R12345",
    "uri": "otpauth://totp/Steam:test_account?secret=FAKESECRETVALUE&issuer=Steam",
    "server_time": 1700000000,
    "account_name": "test_account",
    "token_gid": "abcdef1234567890",
    "identity_secret": "ZmFrZUlkZW50aXR5U2VjcmV0ISE=",  # base64("fakeIdentitySecret!!")
    "secret_1": "ZmFrZVNlY3JldE9uZVZhbHVlISE=",
    "status": 1,
    "device_id": "android:12345678-abcd-efgh-ijkl-123456789012",
    "fully_enrolled": True,
    "Session": {
        "SteamID": 76561198000000000,
        "AccessToken": "jwt...",
        "RefreshToken": "jwt...",
        "SessionID": None,
    },
}


def test_generate_code_valid_format():
    code = generate_steam_guard_code(SAMPLE_SECRET, timestamp=1700000000)
    assert len(code) == 5
    assert all(c in STEAM_ALPHABET for c in code)


def test_code_changes_every_30s():
    code1 = generate_steam_guard_code(SAMPLE_SECRET, timestamp=1000)
    code2 = generate_steam_guard_code(SAMPLE_SECRET, timestamp=1030)
    assert code1 != code2


def test_same_window_same_code():
    code1 = generate_steam_guard_code(SAMPLE_SECRET, timestamp=1000)
    code2 = generate_steam_guard_code(SAMPLE_SECRET, timestamp=1015)
    assert code1 == code2


def test_deterministic():
    code1 = generate_steam_guard_code(SAMPLE_SECRET, timestamp=1700000000)
    code2 = generate_steam_guard_code(SAMPLE_SECRET, timestamp=1700000000)
    assert code1 == code2


def test_generate_code_current_time():
    code = generate_steam_guard_code(SAMPLE_SECRET)
    assert len(code) == 5
    assert all(c in STEAM_ALPHABET for c in code)


def test_time_remaining():
    remaining = time_remaining()
    assert 0 < remaining <= 30


def test_parse_mafile():
    result = parse_mafile(SAMPLE_MAFILE)
    assert result["account_name"] == "test_account"
    assert result["shared_secret"] == "dGVzdFNlY3JldEZvclVuaXRUZXN0cw=="
    assert result["identity_secret"] == "ZmFrZUlkZW50aXR5U2VjcmV0ISE="
    assert result["device_id"] == "android:12345678-abcd-efgh-ijkl-123456789012"
    assert result["serial_number"] == "1234567890123456789"
    assert result["revocation_code"] == "R12345"
    assert result["steam_id"] == 76561198000000000


SAMPLE_IDENTITY_SECRET = "ZmFrZUlkZW50aXR5U2VjcmV0ISE="


def test_confirmation_key_valid_base64():
    import base64

    key = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "conf", timestamp=1700000000)
    decoded = base64.b64decode(key)
    assert len(decoded) == 20  # SHA1 produces 20 bytes


def test_confirmation_key_deterministic():
    key1 = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "conf", timestamp=1700000000)
    key2 = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "conf", timestamp=1700000000)
    assert key1 == key2


def test_confirmation_key_differs_by_tag():
    key_conf = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "conf", timestamp=1700000000)
    key_allow = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "allow", timestamp=1700000000)
    key_cancel = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "cancel", timestamp=1700000000)
    assert key_conf != key_allow
    assert key_conf != key_cancel
    assert key_allow != key_cancel


def test_confirmation_key_differs_by_time():
    key1 = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "conf", timestamp=1000)
    key2 = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "conf", timestamp=1001)
    assert key1 != key2


def test_confirmation_key_current_time():
    import base64

    key = generate_confirmation_key(SAMPLE_IDENTITY_SECRET, "conf")
    decoded = base64.b64decode(key)
    assert len(decoded) == 20


def test_parse_mafile_minimal():
    minimal = {"shared_secret": "abc123==", "account_name": "test"}
    result = parse_mafile(minimal)
    assert result["account_name"] == "test"
    assert result["shared_secret"] == "abc123=="
    assert result["identity_secret"] is None
    assert result["device_id"] is None
    assert result["steam_id"] is None
