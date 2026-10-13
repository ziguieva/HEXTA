from uuid import UUID

from sqlalchemy import select

from app.core.database import create_database_session
from app.core.rbac import Permission, Role, require_permission
from app.models.database import (
    CeremonyApproval,
    KeyCeremony,
    User,
)
from app.models.key_inventory import ManagedKey, KeyStatus


class KeyActivationError(Exception):
    pass


def validate_key_activation(
    ceremony_id: str,
    operator_id: UUID,
):
    try:
        ceremony_uuid = UUID(ceremony_id)
    except (ValueError, TypeError) as exc:
        raise KeyActivationError(
            "Invalid ceremony identifier"
        ) from exc

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        ceremony = session.get(KeyCeremony, ceremony_uuid)

        if ceremony is None:
            raise KeyActivationError("Ceremony not found")

        if ceremony.status != "approved":
            raise KeyActivationError("Ceremony not approved")

        if ceremony.operation != "activate":
            raise KeyActivationError("Unsupported operation")

        operator = session.get(User, operator_id)

        if operator is None or not operator.is_active:
            raise KeyActivationError("Operator unavailable")

        try:
            require_permission(
                Role(operator.role),
                Permission.KEY_EXECUTE,
            )
        except (ValueError, PermissionError) as exc:
            raise KeyActivationError(
                "Execution permission denied"
            ) from exc

        approvals = session.scalars(
            select(CeremonyApproval).where(
                CeremonyApproval.ceremony_id == ceremony.id
            )
        ).all()

        if len(approvals) != 1:
            raise KeyActivationError(
                "Exactly one approval is required"
            )

        approval = approvals[0]

        if approval.decision != "approved":
            raise KeyActivationError("Approval not granted")

        if len({
            ceremony.requested_by,
            approval.approved_by,
            operator.id,
        }) != 3:
            raise KeyActivationError(
                "Separation of duties violation"
            )

        requester = session.get(User, ceremony.requested_by)
        approver = session.get(User, approval.approved_by)

        if (
            requester is None
            or not requester.is_active
            or requester.role != Role.KEY_MANAGER.value
        ):
            raise KeyActivationError(
                "Requester is not authorized"
            )

        if (
            approver is None
            or not approver.is_active
            or approver.role != Role.SECURITY_OFFICER.value
        ):
            raise KeyActivationError(
                "Approver is not authorized"
            )

        keys = session.scalars(
            select(ManagedKey).where(
                ManagedKey.key_label == ceremony.key_label
            )
        ).all()

        if len(keys) != 1:
            raise KeyActivationError(
                "Expected exactly one registered key"
            )

        key = keys[0]

        if key.status != KeyStatus.CREATED.value:
            raise KeyActivationError(
                "Key is not in CREATED state"
            )

        return {
            "ceremony_id": str(ceremony.id),
            "key_label": key.key_label,
            "current_status": key.status,
            "target_status": KeyStatus.ACTIVE.value,
            "operator": operator.username,
            "prevalidation": "passed",
        }
