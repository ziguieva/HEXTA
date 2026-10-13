"""Authenticated laboratory ceremony actions.

The final HSM operation is intentionally disabled over HTTP. Reserve/finalize
must run through a separately authenticated local operator process.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import create_database_session
from app.core.web_auth import get_current_user
from app.models.database import CeremonyApproval, KeyCeremony, User
from app.models.key_inventory import ManagedKey, KeyStatus
from app.services.ceremony_approval_service import (
    CeremonyApprovalError,
    approve_ceremony_request,
)
from app.services.ceremony_execution_service import (
    CeremonyExecutionError,
    verify_execution_authorization,
)

router = APIRouter(prefix="/api/v1/ceremonies", tags=["Ceremony Actions"])


class CreateCeremonyBody(BaseModel):
    key_label: str = Field(min_length=1, max_length=100)
    operation: str = "activate"


def require_role(actor: dict, role: str) -> None:
    if actor.get("role") != role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires the {role} role",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_ceremony(
    body: CreateCeremonyBody,
    actor: dict = Depends(get_current_user),
):
    require_role(actor, "key_manager")
    key_label = body.key_label.strip()
    if not key_label or body.operation != "activate":
        raise HTTPException(status_code=422, detail="Only activation is supported")

    SessionLocal = create_database_session()
    with SessionLocal.begin() as session:
        # A key row lock serializes competing requests for the same asset.
        keys = session.scalars(
            select(ManagedKey)
            .where(ManagedKey.key_label == key_label)
            .with_for_update()
        ).all()
        if len(keys) != 1:
            raise HTTPException(
                status_code=409,
                detail="Expected exactly one registered key with this label",
            )
        if keys[0].status != KeyStatus.CREATED.value:
            raise HTTPException(
                status_code=409,
                detail="Only keys in CREATED state can be activated",
            )
        existing = session.scalar(
            select(KeyCeremony.id).where(
                KeyCeremony.key_label == key_label,
                KeyCeremony.operation == "activate",
                KeyCeremony.status.in_(["pending", "approved", "executing"]),
            ).limit(1)
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="An activation ceremony is already in progress",
            )

        requester = session.get(User, UUID(actor["id"]))
        if (
            requester is None
            or not requester.is_active
            or requester.role != "key_manager"
        ):
            raise HTTPException(status_code=403, detail="Requester not authorized")

        ceremony = KeyCeremony(
            key_label=key_label,
            operation="activate",
            status="pending",
            requested_by=requester.id,
        )
        session.add(ceremony)
        session.flush()
        return {
            "id": str(ceremony.id),
            "key_label": ceremony.key_label,
            "operation": ceremony.operation,
            "status": ceremony.status,
            "requested_by": requester.username,
        }


@router.post("/{ceremony_id}/approve")
def approve_ceremony(
    ceremony_id: UUID,
    actor: dict = Depends(get_current_user),
):
    require_role(actor, "security_officer")
    try:
        # Service locks ceremony row and checks self-approval and role.
        return approve_ceremony_request(str(ceremony_id), actor["username"])
    except CeremonyApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{ceremony_id}/reject")
def reject_ceremony(
    ceremony_id: UUID,
    actor: dict = Depends(get_current_user),
):
    require_role(actor, "security_officer")
    SessionLocal = create_database_session()
    with SessionLocal.begin() as session:
        ceremony = session.scalar(
            select(KeyCeremony)
            .where(KeyCeremony.id == ceremony_id)
            .with_for_update()
        )
        if ceremony is None:
            raise HTTPException(status_code=404, detail="Ceremony not found")
        if ceremony.status != "pending":
            raise HTTPException(status_code=409, detail="Ceremony is not pending")

        officer = session.get(User, UUID(actor["id"]))
        if (
            officer is None
            or not officer.is_active
            or officer.role != "security_officer"
            or officer.id == ceremony.requested_by
        ):
            raise HTTPException(status_code=403, detail="Officer not authorized")

        approval = CeremonyApproval(
            ceremony_id=ceremony.id,
            approved_by=officer.id,
            decision="rejected",
        )
        session.add(approval)
        ceremony.status = "rejected"
        session.flush()
        return {
            "ceremony_id": str(ceremony.id),
            "status": ceremony.status,
            "rejected_by": officer.username,
        }


@router.post("/{ceremony_id}/execution-check")
def check_execution(
    ceremony_id: UUID,
    actor: dict = Depends(get_current_user),
):
    require_role(actor, "hsm_operator")
    try:
        return verify_execution_authorization(
            str(ceremony_id), actor["username"]
        )
    except CeremonyExecutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
