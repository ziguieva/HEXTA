from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.core.database import create_database_session
from app.core.web_auth import get_current_user
from app.models.key_inventory import ManagedKey


router = APIRouter(
    prefix="/api/v1/keys",
    tags=["Key Inventory"],
)


class KeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    token_label: str
    key_id: str
    key_label: str
    algorithm: str
    status: str
    created_at: datetime
    activated_at: datetime | None
    revoked_at: datetime | None


@router.get("", response_model=list[KeyResponse])
def list_keys(user=Depends(get_current_user)):
    SessionLocal = create_database_session()

    with SessionLocal() as session:
        keys = session.scalars(
            select(ManagedKey).order_by(
                ManagedKey.created_at.desc(),
                ManagedKey.id,
            )
        ).all()

        return [
            KeyResponse.model_validate(key)
            for key in keys
        ]
