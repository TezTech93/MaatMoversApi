"""stripe connect status + payout transfer id

Revision ID: 0004_connect_payouts
Revises: 0003_stripe_foundation
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_connect_payouts"
down_revision = "0003_stripe_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Mover Connect status
    op.add_column(
        "movers",
        sa.Column(
            "stripe_connect_charges_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "movers",
        sa.Column(
            "stripe_connect_payouts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "movers",
        sa.Column(
            "stripe_connect_details_submitted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "movers",
        sa.Column(
            "stripe_connect_onboarded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Payout transfer id
    op.add_column(
        "transactions",
        sa.Column("stripe_transfer_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_transactions_transfer_id",
        "transactions",
        ["stripe_transfer_id"],
    )

    # Enforce uniqueness of connect account ids when non-null
    op.create_unique_constraint(
        "uq_movers_stripe_connect_id",
        "movers",
        ["stripe_connect_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_movers_stripe_connect_id", "movers", type_="unique"
    )
    op.drop_index("ix_transactions_transfer_id", table_name="transactions")
    op.drop_column("transactions", "stripe_transfer_id")

    op.drop_column("movers", "stripe_connect_onboarded_at")
    op.drop_column("movers", "stripe_connect_details_submitted")
    op.drop_column("movers", "stripe_connect_payouts_enabled")
    op.drop_column("movers", "stripe_connect_charges_enabled")