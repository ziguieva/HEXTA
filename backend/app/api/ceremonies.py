from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import create_database_session
from app.core.web_auth import get_current_user
from app.models.database import (
    CeremonyApproval,
    KeyCeremony,
    User,
)


router = APIRouter(
    prefix="/api/v1/ceremonies",
    tags=["Key Ceremonies"],
)


class ApprovalResponse(BaseModel):
    approved_by: str
    decision: str
    created_at: datetime


class CeremonyResponse(BaseModel):
    id: UUID
    key_label: str
    operation: str
    status: str
    requested_by: str
    created_at: datetime
    execution_started_at: datetime | None
    executed_at: datetime | None
    executed_by: str | None
    approvals: list[ApprovalResponse]


@router.get("", response_model=list[CeremonyResponse])
def list_ceremonies(user=Depends(get_current_user)):
    SessionLocal = create_database_session()

    with SessionLocal() as session:
        query = select(KeyCeremony)

        # Un Key Manager ne consulte que ses demandes.
        # Les autres roles de supervision du laboratoire
        # peuvent consulter les ceremonies.
        if user["role"] == "key_manager":
            query = query.where(
                KeyCeremony.requested_by == UUID(user["id"])
            )

        ceremonies = session.scalars(
            query.order_by(
                KeyCeremony.created_at.desc(),
                KeyCeremony.id,
            )
        ).all()

        if not ceremonies:
            return []

        user_ids = set()
        ceremony_ids = []

        for ceremony in ceremonies:
            ceremony_ids.append(ceremony.id)
            user_ids.add(ceremony.requested_by)

            if ceremony.executed_by:
                user_ids.add(ceremony.executed_by)

        approvals = session.scalars(
            select(CeremonyApproval).where(
                CeremonyApproval.ceremony_id.in_(
                    ceremony_ids
                )
            )
        ).all()

        for approval in approvals:
            user_ids.add(approval.approved_by)

        users = session.scalars(
            select(User).where(User.id.in_(user_ids))
        ).all()

        usernames = {
            account.id: account.username
            for account in users
        }

        approvals_by_ceremony = {
            ceremony_id: []
            for ceremony_id in ceremony_ids
        }

        for approval in approvals:
            approvals_by_ceremony[
                approval.ceremony_id
            ].append(
                ApprovalResponse(
                    approved_by=usernames.get(
                        approval.approved_by,
                        "unknown",
                    ),
                    decision=approval.decision,
                    created_at=approval.created_at,
                )
            )

        results = []

        for ceremony in ceremonies:
            results.append(
                CeremonyResponse(
                    id=ceremony.id,
                    key_label=ceremony.key_label,
                    operation=ceremony.operation,
                    status=ceremony.status,
                    requested_by=usernames.get(
                        ceremony.requested_by,
                        "unknown",
                    ),
                    created_at=ceremony.created_at,
                    execution_started_at=(
                        ceremony.execution_started_at
                    ),
                    executed_at=ceremony.executed_at,
                    executed_by=(
                        usernames.get(
                            ceremony.executed_by,
                            "unknown",
                        )
                        if ceremony.executed_by
                        else None
                    ),
                    approvals=(
                        approvals_by_ceremony[ceremony.id]
                    ),
                )
            )

        return results
