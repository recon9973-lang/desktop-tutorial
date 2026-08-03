"""무료 진단에서 남긴 상담 요청(리드) — 재시작을 견디는 쪽 절반.

조직 칼럼이 없다. 리드는 아직 어떤 고객도 아니다 — 이름과 연락처 하나가 전부인
문의이고, 격리 불변식(tests/public/test_isolation.py)에 따라 공개 패키지는 이 모델을
임포트하지 못한다. 읽고 쓰는 곳은 조립 지점이 주입하는 저장소 구현
(:mod:`veo.api.public_lead_store`) 하나뿐이다.

칼럼은 :class:`veo.public.leads.StoredLead` 의 다섯 필드 그대로다 — 여섯 번째 칸을
만들지 않는 것이 그 모듈의 존재 이유이므로, 테이블도 똑같이 다섯 칸이다.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from veo.db.base import Base, TimestampMixin


class PublicLead(Base, TimestampMixin):
    """One callback request from the free checker. Five fields, and no sixth."""

    __tablename__ = "public_leads"

    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    site_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
