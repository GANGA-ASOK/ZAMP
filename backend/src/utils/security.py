"""
Security utilities for VendorFlow: Argon2 password hashing and JWT token management.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# ---------------------------------------------------------------------------
# Argon2 Password Hasher
# ---------------------------------------------------------------------------
# Uses Argon2id (default in argon2-cffi), the state-of-the-art memory-hard
# hashing algorithm recommended by OWASP.

_hasher = PasswordHasher(
    time_cost=2,        # Number of iterations
    memory_cost=65536,  # 64 MiB memory
    parallelism=2,      # 2 parallel threads
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2id hash.
    Returns True if valid, False otherwise.
    Never throws an exception on mismatch or malformed hash.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT Configuration
# ---------------------------------------------------------------------------

def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        # Fallback for testing environments only
        return "vendorflow-insecure-test-jwt-secret-key-32-chars-minimum!"
    return secret


def _get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def _get_access_token_expire_minutes() -> int:
    try:
        return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    except ValueError:
        return 60


def _get_refresh_token_expire_days() -> int:
    try:
        return int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    except ValueError:
        return 7


# ---------------------------------------------------------------------------
# JWT Token Operations
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=_get_access_token_expire_minutes())

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email.lower(),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=_get_jwt_algorithm())


def create_refresh_token(
    user_id: str,
    email: str,
    role: str,
) -> str:
    """Create a signed JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=_get_refresh_token_expire_days())

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email.lower(),
        "role": role,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=_get_jwt_algorithm())


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises jwt.PyJWTError (e.g. ExpiredSignatureError, InvalidTokenError)
    if the token is expired, invalid, or has the wrong token type.
    """
    payload = jwt.decode(
        token,
        _get_jwt_secret(),
        algorithms=[_get_jwt_algorithm()],
        options={"require": ["sub", "exp", "type"]},
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Invalid token type: expected {expected_type}")
    return payload

