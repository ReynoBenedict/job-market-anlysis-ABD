"""source public label and condition

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-18 09:00:00.000000

Public reuse statement per source, separate from the internal eligibility gate
(``permission_status``). Nullable: unset means the API returns null.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("public_label", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("public_condition", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sources", "public_condition")
    op.drop_column("sources", "public_label")
