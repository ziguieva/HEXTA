from getpass import getpass

from sqlalchemy import select

from app.core.database import create_database_session
from app.core.password_security import hash_password
from app.core.rbac import Role
from app.models.database import User


def main():
    print("=== BANKKEY HSM | USER PROVISIONING ===")

    username = input("Username: ").strip()

    if not username or len(username) > 100:
        raise ValueError("Invalid username")

    print("\nAvailable roles:")
    for role in Role:
        print(f" - {role.value}")

    role_name = input("\nRole: ").strip()

    try:
        role = Role(role_name)
    except ValueError as exc:
        raise ValueError("Invalid role") from exc

    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")

    if password != confirmation:
        raise ValueError("Passwords do not match")

    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")

    SessionLocal = create_database_session()

    with SessionLocal() as session:
        existing = session.scalar(
            select(User).where(User.username == username)
        )

        if existing:
            raise ValueError("Username already exists")

        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role.value,
            is_active=True,
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        print("\n[OK] User created successfully")
        print("User ID :", user.id)
        print("Username:", user.username)
        print("Role    :", user.role)
        print("Active  :", user.is_active)


if __name__ == "__main__":
    main()
