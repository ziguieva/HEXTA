from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.database import create_database_session
from app.core.rbac import Role
from app.models.database import (
    CeremonyApproval,
    KeyCeremony,
    User,
)
from app.models.key_inventory import ManagedKey, KeyStatus
from app.services.key_verification_service import (
    verify_registered_key,
)


class ActivationFinalizationError(Exception):
    pass


def finalize_activation(
    ceremony_id: str,
    operator_id: UUID,
    user_pin: str,
):
    try:
        ceremony_uuid = UUID(ceremony_id)
    except (TypeError, ValueError) as exc:
        raise ActivationFinalizationError(
            "Invalid ceremony identifier"
        ) from exc

    if not user_pin:
        raise ActivationFinalizationError(
            "HSM authentication required"
        )

    SessionLocal = create_database_session()

    with SessionLocal.begin() as session:
        ceremony = session.scalar(
            select(KeyCeremony)
            .where(KeyCeremony.id == ceremony_uuid)
            .with_for_update()
        )

        if ceremony is None:
            raise ActivationFinalizationError(
                "Ceremony not found"
            )

        if ceremony.status != "executing":
            raise ActivationFinalizationError(
                "Ceremony is not executing"
            )

        if ceremony.operation != "activate":
            raise ActivationFinalizationError(
                "Unsupported operation"
            )

        operator = session.get(User, operator_id)

        if (
            operator is None
            or not operator.is_active
            or operator.role != Role.HSM_OPERATOR.value
            or ceremony.executed_by != operator.id
        ):
            raise ActivationFinalizationError(
                "Operator authorization failed"
            )

        approvals = session.scalars(
            select(CeremonyApproval).where(
                CeremonyApproval.ceremony_id == ceremony.id
            )
        ).all()

        if len(approvals) != 1:
            raise ActivationFinalizationError(
                "Invalid ceremony approvals"
            )

        approval = approvals[0]

        if approval.decision != "approved":
            raise ActivationFinalizationError(
                "Ceremony not approved"
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
            raise ActivationFinalizationError(
                "Invalid ceremony participants"
            )

        if len({
            requester.id,
            approver.id,
            operator.id,
        }) != 3:
            raise ActivationFinalizationError(
                "Separation of duties violation"
            )

        keys = session.scalars(
            select(ManagedKey)
            .where(
                ManagedKey.key_label == ceremony.key_label
            )
            .with_for_update()
        ).all()

        if len(keys) != 1:
            raise ActivationFinalizationError(
                "Expected exactly one managed key"
            )

        key = keys[0]

        if key.status != KeyStatus.CREATED.value:
            raise ActivationFinalizationError(
                "Key is not in CREATED state"
            )

        # Verification reelle via PKCS#11.
        # Aucune preuve booleenne fournie par l'appelant.
        try:
            hsm_result = verify_registered_key(
                key_label=key.key_label,
                user_pin=user_pin,
            )
        except Exception as exc:
            raise ActivationFinalizationError(
                "HSM verification failed"
            ) from exc

        if (
            hsm_result["hsm_verified"] is not True
            or hsm_result["lifecycle_status"]
            != KeyStatus.CREATED.value
            or hsm_result["key_length_bits"] != 256
            or hsm_result["sensitive"] is not True
            or hsm_result["extractable"] is not False
        ):
            raise ActivationFinalizationError(
                "HSM security requirements not satisfied"
            )

        now = datetime.now(timezone.utc)

        key.status = KeyStatus.ACTIVE.value
        key.activated_at = now

        ceremony.status = "executed"
        ceremony.executed_at = now

        session.flush()

        return {
            "ceremony_id": str(ceremony.id),
            "ceremony_status": ceremony.status,
            "key_label": key.key_label,
            "key_status": key.status,
            "executed_by": operator.username,
            "executed_at": now.isoformat(),
            "hsm_verified": True,
        }
