"""answers record how much they cost and why not

``ai_answers.cost_usd`` already carried a comment saying that a missing value means "we do
not know" and that the reason is one of three. There was no column holding the reason. The
provider adapters compute it — five distinct cases, each with a different remedy — and it
reached the answer object store but never the database.

Token counts had the same fate. The adapters parse ``input_tokens`` and ``output_tokens``
from every response and dropped them at the first hop. With the shipped price table still
empty (``prices: {}`` on purpose — an unverified price is worse than none), tokens are the
only measurable signal of what a run actually consumed.

Nullable, not backfilled. Answers stored before these columns cannot have their basis or
token counts recovered — those facts were never written down, and the report reads them as
``UNSPECIFIED`` rather than guessing.

Revision ID: dfefebcc2758
Revises: bd39e74354f4
Create Date: 2026-07-31 21:09:41.494787
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "dfefebcc2758"
down_revision: str | None = "bd39e74354f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_answers",
        sa.Column(
            "cost_basis",
            sa.String(length=48),
            nullable=True,
            comment=(
                "CALCULATED_FROM_USAGE | NO_PRICE_CONFIGURED | NO_USAGE_REPORTED | "
                "PRICE_TABLE_STALE"
            ),
        ),
    )
    op.add_column("ai_answers", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_answers", sa.Column("output_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_answers", "output_tokens")
    op.drop_column("ai_answers", "input_tokens")
    op.drop_column("ai_answers", "cost_basis")
