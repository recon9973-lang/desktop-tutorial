"""check results remember which pages they judged

"canonical 문제 103장" 은 저장되는데 **어느** 103장인지는 저장되지 않았다. 수집기는
페이지 목록을 알고 있었고, 판정 객체에 실리지 않아 저장 직전에 버려졌다 — 비용 근거·
토큰 수·측정 조건·사이트맵 관측값과 같은 "재고 나서 저장할 때 흘림" 의 다섯 번째
사례다.

이 두 칸이 페이지별 점수의 기반이다(v3, SEO_SCORING_V3_PAGES.md §7-③): 페이지 P 의
검사 C 판정은 P ∈ affected_urls 이면 실패, P ∈ evaluated_urls 이면 통과, 어느 쪽에도
없으면 그 페이지에서 잰 적이 없는 것이다. 재크롤 없이 저장된 실행에서 재집계한다.

Nullable 이고 **채워 넣지 않는다.** 이 마이그레이션 전에 저장된 실행은 목록을 버린
뒤라 되살릴 수 없다 — 그럴듯한 값으로 채우면 "모른다" 가 "이 페이지들이었다" 로
둔갑한다. 옛 실행의 NULL 은 "기록되지 않았다" 로 읽는 것이 맞다.

Revision ID: 6f0b1b1941dd
Revises: dfefebcc2758
Create Date: 2026-08-02 01:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6f0b1b1941dd"
down_revision: str | None = "dfefebcc2758"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "check_results",
        sa.Column(
            "affected_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="이 검사에 걸린 페이지 URL 목록. 옛 실행은 NULL(기록되지 않음).",
        ),
    )
    op.add_column(
        "check_results",
        sa.Column(
            "evaluated_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="이 검사가 판정한 페이지 URL 목록. 옛 실행은 NULL(기록되지 않음).",
        ),
    )


def downgrade() -> None:
    op.drop_column("check_results", "evaluated_urls")
    op.drop_column("check_results", "affected_urls")
