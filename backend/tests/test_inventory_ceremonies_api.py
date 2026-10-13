import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.web_auth import get_current_user


client = TestClient(app)


def test_keys_requires_authentication():
    response = client.get("/api/v1/keys")
    assert response.status_code == 401


def test_ceremonies_requires_authentication():
    response = client.get("/api/v1/ceremonies")
    assert response.status_code == 401


@pytest.mark.integration
def test_key_inventory_authenticated():
    if not os.environ.get("BANKKEY_DB_PASSWORD"):
        pytest.skip("Database password not configured")

    app.dependency_overrides[get_current_user] = lambda: {
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "auditor_test",
        "role": "auditor",
    }

    try:
        response = client.get("/api/v1/keys")

        assert response.status_code == 200
        keys = response.json()

        assert isinstance(keys, list)

        matching = [
            key for key in keys
            if key["key_label"] == "BANKKEY-AES-001"
        ]

        assert len(matching) == 1
        assert matching[0]["status"] == "active"
        assert matching[0]["algorithm"] == "AES-256"
        assert "password" not in matching[0]

    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_ceremonies_authenticated():
    if not os.environ.get("BANKKEY_DB_PASSWORD"):
        pytest.skip("Database password not configured")

    app.dependency_overrides[get_current_user] = lambda: {
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "auditor_test",
        "role": "auditor",
    }

    try:
        response = client.get("/api/v1/ceremonies")

        assert response.status_code == 200
        ceremonies = response.json()

        matching = [
            ceremony for ceremony in ceremonies
            if ceremony["key_label"] == "BANKKEY-AES-001"
        ]

        assert len(matching) >= 1

        executed = [
            ceremony for ceremony in matching
            if ceremony["status"] == "executed"
        ]

        assert len(executed) >= 1

        assert (
            executed[0]["executed_by"]
            == "hsm_operator_01"
        )

        assert len(executed[0]["approvals"]) == 1

    finally:
        app.dependency_overrides.clear()
