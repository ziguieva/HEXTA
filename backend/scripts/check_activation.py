from getpass import getpass

from sqlalchemy import select

from app.core.database import create_database_session
from app.models.database import User
from app.services.auth_service import authenticate_user
from app.services.key_activation_service import (
    KeyActivationError,
    validate_key_activation,
)


CEREMONY_ID = "ca812b4f-ef08-4998-a9bc-bd9ffe36cd3c"


def main():
    print("=== BANKKEY HSM | ACTIVATION PREVALIDATION ===")

    username = input("Username: ").strip()
    password = getpass("Password: ")

    authenticated = authenticate_user(username, password)

    if authenticated is None:
        print("[DENIED] Authentication failed")
        return

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        operator = session.scalar(
            select(User).where(User.username == username)
        )

        operator_id = operator.id

    try:
        result = validate_key_activation(
            ceremony_id=CEREMONY_ID,
            operator_id=operator_id,
        )

        for field, value in result.items():
            print(f"{field}: {value}")

        print("[OK] Activation prevalidation successful")

    except KeyActivationError as error:
        print("[DENIED]", str(error))


if __name__ == "__main__":
    main()
