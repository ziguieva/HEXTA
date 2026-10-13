from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.web_auth import (
    create_access_token,
    get_current_user,
)
from app.services.auth_service import authenticate_user


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)


@router.post("/login")
def login(data: LoginRequest):
    user = authenticate_user(
        data.username,
        data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    token = create_access_token(user["id"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 900,
    }


@router.get("/me")
def get_profile(user=Depends(get_current_user)):
    return user
