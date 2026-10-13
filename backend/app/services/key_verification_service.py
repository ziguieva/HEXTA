import os
from pathlib import Path

import pkcs11
from pkcs11 import Attribute, KeyType, ObjectClass
from sqlalchemy import select

from app.core.database import create_database_session
from app.models.key_inventory import ManagedKey


class KeyVerificationError(Exception):
    pass


def verify_registered_key(key_label: str, user_pin: str):
    if not user_pin:
        raise KeyVerificationError("HSM authentication required")

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        records = session.scalars(
            select(ManagedKey).where(
                ManagedKey.key_label == key_label
            )
        ).all()

        if len(records) != 1:
            raise KeyVerificationError(
                "Expected exactly one registered key"
            )

        record = records[0]

        metadata = {
            "token_label": record.token_label,
            "key_id": record.key_id,
            "key_label": record.key_label,
            "algorithm": record.algorithm,
            "status": record.status,
        }

    if metadata["algorithm"] != "AES-256":
        raise KeyVerificationError("Unsupported algorithm")

    try:
        key_id = bytes.fromhex(metadata["key_id"])
    except ValueError as exc:
        raise KeyVerificationError(
            "Invalid PKCS11 key identifier"
        ) from exc

    config = Path.home() / ".bankkey-hsm" / "softhsm2.conf"

    module = (
        Path("/opt/homebrew/opt/softhsm")
        / "lib/softhsm/libsofthsm2.so"
    )

    if not config.is_file() or not module.is_file():
        raise KeyVerificationError(
            "SoftHSM2 configuration unavailable"
        )

    os.environ["SOFTHSM2_CONF"] = str(config)

    try:
        library = pkcs11.lib(str(module))

        token = library.get_token(
            token_label=metadata["token_label"]
        )

        with token.open(user_pin=user_pin) as hsm_session:
            matches = list(
                hsm_session.get_objects({
                    Attribute.CLASS: ObjectClass.SECRET_KEY,
                    Attribute.KEY_TYPE: KeyType.AES,
                    Attribute.ID: key_id,
                })
            )

            if len(matches) != 1:
                raise KeyVerificationError(
                    "Expected exactly one HSM key"
                )

            key = matches[0]

            if key[Attribute.LABEL] != metadata["key_label"]:
                raise KeyVerificationError(
                    "HSM key label mismatch"
                )

            if key[Attribute.VALUE_LEN] != 32:
                raise KeyVerificationError(
                    "Invalid AES-256 key length"
                )

            if not bool(key[Attribute.SENSITIVE]):
                raise KeyVerificationError(
                    "Key must be sensitive"
                )

            if bool(key[Attribute.EXTRACTABLE]):
                raise KeyVerificationError(
                    "Key must not be extractable"
                )

    except pkcs11.PKCS11Error as exc:
        raise KeyVerificationError(
            "PKCS11 verification failed"
        ) from exc

    return {
        "token_label": metadata["token_label"],
        "key_id": metadata["key_id"],
        "key_label": metadata["key_label"],
        "algorithm": metadata["algorithm"],
        "lifecycle_status": metadata["status"],
        "hsm_verified": True,
        "key_length_bits": 256,
        "sensitive": True,
        "extractable": False,
    }
