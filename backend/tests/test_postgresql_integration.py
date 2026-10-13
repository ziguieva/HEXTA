"""PostgreSQL integration tests for an isolated laboratory database."""

from uuid import uuid4

import pytest
from sqlalchemy import inspect, text

from app.core.database import create_database_session
from app.models.database import KeyCeremony, User
from app.services.audit_service import compute_hash


@pytest.mark.integration
def test_postgresql_migrations_and_audit_trigger():
    SessionLocal = create_database_session()

    with SessionLocal() as session:
        try:
            connection = session.connection()
            inspector = inspect(connection)

            required_tables = {
                "users",
                "managed_keys",
                "key_ceremonies",
                "ceremony_approvals",
                "bankkey_audit_events",
            }

            existing_tables = set(
                inspector.get_table_names(schema="public")
            )

            assert required_tables <= existing_tables

            user = User(
                username=f"ci_manager_{uuid4().hex[:12]}",
                password_hash="integration-test-placeholder",
                role="key_manager",
                is_active=True,
            )

            session.add(user)
            session.flush()

            ceremony = KeyCeremony(
                key_label=f"CI-TEST-{uuid4().hex[:12]}",
                operation="activate",
                status="pending",
                requested_by=user.id,
            )

            session.add(ceremony)
            session.flush()

            event = session.execute(
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
                """),
                {"ceremony_id": ceremony.id},
            ).mappings().one()

            assert event["event_type"] == "ceremony_requested"
            assert event["new_status"] == "pending"

            assert compute_hash(dict(event)) == event["event_hash"]

        finally:
            session.rollback()
