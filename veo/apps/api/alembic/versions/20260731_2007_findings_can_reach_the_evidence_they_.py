"""findings can reach the evidence they cite

``check_results.evidence_ids`` and ``issues.evidence_ids`` store names like
``http_response:f98f677064c9d854``. The ``evidence`` table had no column holding that
name, so every stored reference pointed at nothing. Against production: 56 evidence rows,
none of them reachable by the names the findings use.

**This one is backfilled, and that does not contradict the migration before it.** The id
is a pure function of two columns already on the row —
``kind || ':' || left(content_hash, 16)`` is exactly what
:meth:`veo.collect.contract.EvidenceRecord.of` computes. Recomputing a stored function
recovers a fact; filling in measurement conditions would have invented one. The
difference is whether the answer is already in the row.

Revision ID: bd39e74354f4
Revises: ed850547ba54
Create Date: 2026-07-31 20:07:23.993301
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bd39e74354f4"
down_revision: str | None = "ed850547ba54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column(
            "evidence_id",
            sa.String(length=96),
            server_default="",
            nullable=False,
            comment="판정·이슈가 근거를 부를 때 쓰는 이름. kind:content_hash[:16].",
        ),
    )
    # 저장된 두 칸에서 같은 함수로 다시 계산한다. 지어내는 것이 아니라 되찾는 것이다.
    op.execute(
        sa.text(
            "UPDATE evidence SET evidence_id = kind || ':' || left(content_hash, 16) "
            "WHERE evidence_id = ''"
        )
    )
    op.create_index(
        "ix_evidence_run_evidence_id", "evidence", ["scan_run_id", "evidence_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_run_evidence_id", table_name="evidence")
    op.drop_column("evidence", "evidence_id")
