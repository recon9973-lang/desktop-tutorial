"""재검사를 누르면 **재측정이 실제로 시작된다.**

## 왜 이 시험이 없어서 문제가 생겼나

이슈의 상태 기계에는 시험이 많았다 — 어떤 전이가 허용되는지, 사람이
`VERIFIED_RESOLVED` 를 쓸 수 없는지, `WARNING` 이 통과가 아닌지. 전부 **규칙**의 시험이다.

없던 것은 **그 규칙이 실제로 돌아가는지**의 시험이었다. `request_verification` 은
상태를 옮기고 요청서를 만들어 돌려줬고, 시험들은 그 두 가지를 확인했다. 아무도
"그래서 재측정이 시작됐는가" 를 묻지 않았다.

**[실측] 2026-08-09 운영 DB — 이슈 165건 전부 `OPEN`, `verification_runs` 0행.**
같은 프로젝트를 16번 재측정한 곳도 그랬다. 규칙은 완벽했고 실행이 없었다.

이 파일은 그 자리를 지킨다.
"""

from __future__ import annotations

import pathlib

import pytest

pytest.importorskip("pydantic")


class TestRequestingVerificationStartsAMeasurement:
    def test_the_endpoint_dispatches_a_reverification_job(self) -> None:
        """창구가 작업을 **건다**. 상태만 옮기고 끝나면 이슈는 영영 안 닫힌다."""
        from veo.issues import router

        source = pathlib.Path(router.__file__).read_text(encoding="utf-8")
        assert "_start_reverification" in source, (
            "재검사 요청이 재측정을 걸지 않는다 — 상태만 옮기면 이슈는 닫히지 않는다"
        )
        assert "dispatch(" in source, "작업을 만들기만 하고 보내지 않으면 아무도 안 집어간다"

    def test_the_job_type_is_reverification_not_a_full_scan(self) -> None:
        """전체 진단으로 대신하면 거래처 서버를 몇 시간 두드린다."""
        from veo.issues import router

        source = pathlib.Path(router.__file__).read_text(encoding="utf-8")
        assert "JobType.REVERIFICATION" in source
        assert "JobType.SEO_SCAN" not in source


class TestTheWorkIsNarrowByConstruction:
    """ "canonical 하나 고쳤나" 를 묻자고 사이트 200장을 다시 기어가면 안 된다."""

    def test_the_work_never_discovers_more_urls(self) -> None:
        from veo.issues import reverify

        source = pathlib.Path(reverify.__file__).read_text(encoding="utf-8")
        assert "discover=False" in source, "표적 재측정이 스스로 링크를 따라가면 표적이 아니다"

    def test_the_work_reuses_the_one_scoring_pipeline(self) -> None:
        """채점 경로가 두 벌이 되는 순간 한쪽만 고쳐지는 날이 온다."""
        from veo.issues import reverify

        source = pathlib.Path(reverify.__file__).read_text(encoding="utf-8")
        assert "run_console_scan" in source


class TestTheVerdictStaysWithTheMeasurement:
    """이 작업은 결론을 **정하지 않는다.** 저장된 판정에서 도출될 뿐이다."""

    def test_the_work_names_no_outcome(self) -> None:
        from veo.issues import reverify

        source = pathlib.Path(reverify.__file__).read_text(encoding="utf-8")
        # 결론을 직접 쓰는 낱말이 코드에 있으면 안 된다 — 문서 문자열은 예외로 두기
        # 위해, 대입·인자 모양으로 쓰였는지만 본다.
        for forbidden in ("outcome=VerificationOutcome.RESOLVED", 'outcome="RESOLVED"'):
            assert forbidden not in source, (
                f"재측정 작업이 결론을 직접 쓴다({forbidden}) — 판정은 측정에서만 나온다"
            )

    def test_it_hands_the_run_id_to_the_recorder(self) -> None:
        from veo.issues import reverify

        source = pathlib.Path(reverify.__file__).read_text(encoding="utf-8")
        assert "record_verification_outcome" in source
        assert "scan_run_id=saved_run_id" in source, (
            "저장된 실행을 넘겨야 그쪽이 check_results 를 읽어 판정한다"
        )

    def test_an_unsaved_run_fails_instead_of_guessing(self) -> None:
        """저장이 없으면 판정할 근거가 없다. 이슈는 `VERIFYING` 인 채로 남는 편이 낫다."""
        from veo.issues import reverify

        source = pathlib.Path(reverify.__file__).read_text(encoding="utf-8")
        assert "RUN_NOT_SAVED" in source


class TestItDoesNotGoToAQueueThatCannotDoTheWork:
    def test_reverification_is_not_queueable_while_the_worker_is_a_stub(self) -> None:
        """워커의 재검증 태스크는 아직 뼈대다(`Phase 2 에 온다`).

        큐로 보내면 아무도 집어가지 않은 채 대기하고, 그것은 지금보다 나쁘다.
        워커가 실제로 일을 하게 되는 날 이 시험을 **의도적으로** 고치면 된다.
        """
        from veo.contracts.enums import JobType
        from veo.jobs.dispatch import QUEUEABLE

        assert JobType.REVERIFICATION not in QUEUEABLE


class TestTheResponseSaysWhetherItStarted:
    def test_the_payload_carries_a_job_id(self) -> None:
        """화면이 "재측정이 시작됐다" 와 "상태만 바뀌었다" 를 구별할 수 있어야 한다."""
        from veo.issues.schemas import VerificationRequestedPayload

        assert "job_id" in VerificationRequestedPayload.model_fields

    def test_the_job_id_may_be_absent(self) -> None:
        """사이트를 못 찾으면 작업 없이 넘어간다 — 그때 `null` 이 사실이다."""
        from veo.issues.schemas import VerificationRequestedPayload

        field = VerificationRequestedPayload.model_fields["job_id"]
        assert field.default is None


class TestTheWorkerStubIsStillMarked:
    """뼈대를 뼈대라고 적어 두는 것도 지켜야 하는 사실이다."""

    def test_the_worker_task_still_says_it_is_not_implemented(self) -> None:
        worker = (
            pathlib.Path(__file__).resolve().parents[3]
            / "worker"
            / "src"
            / "veo_worker"
            / "runtime"
            / "tasks"
            / "__init__.py"
        )
        if not worker.exists():  # pragma: no cover - 워커가 없는 검사 환경
            pytest.skip("워커 소스가 이 환경에 없다")
        source = worker.read_text(encoding="utf-8")
        assert "REVERIFICATION" in source
