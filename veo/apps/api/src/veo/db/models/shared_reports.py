"""거래처에 전달하는 리포트 공유 링크 — 공유 시점의 **복사본** (P2-10a).

행에는 조직 칼럼이 없고, 익명 읽기는 이 복사본만 본다. 공유란 여기서 "발행"이다:
링크를 만드는 순간의 HTML 내보내기가 통째로 굳어 저장되고, 이후 원본 조직 데이터가
어떻게 되든 링크가 여는 것은 그때 그 문서다 — 발행된 버전은 고칠 수 없다는 리포트
불변 원칙과 정확히 같은 결이고, 익명 표면이 요청 시점에 고객 데이터에 닿지 않는다는
격리 원칙(공유 진단 결과와 같은 계열)도 그대로다.

토큰 원문은 어디에도 없다 — 행의 키는 토큰의 지문(해시)이다. DB 가 통째로 읽혀도
공유 주소를 복원할 수 없다.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from veo.db.base import Base, TimestampMixin


class PublicSharedReport(Base, TimestampMixin):
    """One shared report version, frozen at share time, keyed by the token's fingerprint."""

    __tablename__ = "public_shared_reports"

    fingerprint: Mapped[str] = mapped_column(String(128), primary_key=True)
    #: 공유 시점의 HTML 내보내기 전문 — 외부 자원 없는 단일 파일(엔진 계약).
    html: Mapped[str] = mapped_column(Text, nullable=False)
    title_ko: Mapped[str] = mapped_column(String(300), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
