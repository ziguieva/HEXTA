import os
from pathlib import Path

import pkcs11


TOKEN_LABEL = "BANKKEY-PAYMENT-LAB"


def get_hsm_status():
    config = Path.home() / ".bankkey-hsm" / "softhsm2.conf"
    module = (
        Path("/opt/homebrew/opt/softhsm")
        / "lib/softhsm/libsofthsm2.so"
    )

    if not config.is_file() or not module.is_file():
        return {
            "status": "unavailable",
            "token_connected": False,
            "token_label": TOKEN_LABEL,
        }

    try:
        os.environ["SOFTHSM2_CONF"] = str(config)

        library = pkcs11.lib(str(module))
        token = library.get_token(token_label=TOKEN_LABEL)

        return {
            "status": "operational",
            "token_connected": True,
            "token_label": token.label.strip(),
            "provider": "SoftHSM2",
            "environment": "laboratory",
        }

    except (pkcs11.PKCS11Error, LookupError, OSError):
        return {
            "status": "unavailable",
            "token_connected": False,
            "token_label": TOKEN_LABEL,
        }
