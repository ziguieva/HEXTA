from sqlalchemy import select

from app.core.database import create_database_session
from app.core.password_security import verify_password
from app.models.database import User


def authenticate_user(username: str, password: str):
    SessionLocal = create_database_session()

    with SessionLocal() as session:
        user = session.scalar(
            select(User).where(User.username == username)
        )

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
        }
