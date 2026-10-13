from datetime import datetime, timezone
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
from app.models.key_inventory import ManagedKey
from app.services import activation_finalization_service as finalizer
from app.services import activation_reservation_service as reservation


CEREMONY_ID = "ca812b4f-ef08-4998-a9bc-bd9ffe36cd3c"
KEY_LABEL = "BANKKEY-AES-001"


@pytest.fixture
def db_context(monkeypatch):
    engine = create_engine(get_database_url())
    connection = engine.connect()
    transaction = connection.begin()

    TestSession = sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        finalizer,
        "create_database_session",
        lambda: TestSession,
    )

    monkeypatch.setattr(
        reservation,
        "create_database_session",
        lambda: TestSession,
    )

    try:
        yield TestSession
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()


def get_users(Session):
    with Session() as session:
        users = {
            user.username: user
            for user in session.scalars(select(User)).all()
        }

        required = [
            "key_manager_01",
            "security_officer_01",
            "hsm_operator_01",
            "auditor_01",
        ]

        assert all(name in users for name in required)

        return {
            name: users[name].id
            for name in required
        }


def create_execution_ceremony(Session, users):
    with Session.begin() as session:
        ceremony = KeyCeremony(
            id=uuid4(),
            key_label=KEY_LABEL,
            operation="activate",
            status="executing",
            requested_by=users["key_manager_01"],
            executed_by=users["hsm_operator_01"],
            execution_started_at=datetime.now(timezone.utc),
        )

        session.add(ceremony)
        session.flush()

        approval = CeremonyApproval(
            ceremony_id=ceremony.id,
            approved_by=users["security_officer_01"],
            decision="approved",
        )

        session.add(approval)

        ceremony_id = str(ceremony.id)

    return ceremony_id


def fake_hsm_success(**kwargs):
    assert kwargs["key_label"] == KEY_LABEL

    return {
        "hsm_verified": True,
        "lifecycle_status": "created",
        "key_length_bits": 256,
        "sensitive": True,
        "extractable": False,
    }


@pytest.mark.integration
def test_hsm_failure_after_authorization(
    db_context, monkeypatch
):
    users = get_users(db_context)
    ceremony_id = create_execution_ceremony(
        db_context, users
    )

    def simulate_hsm_failure(**kwargs):
        raise RuntimeError("Simulated PKCS11 failure")

    monkeypatch.setattr(
        finalizer,
        "verify_registered_key",
        simulate_hsm_failure,
    )

    with pytest.raises(
        finalizer.ActivationFinalizationError,
        match="HSM verification failed",
    ):
        finalizer.finalize_activation(
            ceremony_id=ceremony_id,
            operator_id=users["hsm_operator_01"],
            user_pin="test-only",
        )

    with db_context() as session:
        ceremony = session.get(
            KeyCeremony, ceremony_id
        )

        key = session.scalar(
            select(ManagedKey).where(
                ManagedKey.key_label == KEY_LABEL
            )
        )

        assert ceremony.status == "executing"
        assert ceremony.executed_at is None
        assert key.status == "created"

    print("[OK] HSM failure blocks activation")


@pytest.mark.integration
def test_wrong_operator_rejected(db_context):
    users = get_users(db_context)
    ceremony_id = create_execution_ceremony(
        db_context, users
    )

    with pytest.raises(
        finalizer.ActivationFinalizationError,
        match="Operator authorization failed",
    ):
        finalizer.finalize_activation(
            ceremony_id=ceremony_id,
            operator_id=users["auditor_01"],
            user_pin="test-only",
        )

    print("[OK] Unauthorized operator rejected")


@pytest.mark.integration
def test_successful_finalization_transaction(
    db_context, monkeypatch
):
    users = get_users(db_context)
    ceremony_id = create_execution_ceremony(
        db_context, users
    )

    monkeypatch.setattr(
        finalizer,
        "verify_registered_key",
        fake_hsm_success,
    )

    result = finalizer.finalize_activation(
        ceremony_id=ceremony_id,
        operator_id=users["hsm_operator_01"],
        user_pin="test-only",
    )

    assert result["ceremony_status"] == "executed"
    assert result["key_status"] == "active"
    assert result["hsm_verified"] is True

    with db_context() as session:
        ceremony = session.get(
            KeyCeremony, ceremony_id
        )

        key = session.scalar(
            select(ManagedKey).where(
                ManagedKey.key_label == KEY_LABEL
            )
        )

        assert ceremony.status == "executed"
        assert ceremony.executed_at is not None
        assert key.status == "active"
        assert key.activated_at is not None

    print("[OK] Finalization transaction validated")


@pytest.mark.integration
def test_double_finalization_rejected(
    db_context, monkeypatch
):
    users = get_users(db_context)
    ceremony_id = create_execution_ceremony(
        db_context, users
    )

    monkeypatch.setattr(
        finalizer,
        "verify_registered_key",
        fake_hsm_success,
    )

    finalizer.finalize_activation(
        ceremony_id=ceremony_id,
        operator_id=users["hsm_operator_01"],
        user_pin="test-only",
    )

    with pytest.raises(
        finalizer.ActivationFinalizationError,
        match="Ceremony is not executing",
    ):
        finalizer.finalize_activation(
            ceremony_id=ceremony_id,
            operator_id=users["hsm_operator_01"],
            user_pin="test-only",
        )

    print("[OK] Double finalization rejected")
