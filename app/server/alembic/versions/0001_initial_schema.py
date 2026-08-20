"""Immutable baseline for the current FAIRS relational schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This revision is the immutable representation of the pre-Alembic schema.
    op.create_table(
        "datasets",
        sa.Column("dataset_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_name", sa.String(length=128), nullable=False),
        sa.Column("dataset_name_key", sa.String(length=128), nullable=False),
        sa.Column("dataset_kind", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "dataset_kind IN ('training', 'inference')",
            name="ck_datasets_kind",
        ),
        sa.PrimaryKeyConstraint("dataset_id"),
        sa.UniqueConstraint(
            "dataset_kind",
            "dataset_name_key",
            name="uq_datasets_kind_name_key",
        ),
    )
    op.create_index(
        "ix_datasets_kind_name",
        "datasets",
        ["dataset_kind", "dataset_name_key"],
        unique=False,
    )

    op.create_table(
        "dataset_outcomes",
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("outcome_id", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "sequence_index >= 0",
            name="ck_dataset_outcomes_sequence",
        ),
        sa.CheckConstraint(
            "outcome_id >= 0 AND outcome_id <= 36",
            name="ck_dataset_outcomes_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.dataset_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("dataset_id", "sequence_index"),
    )
    op.create_index(
        "ix_dataset_outcomes_dataset_outcome",
        "dataset_outcomes",
        ["dataset_id", "outcome_id"],
        unique=False,
    )

    op.create_table(
        "inference_sessions",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("checkpoint_name", sa.String(length=128), nullable=False),
        sa.Column("initial_capital", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "initial_capital > 0",
            name="ck_inference_sessions_initial_capital",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.dataset_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(
        "ix_inference_sessions_dataset_started",
        "inference_sessions",
        ["dataset_id", "started_at"],
        unique=False,
    )

    op.create_table(
        "inference_session_steps",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("bet_amount", sa.Integer(), nullable=False),
        sa.Column("predicted_action", sa.Integer(), nullable=False),
        sa.Column("predicted_confidence", sa.Float(), nullable=True),
        sa.Column("observed_outcome_id", sa.SmallInteger(), nullable=True),
        sa.Column("reward", sa.Integer(), nullable=True),
        sa.Column("capital_after", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "step_number > 0",
            name="ck_inference_steps_step_number",
        ),
        sa.CheckConstraint(
            "bet_amount > 0",
            name="ck_inference_steps_bet_amount",
        ),
        sa.CheckConstraint(
            "predicted_action >= 0 AND predicted_action <= 46",
            name="ck_inference_steps_action",
        ),
        sa.CheckConstraint(
            "observed_outcome_id IS NULL OR (observed_outcome_id >= 0 AND observed_outcome_id <= 36)",
            name="ck_inference_steps_observed_outcome",
        ),
        sa.CheckConstraint(
            "predicted_confidence IS NULL OR (predicted_confidence >= 0 AND predicted_confidence <= 1)",
            name="ck_inference_steps_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["inference_sessions.session_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id", "step_number"),
    )
    op.create_index(
        "ix_inference_steps_session_recorded",
        "inference_session_steps",
        ["session_id", "recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inference_steps_session_recorded",
        table_name="inference_session_steps",
    )
    op.drop_table("inference_session_steps")
    op.drop_index(
        "ix_inference_sessions_dataset_started",
        table_name="inference_sessions",
    )
    op.drop_table("inference_sessions")
    op.drop_index(
        "ix_dataset_outcomes_dataset_outcome",
        table_name="dataset_outcomes",
    )
    op.drop_table("dataset_outcomes")
    op.drop_index("ix_datasets_kind_name", table_name="datasets")
    op.drop_table("datasets")
