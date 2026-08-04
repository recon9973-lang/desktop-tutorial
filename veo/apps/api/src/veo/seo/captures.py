"""잰 것을 남긴다 — 진단이 실제로 받은 응답.

venomad.com 진단이 15~27점으로 나왔는데 "무엇을 받았길래 그 점수인가" 에 답할 방법이
없었다. 남아 있던 것은 sha256 해시 64자와 수집기가 고른 2,000자 발췌뿐이었다. 코드를
읽고 판정에서 거꾸로 추측하는 데 감사관 넷과 하루가 들었고, 그러고도 확정하지 못했다.

아무 AI에게 주소를 주면 페이지를 열어 보고 답한다. 측정기라면서 측정한 것을 안 갖고
있었던 것이 이 사태의 뿌리다.

**못 읽은 응답을 먼저 담는다.** 그것이 가장 필요한 자리다 — 잘 읽은 페이지는 점수가
설명해 주지만, 못 읽은 응답은 아무것도 말해 주지 않는다.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from veo.collect.contract import CollectionContext
from veo.common.security.fetcher import FetchedDocument
from veo.db.models.analysis import FetchCapture, ScanRun

#: 한 응답에서 담을 최대 바이트. 넘으면 앞부분만 담고 `truncated` 로 남긴다.
#:
#: 64KB 는 HTML 문서의 head 와 본문 상당 부분을 담기에 넉넉하고(venomad 홈이 51KB),
#: 진단 한 번에 몇 장을 담아도 용량이 문제되지 않는 크기다.
MAX_CAPTURE_BYTES = 64 * 1024

#: 한 진단에서 담을 최대 응답 수. 못 읽은 것을 먼저 담으므로, 상한에 걸려도 문제를
#: 보여 주는 쪽이 남는다.
MAX_CAPTURES_PER_RUN = 10

#: 헤더 중 남기는 것. 나머지는 담지 않는다 — 쿠키·인증 값이 섞여 들어올 자리를 애초에
#: 만들지 않는다.
KEPT_HEADERS = frozenset(
    {
        "content-type",
        "content-length",
        "content-encoding",
        "server",
        "cache-control",
        "location",
        "x-robots-tag",
        "vary",
    }
)


def _safe(headers: object) -> dict[str, str]:
    if not isinstance(headers, dict):
        return {}
    return {
        str(key).lower(): str(value)
        for key, value in headers.items()
        if str(key).lower() in KEPT_HEADERS
    }


def _row(
    *,
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
    document: FetchedDocument,
    reason_ko: str | None,
) -> FetchCapture:
    body = document.body or b""
    kept = body[:MAX_CAPTURE_BYTES]
    return FetchCapture(
        organization_id=organization_id,
        scan_run_id=run_id,
        url=document.requested_url,
        final_url=document.final_url,
        status=document.status,
        headers=_safe(document.headers),
        request_headers=_safe(document.request_headers),
        body=kept,
        byte_size=len(body),
        truncated=len(kept) < len(body),
        content_hash=hashlib.sha256(body).hexdigest(),
        fetched_at=document.fetched_at,
        read_failure_ko=reason_ko,
    )


def save_captures(
    db: Session,
    *,
    organization_id: uuid.UUID,
    scan_id: uuid.UUID,
    run_id: uuid.UUID,
    context: CollectionContext,
) -> int:
    """이번 진단이 받은 응답을 담고, 같은 대상의 **옛 보관본은 지운다.**

    보관 기간은 대상마다 가장 최근 한 번분이다. 문제를 볼 수 있으면서 용량은 최소다 —
    이 자리가 커지면 아무도 켜 두지 않게 되고, 그러면 없는 것과 같아진다.
    """
    # 못 읽은 것을 **먼저**. 상한에 걸려도 문제를 보여 주는 쪽이 남는다.
    ordered: list[tuple[FetchedDocument, str | None]] = [
        (document, reason) for document, reason in context.unread_documents
    ]
    ordered.extend((document, None) for document in context.documents.values())

    rows = [
        _row(
            organization_id=organization_id,
            run_id=run_id,
            document=document,
            reason_ko=reason,
        )
        for document, reason in ordered[:MAX_CAPTURES_PER_RUN]
    ]
    if not rows:
        return 0

    _forget_older_runs(db, scan_id=scan_id, keep_run_id=run_id)
    db.add_all(rows)
    db.flush()
    return len(rows)


def _forget_older_runs(db: Session, *, scan_id: uuid.UUID, keep_run_id: uuid.UUID) -> None:
    older = select(ScanRun.id).where(ScanRun.scan_id == scan_id, ScanRun.id != keep_run_id)
    db.execute(delete(FetchCapture).where(FetchCapture.scan_run_id.in_(older)))


def read_captures(
    db: Session, *, organization_id: uuid.UUID, run_id: uuid.UUID
) -> Sequence[FetchCapture]:
    """이 실행이 받은 응답들. 조직 밖의 것은 돌려주지 않는다."""
    statement = (
        select(FetchCapture)
        .where(
            FetchCapture.scan_run_id == run_id,
            FetchCapture.organization_id == organization_id,
        )
        .order_by(FetchCapture.read_failure_ko.is_(None), FetchCapture.url)
    )
    return list(db.scalars(statement))
