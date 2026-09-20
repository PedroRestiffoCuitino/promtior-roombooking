"""Authentication for the two challenge users (JWT tokens, salted hashing)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

# Both users authenticate with the password defined in the challenge.
PASSWORD = "TechnicalChallengePromtior"

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me")
JWT_ALG = "HS256"
TOKEN_TTL_MINUTES = 480  # 8 working hours


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000).hex()


def _make_user() -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    return salt.hex(), _hash(PASSWORD, salt)


# Salted password hashes are generated once at import time.
_USERS = {"User1": _make_user(), "User2": _make_user()}


def verify_user(username: str, password: str) -> bool:
    stored = _USERS.get(username)
    if not stored:
        return False
    salt_hex, expected = stored
    candidate = _hash(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, expected)


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("sub")
    except JWTError:
        return None
