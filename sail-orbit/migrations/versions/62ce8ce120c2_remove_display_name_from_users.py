"""remove display_name from users

Revision ID: 62ce8ce120c2
Revises: d383129da037
Create Date: 2026-10-07 21:47:52.424196

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "62ce8ce120c2"
down_revision: str | Sequence[str] | None = "d383129da037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove the display_name column from the users table."""
    op.drop_column("users", "display_name")


def downgrade() -> None:
    """Restore the display_name column to the users table."""
    op.add_column(
        "users",
        sa.Column(
            "display_name",
            sa.String(length=100),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column(
        "users",
        "display_name",
        server_default=None,
    )
