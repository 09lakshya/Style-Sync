import base64
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.auth.repository import user_repository


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def check_password(password: str, hashed_password: str, password_salt: str = "") -> bool:
    """Verify password against bcrypt hash or legacy PBKDF2 hash."""
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    # Legacy PBKDF2 fallback for backward compatibility
    if password_salt:
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), password_salt.encode("utf-8"), 150_000)
        expected = base64.urlsafe_b64encode(digest).decode("utf-8")
        return hmac.compare_digest(expected, hashed_password)

    return False


def create_access_token(subject: str, expires_in_minutes: int | None = None) -> str:
    """Generate a signed JWT access token."""
    expire_delta = timedelta(minutes=expires_in_minutes or settings.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expire_delta
    payload = {
        "sub": str(subject),
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Validate and decode a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except jwt.PyJWTError:
        return None


async def register_user(name: str, email: str, password: str) -> dict[str, Any]:
    """Register a new user in MongoDB."""
    normalized_email = email.lower().strip()
    existing = await user_repository.find_by_email(normalized_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    pwd_hash = hash_password(password)
    user = await user_repository.create_user(
        name=name.strip(),
        email=normalized_email,
        password_hash=pwd_hash,
    )
    return user


async def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    """Verify credentials and return user document if valid."""
    user = await user_repository.find_by_email(email.lower().strip())
    if not user:
        return None

    pwd_hash = str(user.get("password_hash", ""))
    pwd_salt = str(user.get("password_salt", ""))
    if not check_password(password, pwd_hash, pwd_salt):
        return None

    return user


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Retrieve user by ID."""
    return await user_repository.find_by_id(user_id)
