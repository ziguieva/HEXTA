from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core.database import get_database_url


@pytest.mark.integration
def test_prevent_two_executions_for_same_key():
    engine = create_engine(get_database_url())

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                user_id = connection.execute(
                    text("""
                        SELECT id
                        FROM users
                        WHERE username = 'key_manager_01'
                    """)
                ).scalar_one()

                key_label = "BANKKEY-CONCURRENCY-TEST"

                def insert_ceremony():
                    connection.execute(
                        text("""
                            INSERT INTO key_ceremonies (
                                id,
                                key_label,
                                operation,
                                status,
                                requested_by,
                                created_at
                            )
                            VALUES (
                                :id,
                                :key_label,
                                'activate',
                                'executing',
                                :requested_by,
                                NOW()
                            )
                        """),
                        {
                            "id": uuid4(),
                            "key_label": key_label,
                            "requested_by": user_id,
                        },
                    )

                # Premiere execution : autorisee.
                insert_ceremony()

                # Seconde execution : doit etre refusee.
                savepoint = connection.begin_nested()

                try:
                    insert_ceremony()
                except IntegrityError as exc:
                    savepoint.rollback()

                    assert (
                        exc.orig.sqlstate == "23505"
                    ), "Expected PostgreSQL unique violation"

                    print(
                        "[OK] Duplicate execution rejected"
                    )
                else:
                    savepoint.rollback()
                    pytest.fail(
                        "Security failure: duplicate accepted"
                    )

            finally:
                transaction.rollback()

    finally:
        engine.dispose()
