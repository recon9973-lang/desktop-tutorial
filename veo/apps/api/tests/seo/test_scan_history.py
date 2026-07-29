"""진단 결과를 남기는 규칙.

지금까지 진단은 채점하고 **버렸다.** 그래서 "지난달보다 나아졌나" 에 답할 수 없었고,
고객에게 낼 보고서도 매번 새로 뽑는 단발성 숫자였다. 기획서 §10 은 방법론 버전이 바뀌어도
과거 점수를 보존하라고 요구하고, 구현계획 3단계는 이슈의 재발 추적을 요구한다. 둘 다
결과가 남아 있어야 성립한다.

여기서 고정하는 것:

* 한 번의 진단은 `ScanRun` 한 줄과 `ScoreResult` 한 줄을 남긴다 — 시계열의 단위다.
* 항목별 판정과 근거도 남긴다. 점수만 남기면 "왜 35점이었는지" 를 나중에 설명할 수 없다.
* 같은 문제가 다시 잡히면 **새 이슈를 만들지 않고** 기존 이슈를 갱신한다. 매번 새로 만들면
  이슈 목록이 진단 횟수만큼 불어나고, 담당자 배정과 재검증 이력이 끊긴다.
* 다른 조직의 사이트에는 저장하지 못한다.
"""

from __future__ import annotations

import uuid

import pytest

pytest.importorskip("sqlalchemy")


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


class TestSavingOneRun:
    def test_a_run_and_its_score_are_recorded(self, db_session, principal, site, scan_result):
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session,
            principal=principal,
            site_id=site.id,
            result=scan_result,
            urls_attempted=3,
            urls_collected=3,
        )

        assert saved.score is not None
        assert saved.spec_version != ""
        assert saved.finished_at is not None

    def test_check_results_are_recorded_so_the_score_can_be_explained(
        self, db_session, principal, site, scan_result
    ):
        from veo.db.models.analysis import CheckResult
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )

        rows = db_session.query(CheckResult).filter_by(scan_run_id=saved.scan_run_id).all()
        assert len(rows) == len(scan_result.score.outcomes)

    def test_the_reason_a_check_was_unmeasurable_survives(
        self, db_session, principal, site, scan_result
    ):
        """'측정 불가' 만 남기면 나중에 고장으로 읽힌다. 이유가 함께 남아야 한다."""
        from veo.db.models.analysis import CheckResult
        from veo.seo.history import save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )

        unknown = (
            db_session.query(CheckResult)
            .filter_by(scan_run_id=saved.scan_run_id, status="UNKNOWN")
            .all()
        )
        assert unknown, "이 fixture 는 측정 불가 항목을 포함해야 한다"
        assert all(row.unknown_reason for row in unknown)


class TestHistory:
    def test_two_runs_read_back_newest_first(self, db_session, principal, site, scan_result):
        from veo.seo.history import read_scan_history, save_scan_run

        for _ in range(2):
            save_scan_run(
                db_session, principal=principal, site_id=site.id, result=scan_result,
                urls_attempted=1, urls_collected=1,
            )

        history = read_scan_history(db_session, principal=principal, site_id=site.id)

        assert len(history) == 2
        assert history[0].started_at >= history[1].started_at

    def test_another_organization_cannot_read_this_history(
        self, db_session, principal, other_principal, site, scan_result
    ):
        from veo.seo.history import read_scan_history, save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )

        assert read_scan_history(db_session, principal=other_principal, site_id=site.id) == []


class TestIssueLifecycle:
    def test_the_same_problem_twice_updates_one_issue(
        self, db_session, principal, site, project, scan_result
    ):
        from veo.db.models.analysis import Issue
        from veo.seo.history import save_scan_run

        first = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )
        second = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )

        issues = db_session.query(Issue).filter_by(project_id=project.id).all()
        assert len(issues) == len({issue.check_id for issue in issues}), (
            "같은 검사 항목으로 이슈가 두 줄 생기면 안 된다"
        )
        assert all(issue.first_seen_run_id == first.scan_run_id for issue in issues)
        assert all(issue.last_seen_run_id == second.scan_run_id for issue in issues)

    def test_a_resolved_problem_that_returns_is_counted_as_a_regression(
        self, db_session, principal, site, project, scan_result
    ):
        """고쳤다가 다시 깨진 것과 한 번도 못 고친 것은 다른 사건이다."""
        from veo.db.models.analysis import Issue
        from veo.seo.history import save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )
        resolved = db_session.query(Issue).filter_by(project_id=project.id).first()
        assert resolved is not None
        resolved.state = "VERIFIED_RESOLVED"
        db_session.flush()

        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )
        db_session.refresh(resolved)

        assert resolved.state == "RECURRED"
        assert resolved.regression_count == 1


class TestReadingAPastRunBack:
    """화면을 닫았다 다시 열면 지난 결과가 그대로 보여야 한다.

    같은 도메인을 하루에도 몇 번씩 다시 재는 것은 대상 사이트에도, 우리 쪽 비용에도
    부담이다. 변경을 확인하려고 **일부러** 다시 재는 경우가 아니면 다시 재지 않는다.
    그러려면 저장된 결과를 그대로 되읽을 수 있어야 한다.
    """

    def test_the_report_comes_back_exactly_as_it_was_shown(
        self, db_session, principal, site, scan_result
    ):
        from veo.seo.history import read_scan_report, save_scan_run

        snapshot = {"summary_ko": "그때의 요약", "issues": [{"check_id": "x"}]}
        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1, report_snapshot=snapshot,
        )

        assert read_scan_report(
            db_session, principal=principal, scan_run_id=saved.scan_run_id
        ) == snapshot

    def test_another_organization_cannot_read_the_report(
        self, db_session, principal, other_principal, site, scan_result
    ):
        from veo.seo.history import read_scan_report, save_scan_run

        saved = save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1, report_snapshot={"summary_ko": "비밀"},
        )

        assert read_scan_report(
            db_session, principal=other_principal, scan_run_id=saved.scan_run_id
        ) is None


class TestWhoRanIt:
    def test_the_history_names_the_person_who_ran_the_scan(
        self, db_session, principal, site, scan_result, user
    ):
        """'언제' 만으로는 부족하다. 직원 여럿이 같은 사이트를 만진다."""
        from veo.seo.history import read_scan_history, save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )

        entry = read_scan_history(db_session, principal=principal, site_id=site.id)[0]
        assert entry.requested_by_name == user.display_name

    def test_a_departed_employee_does_not_take_the_history_with_them(
        self, db_session, principal, site, scan_result, user
    ):
        from veo.db.models.identity import User
        from veo.seo.history import read_scan_history, save_scan_run

        save_scan_run(
            db_session, principal=principal, site_id=site.id, result=scan_result,
            urls_attempted=1, urls_collected=1,
        )
        db_session.delete(db_session.get(User, user.id))
        db_session.flush()

        history = read_scan_history(db_session, principal=principal, site_id=site.id)
        assert len(history) == 1
        assert history[0].requested_by_name is None
