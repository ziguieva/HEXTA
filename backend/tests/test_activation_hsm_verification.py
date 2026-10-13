import os

import pytest

from app.services.key_verification_service import (
    verify_registered_key,
)


@pytest.mark.integration
def test_hsm_key_verification_before_activation():
    user_pin = os.environ.get("BANKKEY_USER_PIN")

    if not user_pin:
        pytest.skip("BANKKEY_USER_PIN not configured")

    result = verify_registered_key(
        key_label="BANKKEY-AES-001",
        user_pin=user_pin,
    )

    assert result["hsm_verified"] is True
    assert result["key_length_bits"] == 256
    assert result["sensitive"] is True
    assert result["extractable"] is False
    assert result["lifecycle_status"] == "created"

    print("[OK] HSM key verified before activation")
