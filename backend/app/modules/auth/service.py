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


# What sign-up accepts. Kept apart from style_rules.VALID_GENDERS: this is who
# the user says they are, that is which styling conventions to reach for.
VALID_PROFILE_GENDERS = {"female", "male", "non-binary", "unspecified"}

PROFILE_TO_STYLING = {
    "female": "female",
    "male": "male",
    "non-binary": "unisex",
    "unspecified": "unisex",
}


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


async def register_user(
    name: str, email: str, password: str, gender: str = "unspecified"
) -> dict[str, Any]:
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
        preferences={
            "gender": gender if gender in VALID_PROFILE_GENDERS else "unspecified",
            "preferred_colors": [],
            "style_tags": [],
            "notification_enabled": True,
        },
    )
    return user


async def get_profile_gender(user_id: str) -> str:
    """The gender the user chose at sign-up, or "unspecified"."""
    user = await user_repository.find_by_id(user_id)
    preferences = (user or {}).get("preferences") or {}
    if not isinstance(preferences, dict):
        return "unspecified"
    gender = str(preferences.get("gender", "unspecified"))
    return gender if gender in VALID_PROFILE_GENDERS else "unspecified"


async def get_styling_gender(user_id: str) -> str:
    """Profile gender mapped onto the styling vocabulary in `style_rules`.

    Non-binary and unspecified both style as unisex: the rule set only splits
    where the conventional options genuinely differ, and offering someone the
    unisex set is the honest answer when it does not know.
    """
    return PROFILE_TO_STYLING.get(await get_profile_gender(user_id), "unisex")


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
