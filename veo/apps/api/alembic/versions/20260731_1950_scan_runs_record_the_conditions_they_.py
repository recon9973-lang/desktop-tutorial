"""scan runs record the conditions they were measured under

`MeasurementConditions` says of itself that it is stored with every result. It was stored
with none. This adds the column that holds it.

Nullable on purpose, and **not backfilled**. Runs saved before this migration were made
under conditions nobody wrote down; filling them with today's values would turn "we do
not know" into "it was the same", which is the one answer the comparison guard must never
be handed. Those rows read back as incomparable, and that is correct.

Revision ID: ed850547ba54
Revises: 8c41d7b02e19
Create Date: 2026-07-31 19:50:51.479584
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ed850547ba54"
down_revision: str | None = "8c41d7b02e19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scan_runs",
        sa.Column(
            "measurement_conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="MeasurementConditions.as_dict(). 옛 실행은 NULL.",
        ),
    )


def downgrade() -> None:
    op.drop_column("scan_runs", "measurement_conditions")
