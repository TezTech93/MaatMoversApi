"""stripe foundation: processed_events + checkout session id

Revision ID: 0003_stripe_foundation
Revises: 0002_core_tables
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_stripe_foundation"
down_revision = "0002_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.add_column(
        "transactions",
        sa.Column("stripe_checkout_session_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_transactions_checkout_session",
        "transactions",
        ["stripe_checkout_session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_checkout_session", table_name="transactions")
    op.drop_column("transactions", "stripe_checkout_session_id")
    op.drop_table("processed_events")