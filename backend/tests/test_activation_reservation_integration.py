from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import get_database_url
from app.models.database import (
    CeremonyApproval,
    KeyCeremony,
    User,
)
from app.services import activation_reservation_service


@pytest.mark.integration
def test_activation_reservation_transaction(monkeypatch):
    engine = create_engine(get_database_url())

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                TestSession = sessionmaker(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                    expire_on_commit=False,
                )

                monkeypatch.setattr(
                    activation_reservation_service,
                    "create_database_session",
                    lambda: TestSession,
                )

                with TestSession() as session:
                    requester = session.scalar(
                        select(User).where(
                            User.username == "key_manager_01"
                        )
                    )

                    approver = session.scalar(
                        select(User).where(
                            User.username == "security_officer_01"
                        )
                    )

                    operator = session.scalar(
                        select(User).where(
                            User.username == "hsm_operator_01"
                        )
                    )

                    assert all(
                        (requester, approver, operator)
                    )

                    ceremony = KeyCeremony(
                        id=uuid4(),
                        key_label="BANKKEY-AES-001",
                        operation="activate",
                        status="approved",
                        requested_by=requester.id,
                    )

                    session.add(ceremony)
                    session.flush()

                    session.add(
                        CeremonyApproval(
                            ceremony_id=ceremony.id,
                            approved_by=approver.id,
                            decision="approved",
                        )
                    )

                    session.commit()
                    ceremony_id = str(ceremony.id)
                    operator_id = operator.id

                result = (
                    activation_reservation_service.reserve_activation(
                        ceremony_id=ceremony_id,
                        operator_id=operator_id,
                    )
                )

                assert result["ceremony_status"] == "executing"
                assert result["key_status"] == "created"

                with TestSession() as session:
                    stored = session.get(
                        KeyCeremony,
                        ceremony.id,
                    )

                    assert stored.status == "executing"
                    assert stored.executed_by == operator_id
                    assert stored.execution_started_at is not None

                print("[OK] Reservation recorded")
                print("[OK] Operator identity recorded")
                print("[OK] Execution timestamp recorded")

                with pytest.raises(
                    activation_reservation_service.ActivationReservationError
                ):
                    activation_reservation_service.reserve_activation(
                        ceremony_id=ceremony_id,
                        operator_id=operator_id,
                    )

                print("[OK] Duplicate reservation rejected")

            finally:
                transaction.rollback()

    finally:
        engine.dispose()
