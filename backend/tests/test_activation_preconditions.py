from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.database import create_database_session
from app.models.database import KeyCeremony, CeremonyApproval, User
from app.models.key_inventory import ManagedKey


CEREMONY_ID = UUID(
    "ca812b4f-ef08-4998-a9bc-bd9ffe36cd3c"
)


@pytest.mark.integration
def test_activation_preconditions():

    SessionLocal = create_database_session()

    with SessionLocal.begin() as session:

        ceremony = session.scalar(
            select(KeyCeremony)
            .where(KeyCeremony.id == CEREMONY_ID)
            .with_for_update()
        )

        assert ceremony is not None
        assert ceremony.status == "approved"
        assert ceremony.operation == "activate"

        approvals = session.scalars(
            select(CeremonyApproval).where(
                CeremonyApproval.ceremony_id == CEREMONY_ID
            )
        ).all()

        assert len(approvals) == 1
        assert approvals[0].decision == "approved"

        requester = session.get(User, ceremony.requested_by)
        approver = session.get(User, approvals[0].approved_by)

        operator = session.scalar(
            select(User).where(
                User.username == "hsm_operator_01"
            )
        )

        assert requester is not None
        assert approver is not None
        assert operator is not None

        assert requester.is_active
        assert approver.is_active
        assert operator.is_active

        assert requester.role == "key_manager"
        assert approver.role == "security_officer"
        assert operator.role == "hsm_operator"

        assert len({
            requester.id,
            approver.id,
            operator.id
        }) == 3

        keys = session.scalars(
            select(ManagedKey)
            .where(
                ManagedKey.key_label == ceremony.key_label
            )
            .with_for_update()
        ).all()

        assert len(keys) == 1
        assert keys[0].status == "created"
        assert keys[0].token_label == "BANKKEY-PAYMENT-LAB"
        assert keys[0].key_id == "01"

        print("[OK] All activation preconditions satisfied")
        print("[OK] PostgreSQL row locks acquired")
        print("[OK] No key lifecycle transition performed")
