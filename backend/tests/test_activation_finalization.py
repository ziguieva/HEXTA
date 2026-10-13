from uuid import UUID

import pytest

from app.services.activation_finalization_service import (
    ActivationFinalizationError,
    finalize_activation,
)


CEREMONY_ID = "ca812b4f-ef08-4998-a9bc-bd9ffe36cd3c"

OPERATOR_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)


def test_finalization_without_hsm_authentication():
    with pytest.raises(
        ActivationFinalizationError,
        match="HSM authentication required",
    ):
        finalize_activation(
            ceremony_id=CEREMONY_ID,
            operator_id=OPERATOR_ID,
            user_pin="",
        )


def test_invalid_ceremony_identifier():
    with pytest.raises(
        ActivationFinalizationError,
        match="Invalid ceremony identifier",
    ):
        finalize_activation(
            ceremony_id="invalid-uuid",
            operator_id=OPERATOR_ID,
            user_pin="dummy-test-pin",
        )


@pytest.mark.integration
def test_finalization_without_reservation():
    with pytest.raises(
        ActivationFinalizationError,
        match="Ceremony is not executing",
    ):
        finalize_activation(
            ceremony_id=CEREMONY_ID,
            operator_id=OPERATOR_ID,
            user_pin="dummy-test-pin",
        )
