import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker


def get_database_url():
    password = os.environ.get("BANKKEY_DB_PASSWORD")

    if not password:
        raise RuntimeError(
            "BANKKEY_DB_PASSWORD is not configured"
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username="bankkey",
        password=password,
        host="127.0.0.1",
        port=5433,
        database="bankkey",
    )


def create_database_session():
    engine = create_engine(
        get_database_url(),
        pool_pre_ping=True,
    )

    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
