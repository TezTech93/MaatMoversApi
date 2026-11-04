"""admin strikes: nullable booking_id + created_by; escalations already exist

Revision ID: 0006_admin_strikes
Revises: 0005_admin_foundation
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_admin_strikes"
down_revision = "0005_admin_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Manual admin strikes may not tie to a specific booking
    op.alter_column("strikes", "booking_id", existing_type=sa.Integer(), nullable=True)
    # Audit trail for manual strikes; null = system-issued (cancellation policy)
    op.add_column(
        "strikes",
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_strikes_created_by", "strikes", ["created_by_id"])


def downgrade() -> None:
    op.drop_index("ix_strikes_created_by", table_name="strikes")
    op.drop_column("strikes", "created_by_id")
    # Can't downgrade to NOT NULL if any nulls exist; leave as-is or clean first
    op.alter_column("strikes", "booking_id", existing_type=sa.Integer(), nullable=False)