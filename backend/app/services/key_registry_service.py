from sqlalchemy import select

from app.core.database import create_database_session
from app.models.key_inventory import ManagedKey, KeyStatus


class KeyRegistryError(Exception):
    pass


def register_existing_key(
    token_label: str,
    key_id: str,
    key_label: str,
    algorithm: str,
):
    if not all([
        token_label.strip(),
        key_id.strip(),
        key_label.strip(),
        algorithm.strip(),
    ]):
        raise KeyRegistryError("Missing key metadata")

    SessionLocal = create_database_session()

    with SessionLocal.begin() as session:
        existing = session.scalar(
            select(ManagedKey).where(
                ManagedKey.token_label == token_label,
                ManagedKey.key_id == key_id,
            )
        )

        if existing:
            raise KeyRegistryError(
                "Key already registered"
            )

        key = ManagedKey(
            token_label=token_label,
            key_id=key_id,
            key_label=key_label,
            algorithm=algorithm,
            status=KeyStatus.CREATED.value,
        )

        session.add(key)
        session.flush()

        return {
            "id": str(key.id),
            "token_label": key.token_label,
            "key_id": key.key_id,
            "key_label": key.key_label,
            "algorithm": key.algorithm,
            "status": key.status,
        }
