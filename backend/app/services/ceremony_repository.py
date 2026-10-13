from sqlalchemy import select

from app.core.database import create_database_session
from app.core.rbac import Permission, Role, require_permission
from app.models.database import KeyCeremony, User


class CeremonyRepositoryError(Exception):
    pass


def create_ceremony_request(
    username: str,
    key_label: str,
    operation: str,
):
    if not key_label or not key_label.strip():
        raise CeremonyRepositoryError("Key label is required")

    if operation != "activate":
        raise CeremonyRepositoryError("Unsupported operation")

    SessionLocal = create_database_session()

    with SessionLocal.begin() as session:
        user = session.scalar(
            select(User).where(User.username == username)
        )

        if user is None or not user.is_active:
            raise CeremonyRepositoryError(
                "User not found or inactive"
            )

        try:
            role = Role(user.role)
            require_permission(role, Permission.KEY_REQUEST)
        except (ValueError, PermissionError) as exc:
            raise CeremonyRepositoryError(
                "User cannot request key operations"
            ) from exc

        ceremony = KeyCeremony(
            key_label=key_label.strip(),
            operation=operation,
            status="pending",
            requested_by=user.id,
        )

        session.add(ceremony)
        session.flush()

        return {
            "id": str(ceremony.id),
            "key_label": ceremony.key_label,
            "operation": ceremony.operation,
            "status": ceremony.status,
            "requested_by": username,
        }
