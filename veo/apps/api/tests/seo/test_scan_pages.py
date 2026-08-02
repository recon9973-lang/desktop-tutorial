"""페이지 축 재집계 — "canonical 문제 103장" 을 "이 페이지의 문제 목록" 으로.

이 파일이 지키는 성질:

1. 판정 규칙 — 걸린 페이지는 그 행의 상태 그대로, 판정됐지만 안 걸린 페이지는 통과,
   어느 목록에도 없는 페이지·검사 조합은 **아예 나오지 않는다** (통과와 미측정을
   섞으면 페이지가 실제보다 건강해 보인다).
2. 페이지 점수(1.9.0+) — 저장된 판정에서 재크롤 없이 계산되고, 항등식이 응답
   안에서 성립하며, 표본 밖 성능 검사는 여기서 NOT_SAMPLED 로 처음 발행된다.
   1.9.0 이전 명세로 저장된 실행은 점수 없이 이유를 말한다(ADR 0012).
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

    def test_a_1_9_0_run_carries_page_scores_with_their_identity(
        self, db_session, principal, site, scan_result, scan_context
    ):
        """이전 시험은 "점수 필드가 없다" 를 못박았다 — 1.9.0 발행 전의 사실이었고,
        발행과 함께 이름째 바꾼다(0-I): 이제 점수가 있고, 항등식이 성립해야 한다."""
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

        scored = [p for p in breakdown.pages if p.score is not None]
        assert scored, "1.9.0 실행인데 점수가 하나도 없다"
        for page in scored:
            score = page.score
            assert score.spec_version == "1.9.0"
            if score.status == "SCORED":
                assert score.quality == pytest.approx(
                    100.0 - sum(loss.lost for loss in score.losses), abs=1e-6
                )
                assert score.score == pytest.approx(
                    score.reach * score.quality, abs=1e-6
                )

    def test_a_run_scored_with_an_older_spec_gets_no_page_score(
        self, db_session, principal, site, scan_result, scan_context
    ):
        """1.8.0 의 규칙에는 NOT_SAMPLED 가 없다 — 그 판의 이름으로 그 판에 없던
        산수를 하지 않는다(ADR 0012). 점수 대신 이유가 나간다."""
        from sqlalchemy import text

        from veo.seo.history import save_scan_run
        from veo.seo.pages import page_breakdown

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1,
        )
        # ScoreResult 는 불변 기록이라 ORM 으로 못 고친다 — "1.8.0 으로 채점된 옛
        # 실행" 을 흉내내는 시험이므로 SQL 로 직접 되돌린다.
        db_session.execute(
            text("update score_results set spec_version='1.8.0' where scan_run_id=:r"),
            {"r": saved.scan_run_id},
        )
        db_session.expire_all()

        breakdown = page_breakdown(
            db_session, principal=principal, scan_run_id=saved.scan_run_id
        )

        assert breakdown.pages
        assert all(page.score is None for page in breakdown.pages)
        assert any("1.9.0 이전" in note for note in breakdown.notes_ko)

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


class TestTurningRowsIntoPageOutcomes:
    """_score_page 의 변환 규칙 — 저장 행 하나가 페이지 판정 하나가 되는 자리."""

    @staticmethod
    def _row(check_id, status, *, affected=None, evaluated=None, confidence=1.0):  # type: ignore[no-untyped-def]
        from types import SimpleNamespace

        return SimpleNamespace(
            check_id=check_id,
            status=status,
            confidence=confidence,
            affected_urls=affected,
            evaluated_urls=evaluated,
            evidence_ids=[],
        )

    def test_a_sampled_perf_check_off_the_sample_becomes_not_sampled(self) -> None:
        """NOT_SAMPLED 가 실제로 발행되는 유일한 자리 — 표본 밖 페이지의 성능 검사."""
        from veo.scoring import latest_published
        from veo.seo.pages import _score_page

        spec = latest_published("veo.seo.readiness")
        page = "https://clinic.example/sub/"
        rows = [
            self._row(
                "seo.perf.lcp_lab", "PASS",
                affected=[], evaluated=["https://clinic.example/"],
            ),
            self._row(
                "seo.onpage.single_meaningful_h1", "PASS",
                affected=[], evaluated=[page],
            ),
        ]
        score = _score_page(spec, rows, page)

        assert score is not None
        assert "seo.perf.lcp_lab" in score.not_sampled
        assert score.score == 100.0, "표본 밖은 감점이 아니다"

    def test_a_check_unknown_everywhere_stays_unknown_on_every_page(self) -> None:
        """재려다 실패한 것은 페이지에서도 아프다 — 분모에 남는다."""
        from veo.scoring import latest_published
        from veo.seo.pages import _score_page

        spec = latest_published("veo.seo.readiness")
        page = "https://clinic.example/"
        rows = [
            self._row("seo.perf.lcp_lab", "UNKNOWN", affected=None, evaluated=None),
            self._row(
                "seo.onpage.single_meaningful_h1", "PASS",
                affected=[], evaluated=[page],
            ),
        ]
        score = _score_page(spec, rows, page)

        assert score is not None
        assert "seo.perf.lcp_lab" in score.unmeasured
        assert score.score is not None and score.score < 100.0

    def test_rows_from_before_the_columns_supply_nothing(self) -> None:
        from veo.scoring import latest_published
        from veo.seo.pages import _score_page

        spec = latest_published("veo.seo.readiness")
        rows = [
            self._row(
                "seo.onpage.single_meaningful_h1", "FAIL",
                affected=None, evaluated=None,
            ),
        ]
        assert _score_page(spec, rows, "https://clinic.example/") is None
