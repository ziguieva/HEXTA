from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import create_database_session
from app.core.rbac import Permission, Role, require_permission
from app.models.database import (
    CeremonyApproval,
    KeyCeremony,
    User,
)


class CeremonyApprovalError(Exception):
    pass


def approve_ceremony_request(
    ceremony_id: str,
    approver_username: str,
):
    try:
        ceremony_uuid = UUID(ceremony_id)
    except (ValueError, TypeError) as exc:
        raise CeremonyApprovalError(
            "Invalid ceremony identifier"
        ) from exc

    SessionLocal = create_database_session()

    try:
        with SessionLocal.begin() as session:

            # Verrouillage transactionnel de la ceremonie.
            ceremony = session.scalar(
                select(KeyCeremony)
                .where(KeyCeremony.id == ceremony_uuid)
                .with_for_update()
            )

            if ceremony is None:
                raise CeremonyApprovalError(
                    "Ceremony not found"
                )

            if ceremony.status != "pending":
                raise CeremonyApprovalError(
                    "Ceremony is not pending"
                )

            approver = session.scalar(
                select(User).where(
                    User.username == approver_username
                )
            )

            if approver is None or not approver.is_active:
                raise CeremonyApprovalError(
                    "Approver unavailable"
                )

            try:
                role = Role(approver.role)
                require_permission(
                    role,
                    Permission.KEY_APPROVE,
                )
            except (ValueError, PermissionError) as exc:
                raise CeremonyApprovalError(
                    "Approval permission denied"
                ) from exc

            if approver.id == ceremony.requested_by:
                raise CeremonyApprovalError(
                    "Self-approval forbidden"
                )

            approval = CeremonyApproval(
                ceremony_id=ceremony.id,
                approved_by=approver.id,
                decision="approved",
            )

            session.add(approval)

            ceremony.status = "approved"

            session.flush()

            return {
                "ceremony_id": str(ceremony.id),
                "key_label": ceremony.key_label,
                "status": ceremony.status,
                "approved_by": approver.username,
            }

    except IntegrityError as exc:
        raise CeremonyApprovalError(
            "Approval already recorded"
        ) from exc
