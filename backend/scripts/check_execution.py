from getpass import getpass

from app.services.auth_service import authenticate_user
from app.services.ceremony_execution_service import (
    CeremonyExecutionError,
    verify_execution_authorization,
)


CEREMONY_ID = "ca812b4f-ef08-4998-a9bc-bd9ffe36cd3c"


def main():
    print("=== BANKKEY HSM | EXECUTION AUTHORIZATION ===")

    username = input("Username: ").strip()
    password = getpass("Password: ")

    user = authenticate_user(username, password)

    if user is None:
        print("[DENIED] Authentication failed")
        return

    try:
        result = verify_execution_authorization(
            ceremony_id=CEREMONY_ID,
            operator_username=user["username"],
        )

        print("[OK] Execution authorization verified")
        print("Ceremony:", result["ceremony_id"])
        print("Key:", result["key_label"])
        print("Operator:", result["operator"])
        print("Authorized:", result["authorized"])

    except CeremonyExecutionError as exc:
        print("[DENIED]", str(exc))


if __name__ == "__main__":
    main()
