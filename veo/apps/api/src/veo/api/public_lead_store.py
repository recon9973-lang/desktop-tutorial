"""리드의 DB 저장소 — 격리 불변식의 반대편 절반, 공유 결과 저장소와 같은 계열.

공개 패키지는 DB 를 임포트하지 못한다(tests/public/test_isolation.py). 그래서
재시작을 견디는 저장은 여기가 맡고, :func:`veo.api.app.create_app` 이
``dependency_overrides[get_lead_store]`` 로 건다.

실패의 방향이 공유 결과 저장소와 **반대**라는 점이 이 모듈의 요지다:

* 공유 결과의 쓰기 실패는 삼킨다 — 진단은 이미 끝났고, 링크 하나 때문에 완성된
  결과를 버리는 것이 더 큰 거짓이다.
* **리드의 쓰기 실패는 던진다** — 이 엔드포인트의 응답은 "무엇을 저장했는지" 그
  자체다. 저장하지 못했으면서 "저장했습니다" 라고 답하는 것이야말로 최악의 거짓이고,
  방문자는 실패를 보고 전화라는 다른 길을 찾을 수 있다.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import final

from sqlalchemy.orm import Session

from veo.db.models import PublicLead
from veo.db.session import session_scope
from veo.public.leads import LeadStore, StoredLead

__all__ = ["DbLeadStore", "build_lead_store"]


@final
class DbLeadStore:
    """세션은 요청의 것이 아니라 그 자리에서 열고 닫는다 — usage recorder 와 같은 이유."""

    __slots__ = ("_scope",)

    def __init__(
        self,
        scope: Callable[[], AbstractContextManager[Session]] = session_scope,
    ) -> None:
        self._scope = scope

    def add(self, lead: StoredLead) -> None:
        # 실패는 그대로 올라간다 — "저장했습니다" 가 거짓이 되면 안 된다(모듈 머리글).
        with self._scope() as db:
            db.add(
                PublicLead(
                    lead_id=lead.lead_id,
                    received_at=lead.received_at,
                    name=lead.name,
                    phone=lead.phone,
                    email=lead.email,
                    site_url=lead.site_url,
                )
            )


def build_lead_store() -> LeadStore:
    return DbLeadStore()
