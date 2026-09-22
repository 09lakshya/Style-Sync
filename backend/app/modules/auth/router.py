from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.service import authenticate_user, create_access_token, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(AuthRequest):
    name: str = Field(min_length=2, max_length=80)
    # Asked at sign-up because it decides which trends and styling rules apply.
    # "unspecified" is a real answer, not a missing one, and is styled as unisex.
    gender: Literal["female", "male", "non-binary", "unspecified"] = "unspecified"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> dict[str, object]:
    user = await register_user(payload.name, payload.email, payload.password, payload.gender)
    token = create_access_token(str(user["id"]))
    return {"user": _public_user(user), "access_token": token, "token_type": "bearer"}


@router.post("/login")
async def login(payload: AuthRequest) -> dict[str, object]:
    user = await authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(str(user["id"]))
    return {"user": _public_user(user), "access_token": token, "token_type": "bearer"}


def _public_user(user: dict[str, object]) -> dict[str, object]:
    preferences = user.get("preferences") or {}
    gender = preferences.get("gender", "unspecified") if isinstance(preferences, dict) else "unspecified"
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "gender": gender,
    }
