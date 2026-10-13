from enum import Enum


class Role(str, Enum):
    KEY_MANAGER = "key_manager"
    SECURITY_OFFICER = "security_officer"
    HSM_OPERATOR = "hsm_operator"
    AUDITOR = "auditor"


class Permission(str, Enum):
    KEY_REQUEST = "key:request"
    KEY_APPROVE = "key:approve"
    KEY_EXECUTE = "key:execute"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS = {
    Role.KEY_MANAGER: {
        Permission.KEY_REQUEST,
    },
    Role.SECURITY_OFFICER: {
        Permission.KEY_APPROVE,
    },
    Role.HSM_OPERATOR: {
        Permission.KEY_EXECUTE,
    },
    Role.AUDITOR: {
        Permission.AUDIT_READ,
    },
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(role: Role, permission: Permission) -> None:
    if not has_permission(role, permission):
        raise PermissionError(
            f"Access denied: {role.value} cannot perform {permission.value}"
        )
