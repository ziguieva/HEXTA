"""Audit views. SHA chain is checked over ALL records, never a filtered subset."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from app.core.database import create_database_session
from app.core.web_auth import get_current_user
from app.services.audit_service import verify_chain

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Center"])


def allow(actor):
    if actor.get("role") not in ("auditor", "security_officer"):
        raise HTTPException(403, "Audit access requires auditor or security_officer")


@router.get("")
def get_audit(limit: int = 100, actor: dict = Depends(get_current_user)):
    allow(actor)
    if limit < 1 or limit > 500:
        raise HTTPException(422, "Limit must be between 1 and 500")
    SessionLocal = create_database_session()
    with SessionLocal() as session:
        # Snapshot ensures verification and returned subset are consistent.
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        rows = [dict(row) for row in session.execute(text(
            "SELECT seq, occurred_at, entity_type, entity_id, event_type, actor_id, "
            "old_status, new_status, prev_hash, event_hash "
            "FROM bankkey_audit_events ORDER BY seq ASC"
        )).mappings()]
        result = verify_chain(rows)
        latest = list(reversed(rows[-limit:]))
        return {"integrity": result, "total": len(rows), "events": latest,
                "historical_note": "Audit capture began at migration v0.7; earlier business records are not backfilled."}
