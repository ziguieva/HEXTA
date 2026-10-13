"""Prevent concurrent key executions.

Revision ID: 3f4b37bacbe3
Revises: e80dd8ea16f1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3f4b37bacbe3"
down_revision: Union[str, Sequence[str], None] = "e80dd8ea16f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_executing_ceremony_per_key",
        "key_ceremonies",
        ["key_label"],
        unique=True,
        postgresql_where=sa.text(
            "status = 'executing'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_executing_ceremony_per_key",
        table_name="key_ceremonies",
    )
