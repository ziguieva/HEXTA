"""HTTP authorization smoke tests; do not alter lab data."""
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.web_auth import get_current_user
from app.main import app

client = TestClient(app)


def _actor(role):
    return {
        "id": str(uuid4()),
        "username": f"test_{role}",
        "role": role,
    }


def test_new_actions_require_authentication():
    uid = uuid4()
    paths = [
        "/api/v1/ceremonies",
        f"/api/v1/ceremonies/{uid}/approve",
        f"/api/v1/ceremonies/{uid}/reject",
        f"/api/v1/ceremonies/{uid}/execution-check",
    ]
    for path in paths:
        response = client.post(
            path,
            json={"key_label": "TEST-KEY", "operation": "activate"}
            if path.endswith("/ceremonies") else None,
        )
        assert response.status_code == 401, (path, response.text)


def test_wrong_roles_are_rejected_before_database_access():
    uid = uuid4()
    cases = [
        ("auditor", "/api/v1/ceremonies", {"key_label": "TEST-KEY"}),
        ("key_manager", f"/api/v1/ceremonies/{uid}/approve", None),
        ("hsm_operator", f"/api/v1/ceremonies/{uid}/reject", None),
        ("security_officer", f"/api/v1/ceremonies/{uid}/execution-check", None),
    ]
    try:
        for role, path, body in cases:
            app.dependency_overrides[get_current_user] = lambda role=role: _actor(role)
            response = client.post(path, json=body)
            assert response.status_code == 403, (role, path, response.text)
    finally:
        app.dependency_overrides.clear()


def test_approve_uses_authenticated_actor(monkeypatch):
    uid = uuid4()
    calls = []

    def fake_approve(ceremony_id, username):
        calls.append((ceremony_id, username))
        return {"ceremony_id": ceremony_id, "status": "approved"}

    monkeypatch.setattr(
        "app.api.ceremony_actions.approve_ceremony_request", fake_approve
    )
    try:
        app.dependency_overrides[get_current_user] = lambda: _actor("security_officer")
        response = client.post(f"/api/v1/ceremonies/{uid}/approve")
        assert response.status_code == 200
        assert calls[0][0] == str(uid)
        assert calls[0][1] == "test_security_officer"
    finally:
        app.dependency_overrides.clear()


def test_execution_check_never_executes_hsm(monkeypatch):
    uid = uuid4()
    calls = []

    def fake_check(ceremony_id, username):
        calls.append((ceremony_id, username))
        return {"authorized": True, "status": "approved"}

    monkeypatch.setattr(
        "app.api.ceremony_actions.verify_execution_authorization", fake_check
    )
    try:
        app.dependency_overrides[get_current_user] = lambda: _actor("hsm_operator")
        response = client.post(f"/api/v1/ceremonies/{uid}/execution-check")
        assert response.status_code == 200
        assert response.json()["authorized"] is True
        assert calls == [(str(uid), "test_hsm_operator")]
    finally:
        app.dependency_overrides.clear()
