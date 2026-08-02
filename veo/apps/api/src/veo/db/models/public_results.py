"""공유 토큰으로 다시 읽는 익명 진단 결과 — 재시작을 견디는 쪽 절반.

조직 칼럼이 없다. 익명 방문자의 결과이므로 어떤 고객 행에도 속하지 않고, 격리
불변식(tests/public/test_isolation.py)에 따라 공개 패키지는 이 모델을 임포트하지
못한다. 읽고 쓰는 곳은 조립 지점이 주입하는 저장소 구현
(:mod:`veo.api.public_result_store`) 하나뿐이다.

토큰 원문은 어디에도 없다 — 행의 키는 토큰의 지문(해시)이고, 저장 직전에 payload
안의 ``result_token`` 도 지운다. DB 가 통째로 읽혀도 공유 주소를 복원할 수 없다.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from veo.db.base import Base, JsonObject, TimestampMixin, json_column


class PublicSharedResult(Base, TimestampMixin):
    """One shareable anonymous scan result, keyed by the token's fingerprint."""

    __tablename__ = "public_shared_results"

    fingerprint: Mapped[str] = mapped_column(String(128), primary_key=True)
    #: 응답 payload 그대로(JSON) — 단, result_token 은 빈 문자열로 지워져 있다.
    payload: Mapped[JsonObject] = json_column()
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
