import os
from pathlib import Path

import pkcs11
from pkcs11 import Attribute, ObjectClass


TOKEN_LABEL = "BANKKEY-PAYMENT-LAB"


def list_hsm_keys(user_pin: str):
    config = Path.home() / ".bankkey-hsm" / "softhsm2.conf"
    module = (
        Path("/opt/homebrew/opt/softhsm")
        / "lib/softhsm/libsofthsm2.so"
    )

    os.environ["SOFTHSM2_CONF"] = str(config)

    library = pkcs11.lib(str(module))
    token = library.get_token(token_label=TOKEN_LABEL)

    keys = []

    with token.open(user_pin=user_pin) as session:
        objects = session.get_objects({
            Attribute.CLASS: ObjectClass.SECRET_KEY
        })

        for key in objects:
            label = key[Attribute.LABEL]
            key_id = key[Attribute.ID]

            keys.append({
                "label": label,
                "id": bytes(key_id).hex(),
                "type": "SECRET_KEY",
                "sensitive": bool(key[Attribute.SENSITIVE]),
                "extractable": bool(key[Attribute.EXTRACTABLE]),
            })

    return keys


if __name__ == "__main__":
    from getpass import getpass

    pin = getpass("User PIN SoftHSM2 : ")

    for key in list_hsm_keys(pin):
        print(key)
