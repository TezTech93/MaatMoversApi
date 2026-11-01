"""admin foundation: manager role, permissions column, escalations table

Revision ID: 0005_admin_foundation
Revises: 0004_connect_payouts
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_admin_foundation"
down_revision = "0004_connect_payouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Extend the role check constraint to include 'manager'.
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role in ('client','mover','manager','admin')",
    )

    # 2. Permissions column. JSON array stored as text, default empty list.
    op.add_column(
        "users",
        sa.Column(
            "permissions",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
    )

    # 3. Escalations table (used from Phase 6.2 onward).
    op.create_table(
        "escalations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "related_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "related_booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column(
            "resolved_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status in ('open','in_progress','resolved')",
            name="ck_escalations_status",
        ),
    )
    op.create_index("ix_escalations_status", "escalations", ["status"])
    op.create_index("ix_escalations_created_by", "escalations", ["created_by_id"])
    op.create_index("ix_escalations_related_user", "escalations", ["related_user_id"])


def downgrade() -> None:
    op.drop_index("ix_escalations_related_user", table_name="escalations")
    op.drop_index("ix_escalations_created_by", table_name="escalations")
    op.drop_index("ix_escalations_status", table_name="escalations")
    op.drop_table("escalations")

    op.drop_column("users", "permissions")

    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role in ('client','mover','admin')",
    )