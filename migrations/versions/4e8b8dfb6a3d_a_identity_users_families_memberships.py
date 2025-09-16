"""A_Identity: users families memberships

Revision ID: 4e8b8dfb6a3d
Revises: 
Create Date: 2025-09-14 22:07:03.411159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e8b8dfb6a3d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: users, families, family_memberships."""

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # families
    op.create_table(
        "families",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("invite_code", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # family_memberships
    op.create_table(
        "family_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "family_id",
            sa.Integer(),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("family_id", "user_id", name="uq_family_user"),
    )

    # CHECK constraint on role
    op.create_check_constraint(
        "ck_membership_role",
        "family_memberships",
        "role IN ('owner','admin','member')",
    )

    # Helpful index for membership lookups
    op.create_index(
        "ix_memberships_family_user",
        "family_memberships",
        ["family_id", "user_id"],
    )


def downgrade() -> None:
    """Downgrade schema (reverse order of dependencies)."""

    # drop index/constraint first
    op.drop_index("ix_memberships_family_user", table_name="family_memberships")
    op.drop_constraint("ck_membership_role", "family_memberships", type_="check")

    # drop tables in FK-safe order
    op.drop_table("family_memberships")
    op.drop_table("families")
    op.drop_table("users")