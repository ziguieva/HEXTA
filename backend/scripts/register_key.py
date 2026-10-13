from app.services.key_registry_service import (
    register_existing_key,
)


def main():
    print("=== BANKKEY HSM | KEY REGISTRATION ===")

    result = register_existing_key(
        token_label="BANKKEY-PAYMENT-LAB",
        key_id="01",
        key_label="BANKKEY-AES-001",
        algorithm="AES-256",
    )

    for field, value in result.items():
        print(f"{field}: {value}")

    print("[OK] Key metadata registered in PostgreSQL")


if __name__ == "__main__":
    main()
