from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class CeremonyError(Exception):
    pass


class CeremonyState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


@dataclass(frozen=True)
class CeremonyActor:
    user_id: UUID
    role: str
    is_active: bool = True


@dataclass
class Ceremony:
    requested_by: UUID
    key_label: str
    operation: str
    state: CeremonyState = CeremonyState.PENDING
    approved_by: UUID | None = None
    executed_by: UUID | None = None


def approve_ceremony(
    ceremony: Ceremony,
    actor: CeremonyActor,
) -> None:

    if not actor.is_active:
        raise CeremonyError("Inactive account")

    if actor.role != "security_officer":
        raise CeremonyError("Insufficient permissions")

    if actor.user_id == ceremony.requested_by:
        raise CeremonyError("Self-approval forbidden")

    if ceremony.state != CeremonyState.PENDING:
        raise CeremonyError("Ceremony is not pending")

    ceremony.approved_by = actor.user_id
    ceremony.state = CeremonyState.APPROVED


def execute_ceremony(
    ceremony: Ceremony,
    actor: CeremonyActor,
) -> None:

    if not actor.is_active:
        raise CeremonyError("Inactive account")

    if actor.role != "hsm_operator":
        raise CeremonyError("Execution permission denied")

    if actor.user_id in {
        ceremony.requested_by,
        ceremony.approved_by,
    }:
        raise CeremonyError("Separation of duties violation")

    if ceremony.state != CeremonyState.APPROVED:
        raise CeremonyError("Ceremony not approved")

    ceremony.executed_by = actor.user_id
    ceremony.state = CeremonyState.EXECUTED
