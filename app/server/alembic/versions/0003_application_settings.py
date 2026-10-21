# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

"""Store application preferences in the active database.

Revision ID: 0003_application_settings
Revises: 0002_rename_relative_preference
Create Date: 2026-10-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_application_settings"
down_revision: Union[str, Sequence[str], None] = "0002_rename_relative_preference"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


###############################################################################
def upgrade() -> None:
    op.create_table(
        "application_settings",
        sa.Column("settings_id", sa.Integer(), nullable=False),
        sa.Column("jobs", sa.JSON(), nullable=False),
        sa.Column("device", sa.JSON(), nullable=False),
        sa.Column("roulette", sa.JSON(), nullable=False),
        sa.CheckConstraint("settings_id = 1", name="ck_application_settings_singleton"),
        sa.PrimaryKeyConstraint("settings_id"),
    )


###############################################################################
def downgrade() -> None:
    op.drop_table("application_settings")
