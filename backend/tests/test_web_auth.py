from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.web_auth import (
    create_access_token,
    get_jwt_secret,
)

client = TestClient(app)


def test_login_with_invalid_credentials():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "unknown_user",
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 401


def test_profile_without_token():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_profile_with_invalid_token():
    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401


def test_valid_jwt_generation():
    user_id = uuid4()
    token = create_access_token(user_id)

    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=["HS256"],
        issuer="bankkey-hsm-lab",
        audience="bankkey-api",
    )

    assert payload["sub"] == str(user_id)


def test_expired_jwt_rejected():
    now = datetime.now(timezone.utc)

    expired_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iat": now - timedelta(hours=2),
            "nbf": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "iss": "bankkey-hsm-lab",
            "aud": "bankkey-api",
        },
        get_jwt_secret(),
        algorithm="HS256",
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {expired_token}"
        },
    )

    assert response.status_code == 401


@pytest.mark.integration
def test_real_user_login():
    import os

    username = os.environ.get("BANKKEY_TEST_USERNAME")
    password = os.environ.get("BANKKEY_TEST_PASSWORD")

    if not username or not password:
        pytest.skip("Test user credentials not configured")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    profile = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert profile.status_code == 200
    assert profile.json()["username"] == username
    assert profile.json()["role"] == "key_manager"
