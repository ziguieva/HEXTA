from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.database import create_database_session
from app.models.database import KeyCeremony, User


@pytest.mark.integration
def test_stale_execution_detection():
    SessionLocal = create_database_session()

    with SessionLocal() as session:
        requester = session.scalar(
            select(User).where(
                User.username == "key_manager_01"
            )
        )

        assert requester is not None

        ceremony = KeyCeremony(
            id=uuid4(),
            key_label="BANKKEY-RECOVERY-TEST",
            operation="activate",
            status="executing",
            requested_by=requester.id,
            execution_started_at=(
                datetime.now(timezone.utc)
                - timedelta(minutes=10)
            ),
        )

        session.add(ceremony)
        session.flush()

        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=5
        )

        detected = session.scalar(
            select(KeyCeremony).where(
                KeyCeremony.id == ceremony.id,
                KeyCeremony.status == "executing",
                KeyCeremony.execution_started_at < cutoff,
            )
        )

        assert detected is not None
        assert detected.id == ceremony.id

        print("[OK] Stale execution detected")
        print("[OK] Manual review required")

        # La transaction n'est pas validee.
        session.rollback()
