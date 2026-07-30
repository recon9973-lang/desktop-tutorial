"""원문 AI 답변을 재배포에서 살아남는 자리에 둔다.

## 무엇이 문제였나

`FilesystemAnswerStore` 는 로컬 디스크에 쓴다. 개발 장비에서는 맞지만 배포 환경의
컨테이너 파일시스템은 **재배포마다 초기화된다.**

`ai_answers` 행에는 저장 키와 해시만 남는다(원문 인라인 금지). 그래서 파일이 사라지면
행은 남는데 가리키는 대상이 없어지고, **"이 판정의 근거를 보여 달라" 에 답할 수 없다.**
0-A 의 마지막 줄이 무너지는 지점이다 — *"이 점수가 왜 이렇게 나왔는가에 답할 수 없으면
그 점수는 쓰지 않는다."*

## 왜 오브젝트 스토리지가 아닌가

마스터 §2.1 이 정한 자리는 S3 호환 오브젝트 스토리지이고 그쪽이 맞다. 다만 지금 배포에
그것이 없다. **없는 것을 있는 척하지 않고**, 이미 있는 것 중 재배포를 견디는 유일한
자리인 DB 를 쓴다. 붙으면 이 클래스와 같은 프로토콜로 어댑터를 하나 더 만들면 된다 —
`RecordedAnswerStore` 가 그 자리를 이미 정의해 두었다.

## 읽을 때 해시를 다시 계산한다

파일 저장소와 같다. 기록된 해시와 다르면 **읽기를 거부한다.** 근거로 쓸 수 없는 것을
근거처럼 돌려주는 것보다 못 읽는 편이 낫다.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import final

from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.db.models.observation import AnswerDocument
from veo.observations.answer_store import AnswerNotFoundError, AnswerTamperedError
from veo.observations.providers.storage import (
    REF_SCHEME,
    AnswerRecordKey,
    RecordedAnswer,
    StoredAnswer,
)


@final
class DatabaseAnswerStore:
    """답변 원문을 `answer_documents` 에 보관한다. 조직 단위로 갈라진다."""

    def __init__(self, *, session: Session, organization_id: uuid.UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    def __repr__(self) -> str:
        return f"<DatabaseAnswerStore org={self._organization_id}>"

    # ------------------------------------------------------------------ #

    def put(self, key: AnswerRecordKey, record: RecordedAnswer) -> StoredAnswer:
        """한 건을 저장하고 가리키는 값을 돌려준다.

        같은 키로 다시 부르면 **덮어쓰지 않고 원래 것을 돌려준다.** 관측은 되돌릴 수
        없는 기록이고, 같은 질문·같은 조건·같은 회차는 하나여야 한다. 덮어쓰면 두
        번째 실행이 첫 번째를 지워 버린다.
        """
        existing = self._row(key.object_key)
        if existing is not None:
            return StoredAnswer(ref=key.ref, sha256=existing.sha256)

        body = record.to_bytes()
        digest = hashlib.sha256(body).hexdigest()
        self._session.add(
            AnswerDocument(
                organization_id=self._organization_id,
                object_key=key.object_key,
                sha256=digest,
                body=body,
            )
        )
        # flush 만 한다. 커밋은 실행 전체를 감싸는 쪽이 정한다 — 답변만 남고 실행 기록이
        # 사라지거나 그 반대가 되면 어느 쪽도 근거가 되지 못한다.
        self._session.flush()
        return StoredAnswer(ref=key.ref, sha256=digest)

    def find(self, key: AnswerRecordKey) -> StoredAnswer | None:
        row = self._row(key.object_key)
        if row is None:
            return None
        return StoredAnswer(ref=key.ref, sha256=row.sha256)

    def read(self, ref: str) -> RecordedAnswer:
        object_key = ref[len(REF_SCHEME) :] if ref.startswith(REF_SCHEME) else ref
        row = self._row(object_key)
        if row is None:
            raise AnswerNotFoundError(f"저장된 답변을 찾을 수 없습니다: {ref}")

        actual = hashlib.sha256(row.body).hexdigest()
        if actual != row.sha256:
            raise AnswerTamperedError(
                f"저장된 답변이 기록된 해시와 다릅니다: {ref}. "
                "수집 이후 내용이 바뀌었으므로 근거로 사용하지 않습니다."
            )
        return RecordedAnswer.from_bytes(row.body)

    # ------------------------------------------------------------------ #

    def _row(self, object_key: str) -> AnswerDocument | None:
        return self._session.scalars(
            select(AnswerDocument)
            .where(AnswerDocument.organization_id == self._organization_id)
            .where(AnswerDocument.object_key == object_key)
        ).first()


__all__ = ["DatabaseAnswerStore"]
