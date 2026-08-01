"""페이지 축 재집계 — "canonical 문제 103장" 을 "이 페이지의 문제 목록" 으로.

이 파일이 지키는 성질:

1. 판정 규칙 — 걸린 페이지는 그 행의 상태 그대로, 판정됐지만 안 걸린 페이지는 통과,
   어느 목록에도 없는 페이지·검사 조합은 **아예 나오지 않는다** (통과와 미측정을
   섞으면 페이지가 실제보다 건강해 보인다).
2. 점수 숫자가 없다 — 페이지 점수 산식은 명세 1.9.0 발행 전이다. 숫자가 생기는
   순간 그것은 발행 명세 밖의 숫자다.
3. 옛 실행(NULL)은 페이지를 지어내지 않고 "기록되기 전" 이라고 말한다.
4. SITE 판정은 페이지에 귀속되지 않고 측정 시각과 함께 따로 나온다.
5. 다른 조직의 실행은 없는 것(404)이다.
"""

from __future__ import annotations

import uuid

import pytest

pytest.importorskip("pydantic")


@pytest.fixture
def project(db_session, organization):
    from veo.db.models.identity import Project

    row = Project(
        organization_id=organization.id,
        slug=f"p-{uuid.uuid4().hex[:8]}",
        name="테스트 프로젝트",
        locale="ko-KR",
        settings={},
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def site(db_session, organization, project):
    from veo.db.models.identity import Site

    row = Site(
        organization_id=organization.id,
        project_id=project.id,
        origin="https://example.com",
        display_name="테스트 사이트",
        is_primary=True,
        crawl_settings={},
    )
    db_session.add(row)
    db_session.flush()
    return row


class TestFlippingJudgementsToPages:
    def test_pages_collect_their_own_failures_and_passes(
        self, db_session, principal, site, scan_result, scan_context
    ):
        from veo.seo.history import save_scan_run
        from veo.seo.pages import page_breakdown

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        breakdown = page_breakdown(
            db_session, principal=principal, scan_run_id=saved.scan_run_id
        )

        assert breakdown is not None
        assert breakdown.pages, "URL 목록을 저장했는데 페이지가 나오지 않는다"
        # 저장 전 원본 판정과 대조 — 뒤집기가 사실을 만들거나 잃으면 안 된다.
        source = {o.check_id: o for o in scan_result.score.outcomes}
        for page in breakdown.pages:
            for check_id in page.failed + page.warned:
                assert page.url in source[check_id].affected_urls, (page.url, check_id)
            for check_id in page.passed:
                assert page.url in source[check_id].evaluated_urls
                assert page.url not in source[check_id].affected_urls

    def test_pages_are_ordered_by_problem_count(
        self, db_session, principal, site, scan_result, scan_context
    ):
        from veo.seo.history import save_scan_run
        from veo.seo.pages import page_breakdown

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        breakdown = page_breakdown(
            db_session, principal=principal, scan_run_id=saved.scan_run_id
        )

        counts = [page.problem_count for page in breakdown.pages]
        assert counts == sorted(counts, reverse=True), "고칠 것 많은 페이지가 먼저여야 한다"

    def test_the_breakdown_carries_no_score_number(self) -> None:
        """페이지 점수 산식은 1.9.0 발행 전이다. 숫자가 생기면 명세 밖의 숫자다."""
        import dataclasses

        from veo.seo.pages import PageChecks

        field_names = {f.name for f in dataclasses.fields(PageChecks)}
        assert "score" not in field_names

    def test_site_checks_come_apart_from_pages_with_a_timestamp(
        self, db_session, principal, site, scan_result, scan_context
    ):
        from veo.seo.history import save_scan_run
        from veo.seo.pages import page_breakdown

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        breakdown = page_breakdown(
            db_session, principal=principal, scan_run_id=saved.scan_run_id
        )

        assert breakdown.measured_at is not None, "SITE 값에 날짜가 없으면 표기할 수 없다"
        assert breakdown.pages, "페이지 자체는 있어야 의미가 있다"
        # 같은 검사가 페이지 축과 사이트 축 양쪽에 나오면 화면이 두 번 그린다.
        page_check_ids = {c for p in breakdown.pages for c in p.failed + p.warned + p.passed}
        assert not any(c.check_id in page_check_ids for c in breakdown.site_checks)


class TestLegacyRunsDoNotInventPages:
    def test_a_run_saved_before_the_columns_reads_back_honestly(
        self, db_session, principal, site, scan_result, scan_context
    ):
        from veo.db.models.analysis import CheckResult
        from veo.seo.history import save_scan_run
        from veo.seo.pages import page_breakdown

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        # 이 칸이 생기기 전의 실행을 재현한다 — NULL 로 되돌린다.
        db_session.query(CheckResult).filter_by(scan_run_id=saved.scan_run_id).update(
            {"affected_urls": None, "evaluated_urls": None}
        )
        db_session.flush()

        breakdown = page_breakdown(
            db_session, principal=principal, scan_run_id=saved.scan_run_id
        )

        assert breakdown is not None
        assert breakdown.pages == ()
        assert breakdown.recorded_before_page_lists is True
        assert any("기록되기 전" in note for note in breakdown.notes_ko)


class TestAnotherOrganisationSeesNothing:
    def test_cross_org_read_is_none(
        self, db_session, principal, other_principal, site, scan_result, scan_context
    ):
        from veo.seo.history import save_scan_run
        from veo.seo.pages import page_breakdown

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )

        assert (
            page_breakdown(
                db_session, principal=other_principal, scan_run_id=saved.scan_run_id
            )
            is None
        )
