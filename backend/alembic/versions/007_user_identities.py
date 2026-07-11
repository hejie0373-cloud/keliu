"""add verified user identities

Revision ID: 007
Revises: 006
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade():
    if not _has_column("users", "email"):
        op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True, comment="email"))
        op.create_unique_constraint("uq_users_email", "users", ["email"])

    if not _has_table("user_identities"):
        op.create_table(
            "user_identities",
            sa.Column("id", mysql.CHAR(32), nullable=False),
            sa.Column("user_id", mysql.CHAR(32), nullable=False),
            sa.Column("type", sa.String(length=20), nullable=False),
            sa.Column("identifier", sa.String(length=255), nullable=False),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("type", "identifier", name="uq_user_identity_type_identifier"),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    op.execute(
        """
        INSERT IGNORE INTO user_identities
            (id, user_id, type, identifier, verified_at, is_primary, created_at, updated_at)
        SELECT REPLACE(UUID(), '-', ''), id, 'phone', phone, created_at, TRUE, created_at, updated_at
        FROM users
        WHERE phone IS NOT NULL AND phone <> ''
        """
    )
    op.execute(
        """
        INSERT IGNORE INTO user_identities
            (id, user_id, type, identifier, verified_at, is_primary, created_at, updated_at)
        SELECT REPLACE(UUID(), '-', ''), id, 'email', LOWER(email), created_at, phone IS NULL, created_at, updated_at
        FROM users
        WHERE email IS NOT NULL AND email <> ''
        """
    )
    if _has_column("users", "wechat_openid"):
        op.execute(
            """
            INSERT IGNORE INTO user_identities
                (id, user_id, type, identifier, verified_at, is_primary, created_at, updated_at)
            SELECT REPLACE(UUID(), '-', ''), id, 'wechat', wechat_openid, created_at, FALSE, created_at, updated_at
            FROM users
            WHERE wechat_openid IS NOT NULL AND wechat_openid <> ''
            """
        )


def downgrade():
    if _has_table("user_identities"):
        op.drop_table("user_identities")
