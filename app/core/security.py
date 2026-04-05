import hashlib
import secrets

from cryptography.fernet import Fernet

from app.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        if not settings.FERNET_KEY:
            raise RuntimeError(
                "FERNET_KEY is not set. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        _fernet = Fernet(settings.FERNET_KEY.encode())
    return _fernet


def encrypt_value(plaintext: str) -> bytes:
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_value(ciphertext: bytes) -> str:
    return _get_fernet().decrypt(ciphertext).decode()


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key. Returns (raw_key, key_prefix, key_hash)."""
    raw_key = f"steam_{secrets.token_urlsafe(32)}"
    key_prefix = raw_key[:12]
    key_hash = hash_api_key(raw_key)
    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
