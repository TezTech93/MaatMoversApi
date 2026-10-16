"""create core tables

Revision ID: 0002_core_tables
Revises: 0001_create_users
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_core_tables"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("service_radius_miles", sa.Integer(), nullable=False),
        sa.Column("home_address", sa.String(500), nullable=False),
        sa.Column("home_lat", sa.Float(), nullable=False),
        sa.Column("home_lng", sa.Float(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("stripe_connect_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("service_radius_miles >= 1 AND service_radius_miles <= 25",
                           name="ck_movers_radius"),
        sa.CheckConstraint("verification_status in ('pending','approved','rejected')",
                           name="ck_movers_verification"),
    )
    op.create_index("ix_movers_user_id", "movers", ["user_id"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("default_address", sa.String(500), nullable=True),
        sa.Column("default_lat", sa.Float(), nullable=True),
        sa.Column("default_lng", sa.Float(), nullable=True),
        sa.Column("stripe_customer_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_clients_user_id", "clients", ["user_id"], unique=True)

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price_cents", sa.Integer(), nullable=False),
        sa.Column("per_mile_cents", sa.Integer(), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("mover_id", sa.Integer(), sa.ForeignKey("movers.id"), nullable=True),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("pickup_address", sa.String(500), nullable=False),
        sa.Column("pickup_lat", sa.Float(), nullable=False),
        sa.Column("pickup_lng", sa.Float(), nullable=False),
        sa.Column("dropoff_address", sa.String(500), nullable=False),
        sa.Column("dropoff_lat", sa.Float(), nullable=False),
        sa.Column("dropoff_lng", sa.Float(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("distance_miles", sa.Float(), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("deposit_cents", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status in ('draft','pending','accepted','in_progress','completed','cancelled','refunded')",
            name="ck_bookings_status",
        ),
    )
    op.create_index("ix_bookings_client_id", "bookings", ["client_id"])
    op.create_index("ix_bookings_mover_id", "bookings", ["mover_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(128), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="usd"),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind in ('deposit','final','refund','payout')", name="ck_tx_kind"),
        sa.CheckConstraint("status in ('pending','succeeded','failed','refunded')", name="ck_tx_status"),
    )
    op.create_index("ix_transactions_booking_id", "transactions", ["booking_id"])
    op.create_index("ix_transactions_pi", "transactions", ["stripe_payment_intent_id"])

    op.create_table(
        "strikes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_strikes_user_id", "strikes", ["user_id"])
    op.create_index("ix_strikes_booking_id", "strikes", ["booking_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    op.create_table(
        "push_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("platform", sa.String(16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_push_tokens_user_id", "push_tokens", ["user_id"])
    op.create_index("ix_push_tokens_token", "push_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_push_tokens_token", table_name="push_tokens")
    op.drop_index("ix_push_tokens_user_id", table_name="push_tokens")
    op.drop_table("push_tokens")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_strikes_booking_id", table_name="strikes")
    op.drop_index("ix_strikes_user_id", table_name="strikes")
    op.drop_table("strikes")
    op.drop_index("ix_transactions_pi", table_name="transactions")
    op.drop_index("ix_transactions_booking_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_bookings_mover_id", table_name="bookings")
    op.drop_index("ix_bookings_client_id", table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("services")
    op.drop_index("ix_clients_user_id", table_name="clients")
    op.drop_table("clients")
    op.drop_index("ix_movers_user_id", table_name="movers")
    op.drop_table("movers")