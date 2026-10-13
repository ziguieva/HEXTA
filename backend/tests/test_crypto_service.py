import os

import pytest

from app.services.crypto_service import get_pkcs11_library
from pkcs11 import KeyType, Mechanism, ObjectClass


@pytest.mark.integration
def test_aes256_encrypt_decrypt():

    user_pin = os.environ.get("BANKKEY_USER_PIN")

    if not user_pin:
        pytest.skip("BANKKEY_USER_PIN non defini")

    library = get_pkcs11_library()

    token = library.get_token(
        token_label="BANKKEY-PAYMENT-LAB"
    )

    with token.open(user_pin=user_pin) as session:

        key = session.get_key(
            label="BANKKEY-AES-001",
            object_class=ObjectClass.SECRET_KEY,
            key_type=KeyType.AES,
        )

        plaintext = b"BANKKEY-INTEGRATION-TEST"

        iv = os.urandom(16)

        ciphertext = key.encrypt(
            plaintext,
            mechanism=Mechanism.AES_CBC_PAD,
            mechanism_param=iv,
        )

        assert bytes(ciphertext) != plaintext

        recovered = key.decrypt(
            ciphertext,
            mechanism=Mechanism.AES_CBC_PAD,
            mechanism_param=iv,
        )

        assert bytes(recovered) == plaintext
