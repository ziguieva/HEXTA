from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import create_database_session
from app.models.database import KeyCeremony


class ExecutionRecoveryService:
    TIMEOUT_MINUTES = 5

    def find_stale_executions(self):
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=self.TIMEOUT_MINUTES
        )

        SessionLocal = create_database_session()

        with SessionLocal() as session:
            ceremonies = session.scalars(
                select(KeyCeremony).where(
                    KeyCeremony.status == "executing",
                    KeyCeremony.execution_started_at < cutoff,
                )
            ).all()

            return [
                {
                    "ceremony_id": str(ceremony.id),
                    "key_label": ceremony.key_label,
                    "status": ceremony.status,
                    "execution_started_at": (
                        ceremony.execution_started_at.isoformat()
                    ),
                    "recovery_action": "manual_review_required",
                }
                for ceremony in ceremonies
            ]


if __name__ == "__main__":
    service = ExecutionRecoveryService()
    stale = service.find_stale_executions()

    print("=== BANKKEY HSM | RECOVERY DIAGNOSTIC ===")
    print("Stale executions:", len(stale))

    for ceremony in stale:
        print(ceremony)

    print("[OK] Recovery diagnostic completed")
