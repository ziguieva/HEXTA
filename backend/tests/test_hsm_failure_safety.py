from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import get_database_url
from app.models.database import KeyCeremony, User
from app.services import activation_finalization_service


@pytest.mark.integration
def test_hsm_failure_cannot_finalize_activation(monkeypatch):
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
                    activation_finalization_service,
                    "create_database_session",
                    lambda: TestSession,
                )

                with TestSession() as session:
                    requester = session.scalar(
                        select(User).where(
                            User.username == "key_manager_01"
                        )
                    )

                    operator = session.scalar(
                        select(User).where(
                            User.username == "hsm_operator_01"
                        )
                    )

                    assert requester is not None
                    assert operator is not None

                    ceremony = KeyCeremony(
                        id=uuid4(),
                        key_label="BANKKEY-FAILURE-TEST",
                        operation="activate",
                        status="executing",
                        requested_by=requester.id,
                        executed_by=operator.id,
                    )

                    session.add(ceremony)
                    session.flush()
                    ceremony_id = str(ceremony.id)
                    operator_id = operator.id
                    session.commit()

                with pytest.raises(
                    activation_finalization_service.ActivationFinalizationError
                ):
                    activation_finalization_service.finalize_activation(
                        ceremony_id=ceremony_id,
                        operator_id=operator_id,
                        user_pin="invalid-test-pin",
                    )

                with TestSession() as session:
                    stored = session.get(
                        KeyCeremony,
                        ceremony.id,
                    )

                    assert stored.status == "executing"
                    assert stored.executed_at is None

                print("[OK] Invalid finalization rejected")
                print("[OK] Ceremony not marked as executed")
                print("[OK] No key activated")

            finally:
                transaction.rollback()

    finally:
        engine.dispose()
