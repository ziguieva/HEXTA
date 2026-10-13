import pytest
from sqlalchemy import select

from app.core.database import create_database_session
from app.models.key_inventory import ManagedKey


@pytest.mark.integration
def test_registered_key_identity():
    SessionLocal = create_database_session()

    with SessionLocal() as session:
        keys = session.scalars(
            select(ManagedKey).where(
                ManagedKey.token_label == "BANKKEY-PAYMENT-LAB",
                ManagedKey.key_id == "01",
            )
        ).all()

        assert len(keys) == 1

        key = keys[0]

        assert key.key_label == "BANKKEY-AES-001"
        assert key.algorithm == "AES-256"
        assert key.status == "created"

        print("[OK] Unique cryptographic key identity")
        print("[OK] Token and PKCS11 ID verified")
        print("[OK] Lifecycle status verified")
