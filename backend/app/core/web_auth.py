import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.database import create_database_session
from app.models.database import User


bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
TOKEN_MINUTES = 15


def get_jwt_secret():
    secret = os.environ.get("BANKKEY_JWT_SECRET")

    if not secret or len(secret) < 32:
        raise RuntimeError(
            "BANKKEY_JWT_SECRET must contain at least 32 characters"
        )

    return secret


def create_access_token(user_id):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=TOKEN_MINUTES),
        "iss": "bankkey-hsm-lab",
        "aud": "bankkey-api",
    }

    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials,
            get_jwt_secret(),
            algorithms=[ALGORITHM],
            issuer="bankkey-hsm-lab",
            audience="bankkey-api",
            options={"require": ["sub", "exp", "iat", "nbf"]},
        )

        user_id = UUID(payload["sub"])

    except (jwt.PyJWTError, ValueError, KeyError):
        raise unauthorized from None

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        user = session.get(User, user_id)

        if user is None or not user.is_active:
            raise unauthorized

        return {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
        }
