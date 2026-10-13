from uuid import UUID

from sqlalchemy import select

from app.core.database import create_database_session
from app.core.rbac import Permission, Role, require_permission
from app.models.database import (
    CeremonyApproval,
    KeyCeremony,
    User,
)


class CeremonyExecutionError(Exception):
    pass


def verify_execution_authorization(
    ceremony_id: str,
    operator_username: str,
):
    try:
        ceremony_uuid = UUID(ceremony_id)
    except (ValueError, TypeError) as exc:
        raise CeremonyExecutionError(
            "Invalid ceremony identifier"
        ) from exc

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        ceremony = session.get(KeyCeremony, ceremony_uuid)

        if ceremony is None:
            raise CeremonyExecutionError(
                "Ceremony not found"
            )

        if ceremony.status != "approved":
            raise CeremonyExecutionError(
                "Ceremony is not approved"
            )

        operator = session.scalar(
            select(User).where(
                User.username == operator_username
            )
        )

        if operator is None or not operator.is_active:
            raise CeremonyExecutionError(
                "Operator unavailable"
            )

        try:
            role = Role(operator.role)
            require_permission(
                role,
                Permission.KEY_EXECUTE,
            )
        except (ValueError, PermissionError) as exc:
            raise CeremonyExecutionError(
                "Execution permission denied"
            ) from exc

        approvals = session.scalars(
            select(CeremonyApproval).where(
                CeremonyApproval.ceremony_id == ceremony.id
            )
        ).all()

        if len(approvals) != 1:
            raise CeremonyExecutionError(
                "Invalid approval count"
            )

        approval = approvals[0]

        if approval.decision != "approved":
            raise CeremonyExecutionError(
                "Ceremony approval rejected"
            )

        if operator.id in {
            ceremony.requested_by,
            approval.approved_by,
        }:
            raise CeremonyExecutionError(
                "Separation of duties violation"
            )

        approver = session.get(
            User, approval.approved_by
        )

        if (
            approver is None
            or not approver.is_active
            or approver.role != Role.SECURITY_OFFICER.value
        ):
            raise CeremonyExecutionError(
                "Approver is no longer authorized"
            )

        return {
            "ceremony_id": str(ceremony.id),
            "key_label": ceremony.key_label,
            "operation": ceremony.operation,
            "status": ceremony.status,
            "operator": operator.username,
            "authorized": True,
        }
