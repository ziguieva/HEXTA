import os
import secrets
from pathlib import Path

import pkcs11
from pkcs11 import KeyType, Mechanism, ObjectClass


TOKEN_LABEL = "BANKKEY-PAYMENT-LAB"
KEY_LABEL = "BANKKEY-AES-001"


def get_pkcs11_library():
    config = Path.home() / ".bankkey-hsm" / "softhsm2.conf"
    os.environ["SOFTHSM2_CONF"] = str(config)

    module = (
        Path("/opt/homebrew/opt/softhsm")
        / "lib/softhsm/libsofthsm2.so"
    )

    if not module.is_file():
        raise RuntimeError("Module SoftHSM2 introuvable")

    return pkcs11.lib(str(module))


def main():
    print("=== BANKKEY HSM | AES-256-CBC TEST ===")

    user_pin = os.environ.get("BANKKEY_USER_PIN")

    if not user_pin:
        raise RuntimeError(
            "Variable BANKKEY_USER_PIN absente"
        )

    library = get_pkcs11_library()
    token = library.get_token(token_label=TOKEN_LABEL)

    with token.open(user_pin=user_pin) as session:

        print("[OK] Connexion au token SoftHSM2")

        key = session.get_key(
            label=KEY_LABEL,
            object_class=ObjectClass.SECRET_KEY,
            key_type=KeyType.AES,
        )

        print("[OK] Cle AES-256 localisee")

        plaintext = b"BANKKEY-PAYMENT-TEST-001"

        # IV aleatoire de 128 bits pour AES-CBC.
        iv = secrets.token_bytes(16)

        ciphertext = key.encrypt(
            plaintext,
            mechanism=Mechanism.AES_CBC_PAD,
            mechanism_param=iv,
        )

        print("[OK] Chiffrement AES-256-CBC execute")
        print("Ciphertext:", bytes(ciphertext).hex())

        recovered = key.decrypt(
            ciphertext,
            mechanism=Mechanism.AES_CBC_PAD,
            mechanism_param=iv,
        )

        if bytes(recovered) != plaintext:
            raise AssertionError(
                "ECHEC : le message dechiffre est incorrect"
            )

        print("[OK] Dechiffrement reussi")
        print("[OK] Message original retrouve")
        print("[OK] Cle conservee dans SoftHSM2")

    print("=== TEST CRYPTOGRAPHIQUE REUSSI ===")


if __name__ == "__main__":
    main()
