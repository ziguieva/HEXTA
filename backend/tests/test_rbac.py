import pytest

from app.core.rbac import (
    Permission,
    Role,
    has_permission,
    require_permission,
)


def test_key_manager_can_request():
    assert has_permission(Role.KEY_MANAGER, Permission.KEY_REQUEST)


def test_key_manager_cannot_approve():
    assert not has_permission(Role.KEY_MANAGER, Permission.KEY_APPROVE)


def test_security_officer_can_approve():
    assert has_permission(
        Role.SECURITY_OFFICER,
        Permission.KEY_APPROVE,
    )


def test_operator_cannot_approve():
    assert not has_permission(
        Role.HSM_OPERATOR,
        Permission.KEY_APPROVE,
    )


def test_auditor_can_read_audit():
    assert has_permission(Role.AUDITOR, Permission.AUDIT_READ)


def test_unauthorized_operation_is_rejected():
    with pytest.raises(PermissionError):
        require_permission(
            Role.KEY_MANAGER,
            Permission.KEY_APPROVE,
        )
