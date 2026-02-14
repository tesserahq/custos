"""move user to attributes column

Revision ID: bab49554ee2b
Revises: init
Create Date: 2026-02-14 16:42:46.787073

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bab49554ee2b"
down_revision: Union[str, None] = "init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add attributes JSONB, migrate data, drop old columns."""
    # Add attributes column with empty default
    op.add_column(
        "users",
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    # Migrate existing data into attributes (ISO format for datetimes)
    op.execute("""
        UPDATE users SET attributes = jsonb_build_object(
            'avatar_url', avatar_url,
            'first_name', COALESCE(first_name, ''),
            'last_name', COALESCE(last_name, ''),
            'provider', provider,
            'confirmed_at', CASE WHEN confirmed_at IS NOT NULL
                THEN to_char(confirmed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
                ELSE NULL END,
            'verified', COALESCE(verified, false),
            'verified_at', CASE WHEN verified_at IS NOT NULL
                THEN to_char(verified_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
                ELSE NULL END,
            'service_account', COALESCE(service_account, false)
        )
        """)

    # Drop old columns
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "first_name")
    op.drop_column("users", "last_name")
    op.drop_column("users", "provider")
    op.drop_column("users", "confirmed_at")
    op.drop_column("users", "verified")
    op.drop_column("users", "verified_at")
    op.drop_column("users", "service_account")


def downgrade() -> None:
    """Downgrade schema: restore columns from attributes, drop attributes."""
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("first_name", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "users",
        sa.Column("provider", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("verified", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("verified_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "service_account", sa.Boolean(), nullable=True, server_default="false"
        ),
    )

    # Migrate data back from attributes
    op.execute("""
        UPDATE users SET
            avatar_url = attributes->>'avatar_url',
            first_name = COALESCE(attributes->>'first_name', ''),
            last_name = COALESCE(attributes->>'last_name', ''),
            provider = attributes->>'provider',
            confirmed_at = (attributes->>'confirmed_at')::timestamptz,
            verified = COALESCE((attributes->>'verified')::boolean, false),
            verified_at = (attributes->>'verified_at')::timestamptz,
            service_account = COALESCE((attributes->>'service_account')::boolean, false)
        """)

    # Remove server defaults before adding unique constraint
    op.alter_column("users", "first_name", server_default=None)
    op.alter_column("users", "last_name", server_default=None)
    op.alter_column("users", "verified", server_default=None)
    op.alter_column("users", "service_account", server_default=None)

    # Drop attributes column
    op.drop_column("users", "attributes")
