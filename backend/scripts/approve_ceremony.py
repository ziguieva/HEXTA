from getpass import getpass

from app.services.auth_service import authenticate_user
from app.services.ceremony_approval_service import (
    CeremonyApprovalError,
    approve_ceremony_request,
)


CEREMONY_ID = "ca812b4f-ef08-4998-a9bc-bd9ffe36cd3c"


def main():
    print("=== BANKKEY HSM | CEREMONY APPROVAL ===")

    username = input("Username: ").strip()
    password = getpass("Password: ")

    user = authenticate_user(username, password)

    if user is None:
        print("[DENIED] Authentication failed")
        return

    try:
        result = approve_ceremony_request(
            ceremony_id=CEREMONY_ID,
            approver_username=user["username"],
        )

        print("[OK] Ceremony approved")
        print("Ceremony ID:", result["ceremony_id"])
        print("Key:", result["key_label"])
        print("Status:", result["status"])
        print("Approved by:", result["approved_by"])

    except CeremonyApprovalError as error:
        print("[DENIED]", str(error))


if __name__ == "__main__":
    main()
