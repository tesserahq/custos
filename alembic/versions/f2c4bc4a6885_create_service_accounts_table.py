"""create_service_accounts_table

Revision ID: f2c4bc4a6885
Revises: create_users_table
Create Date: 2025-07-08 12:27:49.589844

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f2c4bc4a6885"
down_revision: Union[str, None] = "create_users_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "service_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # API key is not stored, only the hash is stored for security
        sa.Column("api_key_hash", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_id", sa.String, nullable=True),
        # Permissions are managed through Casbin RBAC system
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )

    # Add partial unique indexes
    op.create_index(
        "uq_service_accounts_external_id",
        "service_accounts",
        ["external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    op.create_index(
        "uq_service_accounts_api_key_hash",
        "service_accounts",
        ["api_key_hash"],
        unique=True,
        postgresql_where=sa.text("api_key_hash IS NOT NULL"),
    )

    # Add foreign key constraint for created_by
    op.create_foreign_key(
        "fk_service_accounts_created_by_users",
        "service_accounts",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint
    op.drop_constraint(
        "fk_service_accounts_created_by_users", "service_accounts", type_="foreignkey"
    )

    # Drop indexes
    op.drop_index("uq_service_accounts_api_key_hash", table_name="service_accounts")
    op.drop_index("uq_service_accounts_external_id", table_name="service_accounts")

    # Drop table
    op.drop_table("service_accounts")
