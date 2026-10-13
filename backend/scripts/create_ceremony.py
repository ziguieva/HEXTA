from app.services.ceremony_repository import (
    create_ceremony_request,
)


def main():
    print("=== BANKKEY HSM | CEREMONY REQUEST ===")

    result = create_ceremony_request(
        username="key_manager_01",
        key_label="BANKKEY-AES-001",
        operation="activate",
    )

    for field, value in result.items():
        print(f"{field}: {value}")

    print("[OK] Ceremony stored in PostgreSQL")


if __name__ == "__main__":
    main()
