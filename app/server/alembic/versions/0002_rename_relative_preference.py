"""Rename inference confidence to relative preference.

Revision ID: 0002_rename_relative_preference
Revises: 0001_initial_schema
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_rename_relative_preference"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


###############################################################################
def upgrade() -> None:
    with op.batch_alter_table("inference_session_steps") as batch_op:
        batch_op.drop_constraint("ck_inference_steps_confidence", type_="check")
        batch_op.alter_column(
            "predicted_confidence",
            new_column_name="predicted_relative_preference",
        )
        batch_op.create_check_constraint(
            "ck_inference_steps_relative_preference",
            "predicted_relative_preference IS NULL OR "
            "(predicted_relative_preference >= 0 AND "
            "predicted_relative_preference <= 1)",
        )


###############################################################################
def downgrade() -> None:
    with op.batch_alter_table("inference_session_steps") as batch_op:
        batch_op.drop_constraint(
            "ck_inference_steps_relative_preference", type_="check"
        )
        batch_op.alter_column(
            "predicted_relative_preference",
            new_column_name="predicted_confidence",
        )
        batch_op.create_check_constraint(
            "ck_inference_steps_confidence",
            "predicted_confidence IS NULL OR "
            "(predicted_confidence >= 0 AND predicted_confidence <= 1)",
        )
