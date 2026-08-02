"""공유 결과의 DB 저장소 — 격리 불변식의 반대편 절반, usage recorder 와 같은 계열.

공개 패키지는 DB 를 임포트하지 못한다(tests/public/test_isolation.py). 그래서
재시작을 견디는 저장은 여기가 맡고, :func:`veo.api.app.create_app` 이
``dependency_overrides[get_result_store]`` 로 건다. 배선이 실제로 걸려 있다는 사실은
``tests/contract/test_public_result_wiring.py`` 가 지킨다.

실패의 방향이 쓰기와 읽기에서 다르다:

* **쓰기 실패는 삼킨다** — 진단은 이미 끝났다. 공유 링크 하나 때문에 완성된 결과를
  버리는 것이 더 큰 거짓이다. 로그에는 남는다.
* **읽기 실패는 던진다** — DB 가 죽었을 때 "만료되었습니다" 라고 말하면 링크를 받은
  사람에게 거짓말이 된다. 500 은 500 으로 나가야 화면이 "불러오지 못했다" 고 말할
  수 있다.

토큰 위생: 행의 키는 지문(해시)이고, 저장 직전에 payload 안의 ``result_token`` 도
지운다. 공유 주소를 복원할 재료를 DB 에 남기지 않기 위해서다 — 인메모리 시절에는
프로세스 메모리라 지나쳤지만, 디스크에 앉는 순간부터는 유출 반경이 다르다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from typing import final

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from veo.db.models import PublicSharedResult
from veo.db.session import session_scope
from veo.public.schemas import PublicResultPayload
from veo.public.service import PublicResultStore, StoredPublicResult

__all__ = ["DbPublicResultStore", "build_public_result_store"]

_PAYLOAD: TypeAdapter[PublicResultPayload] = TypeAdapter(PublicResultPayload)

_log = logging.getLogger(__name__)


@final
class DbPublicResultStore:
    """세션은 요청의 것이 아니라 그 자리에서 열고 닫는다 — usage recorder 와 같은 이유."""

    __slots__ = ("_scope",)

    def __init__(
        self,
        scope: Callable[[], AbstractContextManager[Session]] = session_scope,
    ) -> None:
        self._scope = scope

    def put(self, result: StoredPublicResult) -> None:
        try:
            with self._scope() as db:
                db.merge(
                    PublicSharedResult(
                        fingerprint=result.fingerprint,
                        payload=result.payload.model_copy(
                            update={"result_token": ""}
                        ).model_dump(mode="json"),
                        expires_at=result.expires_at,
                    )
                )
        except Exception:
            _log.exception("shared result write failed (fingerprint=%s)", result.fingerprint)

    def get(self, fingerprint_value: str, *, now: datetime) -> StoredPublicResult | None:
        with self._scope() as db:
            row = db.get(PublicSharedResult, fingerprint_value)
            if row is None:
                return None
            # 인메모리 저장소와 같은 규칙: 만료된 행은 걸러서 돌려주는 게 아니라
            # 읽는 자리에서 지운다 — 호출자의 만료 검사 버그를 살려두지 않는다.
            if now >= row.expires_at:
                db.delete(row)
                return None
            return StoredPublicResult(
                fingerprint=row.fingerprint,
                payload=_PAYLOAD.validate_python(row.payload),
                expires_at=row.expires_at,
            )


def build_public_result_store() -> PublicResultStore:
    """FastAPI 의존성 덮어쓰기 자리 — 요청마다 가벼운 껍데기 하나."""
    return DbPublicResultStore()
