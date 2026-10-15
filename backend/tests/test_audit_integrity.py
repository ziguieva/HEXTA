"""PostgreSQL audit integrity tests for an ephemeral CI database."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.database import create_database_session
from app.models.database import (
    CeremonyApproval,
    KeyCeremony,
    User,
)
from app.services.audit_service import compute_hash


pytestmark = pytest.mark.integration


@pytest.fixture
def audit_context():
    if os.environ.get("BANKKEY_TEST_DATABASE") != "ci_ephemeral_only":
        pytest.fail(
            "Audit integrity tests require the isolated CI database."
        )

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        try:
            suffix = uuid4().hex[:16]

            requester = User(
                username=f"audit_requester_{suffix}",
                password_hash="ci-test-not-for-login",
                role="key_manager",
                is_active=True,
            )

            approver = User(
                username=f"audit_approver_{suffix}",
                password_hash="ci-test-not-for-login",
                role="security_officer",
                is_active=True,
            )

            session.add_all([requester, approver])
            session.flush()

            ceremony = KeyCeremony(
                key_label=f"CI-AUDIT-{suffix}",
                operation="activate",
                status="pending",
                requested_by=requester.id,
            )

            session.add(ceremony)
            session.flush()

            approval = CeremonyApproval(
                ceremony_id=ceremony.id,
                approved_by=approver.id,
                decision="approved",
            )

            session.add(approval)
            session.flush()

            ceremony.status = "approved"
            session.flush()

            ceremony.status = "executing"
            session.flush()

            events = session.execute(
                text("""
                    SELECT
                        seq,
                        entity_type,
                        entity_id,
                        event_type,
                        actor_id,
                        old_status,
                        new_status,
                        prev_hash,
                        event_hash
                    FROM bankkey_audit_events
                    WHERE entity_type = 'ceremony'
                      AND entity_id = :ceremony_id
                    ORDER BY seq
                """),
                {"ceremony_id": ceremony.id},
            ).mappings().all()

            yield {
                "session": session,
                "ceremony_id": ceremony.id,
                "events": [dict(event) for event in events],
            }

        finally:
            session.rollback()


def test_audit_sha256_chain(audit_context):
    events = audit_context["events"]

    assert len(events) == 4

    assert [event["event_type"] for event in events] == [
        "ceremony_requested",
        "decision_approved",
        "ceremony_approved",
        "ceremony_executing",
    ]

    for event in events:
        assert len(event["event_hash"]) == 64
        assert compute_hash(event) == event["event_hash"]

    for previous, current in zip(events, events[1:]):
        assert current["prev_hash"] == previous["event_hash"]


def test_audit_update_is_rejected(audit_context):
    session = audit_context["session"]
    event = audit_context["events"][0]

    with pytest.raises(DBAPIError):
        with session.begin_nested():
            session.execute(
                text("""
                    UPDATE bankkey_audit_events
                    SET event_type = 'tampered'
                    WHERE seq = :seq
                """),
                {"seq": event["seq"]},
            )

    stored = session.execute(
        text("""
            SELECT event_type, event_hash
            FROM bankkey_audit_events
            WHERE seq = :seq
        """),
        {"seq": event["seq"]},
    ).mappings().one()

    assert stored["event_type"] == event["event_type"]
    assert stored["event_hash"] == event["event_hash"]


def test_audit_delete_is_rejected(audit_context):
    session = audit_context["session"]
    event = audit_context["events"][0]

    with pytest.raises(DBAPIError):
        with session.begin_nested():
            session.execute(
                text("""
                    DELETE FROM bankkey_audit_events
                    WHERE seq = :seq
                """),
                {"seq": event["seq"]},
            )

    exists = session.scalar(
        select(
            text("COUNT(*)")
        ).select_from(
            text("bankkey_audit_events")
        ).where(
            text("seq = :seq")
        ).params(seq=event["seq"])
    )

    assert exists == 1
