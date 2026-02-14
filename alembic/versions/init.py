"""initialize tables

Revision ID: init
Revises:
Create Date: 2024-03-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String, unique=True, nullable=True),
        sa.Column("external_id", sa.String, nullable=True),
        sa.Column("avatar_url", sa.String, nullable=True),
        sa.Column("first_name", sa.String, nullable=False),
        sa.Column("last_name", sa.String, nullable=False),
        sa.Column("provider", sa.String, nullable=True),
        sa.Column("confirmed_at", sa.DateTime, nullable=True),
        sa.Column("verified", sa.Boolean, default=False),
        sa.Column("verified_at", sa.DateTime, nullable=True),
        sa.Column("service_account", sa.Boolean, default=False),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    # Add a partial unique index for external_id
    op.create_index(
        "uq_users_external_id",
        "users",
        ["external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    op.create_table(
        "roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("identifier", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_index(
        "uq_roles_identifier",
        "roles",
        ["identifier"],
        unique=True,
    )

    op.create_table(
        "permissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id"),
            nullable=False,
        ),
        sa.Column("object", sa.String, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id"),
            nullable=False,
        ),
        sa.Column(
            "domain",
            sa.String,
            nullable=True,
        ),
        sa.Column(
            "domain_metadata",
            postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    # Drop indexes before dropping tables
    op.drop_index("uq_users_external_id", table_name="users")

    op.drop_table("memberships")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
