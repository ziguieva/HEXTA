from uuid import uuid4

import pytest

from app.services.ceremony_service import (
    Ceremony,
    CeremonyActor,
    CeremonyError,
    CeremonyState,
    approve_ceremony,
    execute_ceremony,
)


def setup_ceremony():
    requester = CeremonyActor(uuid4(), "key_manager")
    approver = CeremonyActor(uuid4(), "security_officer")
    operator = CeremonyActor(uuid4(), "hsm_operator")

    ceremony = Ceremony(
        requested_by=requester.user_id,
        key_label="BANKKEY-AES-001",
        operation="activate",
    )

    return ceremony, requester, approver, operator


def test_valid_ceremony():
    ceremony, _, approver, operator = setup_ceremony()

    approve_ceremony(ceremony, approver)
    assert ceremony.state == CeremonyState.APPROVED

    execute_ceremony(ceremony, operator)
    assert ceremony.state == CeremonyState.EXECUTED


def test_self_approval_rejected():
    ceremony, requester, _, _ = setup_ceremony()

    malicious_actor = CeremonyActor(
        requester.user_id,
        "security_officer",
    )

    with pytest.raises(CeremonyError):
        approve_ceremony(ceremony, malicious_actor)


def test_execution_without_approval_rejected():
    ceremony, _, _, operator = setup_ceremony()

    with pytest.raises(CeremonyError):
        execute_ceremony(ceremony, operator)


def test_unauthorized_approval_rejected():
    ceremony, _, _, operator = setup_ceremony()

    with pytest.raises(CeremonyError):
        approve_ceremony(ceremony, operator)


def test_inactive_approver_rejected():
    ceremony, _, _, _ = setup_ceremony()

    inactive = CeremonyActor(
        uuid4(),
        "security_officer",
        is_active=False,
    )

    with pytest.raises(CeremonyError):
        approve_ceremony(ceremony, inactive)


def test_duplicate_approval_rejected():
    ceremony, _, approver, _ = setup_ceremony()

    approve_ceremony(ceremony, approver)

    with pytest.raises(CeremonyError):
        approve_ceremony(ceremony, approver)


def test_operator_cannot_be_approver():
    ceremony, _, approver, _ = setup_ceremony()

    approve_ceremony(ceremony, approver)

    invalid_operator = CeremonyActor(
        approver.user_id,
        "hsm_operator",
    )

    with pytest.raises(CeremonyError):
        execute_ceremony(ceremony, invalid_operator)
