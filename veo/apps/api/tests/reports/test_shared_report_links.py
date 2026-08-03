"""리포트 거래처 전달 링크 (P2-10a) — 공유는 복사본의 발행이다.

지키는 성질:

1. 링크를 만들면 **그 순간의 HTML** 이 굳어 저장된다 — 이후 무엇이 바뀌어도 링크가
   여는 것은 보낸 그날의 그 문서다.
2. 없는 토큰·만료된 토큰·모양이 아닌 것은 **같은 404** 를 받는다 — 어떤 토큰이
   실재했는지 확인해 주는 창구가 되지 않는다.
3. 만료된 행은 읽는 자리에서 지워진다(공유 진단 결과와 같은 규칙).
4. 익명 문서는 sandbox CSP 로 잠긴다 — 문서가 문서 이상이 되지 못한다.
"""

from __future__ import annotations

import datetime as dt
import uuid
from types import SimpleNamespace

import pytest

pytest.importorskip("pydantic")

from fastapi import HTTPException

from veo.api.routes.shared_reports import read_shared_report, share_report_version
from veo.authz import Principal
from veo.contracts.enums import Role
from veo.db.models import PublicSharedReport
from veo.public.tokens import fingerprint, mint_token
from veo.reports.service import ExportResult


def _principal() -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        roles=frozenset({Role.ANALYST}),
        session_id="share-test",
    )


class StubReportService:
    def __init__(self, html: str) -> None:
        self.html = html

    def export(self, **kwargs):  # type: ignore[no-untyped-def]
        return ExportResult(
            body=self.html.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            filename="report-v3.html",
        )


class TestSharing:
    def test_sharing_freezes_the_document_of_that_moment(
        self, db, monkeypatch
    ):
        import veo.api.routes.shared_reports as module

        monkeypatch.setattr(
            module,
            "get_settings",
            lambda: SimpleNamespace(report_share_ttl_days=90),
        )
        service = StubReportService("<!doctype html><title>8월 보고서</title>")

        response = share_report_version(
            uuid.uuid4(), 3, _principal(), str(uuid.uuid4()), db, service
        )

        path = response.data.share_path
        assert path.startswith("/shared/reports/")
        token = path.rsplit("/", 1)[1]
        row = db.get(PublicSharedReport, fingerprint(token))
        assert row is not None
        assert "8월 보고서" in row.html
        # 토큰 원문은 DB 에 없다 — 지문만.
        assert token not in row.fingerprint

    def test_reading_back_serves_the_frozen_copy_with_a_sandbox(
        self, db, monkeypatch
    ):
        import veo.api.routes.shared_reports as module

        monkeypatch.setattr(
            module, "get_settings", lambda: SimpleNamespace(report_share_ttl_days=90)
        )
        service = StubReportService("<!doctype html><title>굳은 문서</title>")
        shared = share_report_version(
            uuid.uuid4(), 1, _principal(), str(uuid.uuid4()), db, service
        )
        token = shared.data.share_path.rsplit("/", 1)[1]

        page = read_shared_report(token, db)

        assert b"\xea\xb5\xb3\xec\x9d\x80 \xeb\xac\xb8\xec\x84\x9c" in page.body  # "굳은 문서"
        assert page.headers["content-security-policy"] == "sandbox"


class TestUniformAbsence:
    def test_missing_expired_and_malformed_tokens_get_the_same_answer(
        self, db
    ):
        expired_token = mint_token()
        db.add(
            PublicSharedReport(
                fingerprint=fingerprint(expired_token),
                html="<!doctype html>",
                title_ko="지난 문서",
                expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
            )
        )
        db.flush()

        answers = []
        for candidate in [mint_token(), expired_token, "../../etc/passwd"]:
            with pytest.raises(HTTPException) as refused:
                read_shared_report(candidate, db)
            answers.append((refused.value.status_code, refused.value.detail))

        assert len(set(answers)) == 1, "답이 갈리면 어떤 토큰이 실재했는지 알려주는 창구가 된다"
        assert answers[0][0] == 404

    def test_an_expired_row_is_deleted_where_it_is_read(self, db):
        token = mint_token()
        db.add(
            PublicSharedReport(
                fingerprint=fingerprint(token),
                html="<!doctype html>",
                title_ko="지난 문서",
                expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
            )
        )
        db.flush()

        with pytest.raises(HTTPException):
            read_shared_report(token, db)

        assert db.get(PublicSharedReport, fingerprint(token)) is None
