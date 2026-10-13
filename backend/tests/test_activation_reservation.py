from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.database import create_database_session
from app.models.database import User
from app.services.activation_reservation_service import (
    ActivationReservationError,
    reserve_activation,
)


@pytest.mark.integration
def test_unknown_ceremony_is_rejected():
    SessionLocal = create_database_session()

    with SessionLocal() as session:
        operator = session.scalar(
            select(User).where(
                User.username == "hsm_operator_01"
            )
        )

        assert operator is not None

        unknown_ceremony_id = str(uuid4())

        with pytest.raises(
            ActivationReservationError,
            match="Ceremony not found",
        ):
            reserve_activation(
                ceremony_id=unknown_ceremony_id,
                operator_id=operator.id,
            )
