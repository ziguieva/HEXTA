from getpass import getpass

from app.services.key_verification_service import (
    verify_registered_key,
)


def main():
    print("=== BANKKEY HSM | KEY VERIFICATION ===")

    user_pin = getpass("SoftHSM2 User PIN: ")

    result = verify_registered_key(
        key_label="BANKKEY-AES-001",
        user_pin=user_pin,
    )

    for field, value in result.items():
        print(f"{field}: {value}")

    print("[OK] PostgreSQL and SoftHSM2 metadata verified")


if __name__ == "__main__":
    main()
