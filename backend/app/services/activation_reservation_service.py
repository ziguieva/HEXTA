from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.database import create_database_session
from app.core.rbac import Permission, Role, has_permission
from app.models.database import (
    CeremonyApproval,
    KeyCeremony,
    User,
)
from app.models.key_inventory import ManagedKey, KeyStatus


class ActivationReservationError(Exception):
    pass


def reserve_activation(ceremony_id: str, operator_id: UUID):
    try:
        ceremony_uuid = UUID(ceremony_id)
    except (TypeError, ValueError) as exc:
        raise ActivationReservationError(
            "Invalid ceremony identifier"
        ) from exc

    SessionLocal = create_database_session()

    with SessionLocal.begin() as session:
        ceremony = session.scalar(
            select(KeyCeremony)
            .where(KeyCeremony.id == ceremony_uuid)
            .with_for_update()
        )

        if ceremony is None:
            raise ActivationReservationError("Ceremony not found")

        if ceremony.status != "approved":
            raise ActivationReservationError(
                "Ceremony is not available for execution"
            )

        if ceremony.operation != "activate":
            raise ActivationReservationError(
                "Unsupported operation"
            )

        operator = session.get(User, operator_id)

        if (
            operator is None
            or not operator.is_active
            or operator.role != Role.HSM_OPERATOR.value
            or not has_permission(
                Role.HSM_OPERATOR,
                Permission.KEY_EXECUTE,
            )
        ):
            raise ActivationReservationError(
                "Execution permission denied"
            )

        approvals = session.scalars(
            select(CeremonyApproval).where(
                CeremonyApproval.ceremony_id == ceremony.id
            )
        ).all()

        if len(approvals) != 1:
            raise ActivationReservationError(
                "Invalid approval count"
            )

        approval = approvals[0]

        if approval.decision != "approved":
            raise ActivationReservationError(
                "Approval not granted"
            )

        if len({
            ceremony.requested_by,
            approval.approved_by,
            operator.id,
        }) != 3:
            raise ActivationReservationError(
                "Separation of duties violation"
            )

        requester = session.get(User, ceremony.requested_by)
        approver = session.get(User, approval.approved_by)

        if (
            requester is None
            or not requester.is_active
            or requester.role != Role.KEY_MANAGER.value
            or approver is None
            or not approver.is_active
            or approver.role != Role.SECURITY_OFFICER.value
        ):
            raise ActivationReservationError(
                "Ceremony participants are not authorized"
            )

        keys = session.scalars(
            select(ManagedKey)
            .where(ManagedKey.key_label == ceremony.key_label)
            .with_for_update()
        ).all()

        if len(keys) != 1:
            raise ActivationReservationError(
                "Expected exactly one managed key"
            )

        key = keys[0]

        if key.status != KeyStatus.CREATED.value:
            raise ActivationReservationError(
                "Key is not in CREATED state"
            )

        ceremony.status = "executing"
        ceremony.execution_started_at = datetime.now(timezone.utc)
        ceremony.executed_by = operator.id

        session.flush()

        return {
            "ceremony_id": str(ceremony.id),
            "ceremony_status": ceremony.status,
            "key_label": key.key_label,
            "key_status": key.status,
            "operator": operator.username,
        }
