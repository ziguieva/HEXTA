"""Real PostgreSQL concurrency tests on an ephemeral CI database only."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.database import create_database_session
from app.models.database import CeremonyApproval, KeyCeremony, User
from app.models.key_inventory import KeyStatus, ManagedKey
from app.services.activation_reservation_service import (
    ActivationReservationError,
    reserve_activation,
)
from app.services.ceremony_approval_service import (
    CeremonyApprovalError,
    approve_ceremony_request,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def ceremony_context():
    if os.environ.get("BANKKEY_TEST_DATABASE") != "ci_ephemeral_only":
        pytest.fail(
            "Concurrency tests require an explicitly isolated CI database."
        )

    SessionLocal = create_database_session()
    suffix = uuid4().hex[:16]
    label = f"CI-CONCURRENCY-{suffix}"

    with SessionLocal.begin() as session:
        requester = User(
            username=f"ci_requester_{suffix}",
            password_hash="ci-test-not-for-login",
            role="key_manager",
            is_active=True,
        )
        approver_a = User(
            username=f"ci_approver_a_{suffix}",
            password_hash="ci-test-not-for-login",
            role="security_officer",
            is_active=True,
        )
        approver_b = User(
            username=f"ci_approver_b_{suffix}",
            password_hash="ci-test-not-for-login",
            role="security_officer",
            is_active=True,
        )
        operator_a = User(
            username=f"ci_operator_a_{suffix}",
            password_hash="ci-test-not-for-login",
            role="hsm_operator",
            is_active=True,
        )
        operator_b = User(
            username=f"ci_operator_b_{suffix}",
            password_hash="ci-test-not-for-login",
            role="hsm_operator",
            is_active=True,
        )

        session.add_all([
            requester,
            approver_a,
            approver_b,
            operator_a,
            operator_b,
        ])
        session.flush()

        key = ManagedKey(
            token_label="CI-TEMPORARY-TOKEN",
            key_id=suffix,
            key_label=label,
            algorithm="AES-256",
            status=KeyStatus.CREATED.value,
        )

        ceremony = KeyCeremony(
            key_label=label,
            operation="activate",
            status="pending",
            requested_by=requester.id,
        )

        session.add_all([key, ceremony])
        session.flush()

        context = {
            "ceremony_id": ceremony.id,
            "approver_a": approver_a.username,
            "approver_b": approver_b.username,
            "operator_a": operator_a.id,
            "operator_b": operator_b.id,
        }

    return context


def run_concurrently(operations):
    barrier = Barrier(len(operations), timeout=15)

    def execute(operation):
        barrier.wait()
        return operation()

    with ThreadPoolExecutor(max_workers=len(operations)) as executor:
        futures = [
            executor.submit(execute, operation)
            for operation in operations
        ]
        return [future.result(timeout=30) for future in futures]


def test_simultaneous_approvals_allow_only_one(ceremony_context):
    context = ceremony_context
    ceremony_id = str(context["ceremony_id"])

    def attempt(username):
        try:
            approve_ceremony_request(ceremony_id, username)
            return "approved"
        except CeremonyApprovalError:
            return "rejected"

    results = run_concurrently([
        lambda: attempt(context["approver_a"]),
        lambda: attempt(context["approver_b"]),
    ])

    assert sorted(results) == ["approved", "rejected"]

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        ceremony = session.get(
            KeyCeremony, context["ceremony_id"]
        )
        count = session.scalar(
            select(func.count())
            .select_from(CeremonyApproval)
            .where(
                CeremonyApproval.ceremony_id
                == context["ceremony_id"]
            )
        )

        assert ceremony.status == "approved"
        assert count == 1


def test_simultaneous_reservations_allow_only_one(ceremony_context):
    context = ceremony_context
    ceremony_id = str(context["ceremony_id"])

    approve_ceremony_request(
        ceremony_id,
        context["approver_a"],
    )

    def attempt(operator_id):
        try:
            reserve_activation(ceremony_id, operator_id)
            return "reserved"
        except ActivationReservationError:
            return "rejected"

    results = run_concurrently([
        lambda: attempt(context["operator_a"]),
        lambda: attempt(context["operator_b"]),
    ])

    assert sorted(results) == ["rejected", "reserved"]

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        ceremony = session.get(
            KeyCeremony, context["ceremony_id"]
        )

        assert ceremony.status == "executing"
        assert ceremony.executed_by in {
            context["operator_a"],
            context["operator_b"],
        }
