from getpass import getpass
from uuid import UUID

from sqlalchemy import select

from app.core.database import create_database_session
from app.models.database import User
from app.services.auth_service import authenticate_user
from app.services.key_activation_service import (
    validate_key_activation,
)
from app.services.key_verification_service import (
    verify_registered_key,
)
from app.services.activation_reservation_service import (
    reserve_activation,
)
from app.services.activation_finalization_service import (
    finalize_activation,
)


CEREMONY_ID = (
    "ca812b4f-ef08-4998-a9bc-bd9ffe36cd3c"
)


def main():
    print("\n=== BANKKEY HSM | EXECUTION ENGINE ===")

    username = input("Operator username: ").strip()
    password = getpass("Operator password: ")

    authenticated = authenticate_user(
        username, password
    )

    del password

    if authenticated is None:
        raise SystemExit(
            "[DENIED] Authentication failed"
        )

    if authenticated["role"] != "hsm_operator":
        raise SystemExit(
            "[DENIED] HSM Operator role required"
        )

    operator_id = UUID(authenticated["id"])

    print("[OK] Operator authenticated")

    result = validate_key_activation(
        ceremony_id=CEREMONY_ID,
        operator_id=operator_id,
    )

    print("[OK] Ceremony authorization verified")
    print("Key:", result["key_label"])
    print("Current state:", result["current_status"])
    print("Target state:", result["target_status"])

    pin = getpass("SoftHSM2 User PIN: ")

    if not pin:
        raise SystemExit(
            "[DENIED] HSM PIN required"
        )

    hsm_result = verify_registered_key(
        key_label=result["key_label"],
        user_pin=pin,
    )

    if not hsm_result["hsm_verified"]:
        raise SystemExit(
            "[DENIED] HSM verification failed"
        )

    print("[OK] SoftHSM2 key verified")

    confirmation = input(
        "\nType ACTIVATE to execute ceremony: "
    ).strip()

    if confirmation != "ACTIVATE":
        print("[CANCELLED] No changes performed")
        return

    reservation_completed = False

    try:
        reservation = reserve_activation(
            ceremony_id=CEREMONY_ID,
            operator_id=operator_id,
        )

        reservation_completed = True

        print(
            "[OK] Ceremony reserved:",
            reservation["ceremony_status"],
        )

        final_result = finalize_activation(
            ceremony_id=CEREMONY_ID,
            operator_id=operator_id,
            user_pin=pin,
        )

        print("\n=== ACTIVATION RESULT ===")

        for field, value in final_result.items():
            print(f"{field}: {value}")

        print("\n[SUCCESS] Ceremony completed")

    except Exception:
        if reservation_completed:
            print(
                "\n[WARNING] Execution interrupted."
            )
            print(
                "Ceremony may remain EXECUTING."
            )
            print(
                "Manual reconciliation is required."
            )
        raise

    finally:
        pin = None


if __name__ == "__main__":
    main()
