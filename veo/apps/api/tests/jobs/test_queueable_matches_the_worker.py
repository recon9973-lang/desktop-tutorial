"""큐로 보내는 종류와 **워커가 실제로 하는 일**이 어긋나지 않는다.

## 왜 이 시험이 있나

`QUEUEABLE` 은 손으로 관리하는 목록이고, 워커의 태스크는 다른 저장소 폴더에 있다.
둘이 어긋나는 방향은 두 가지이고 **한쪽이 훨씬 나쁘다** —

```
큐로 보내는데 워커가 껍데기   → 잡이 아무도 안 집어간 채 QUEUED 로 남는다.
                              화면은 계속 "대기 중". 배경 스레드보다 나쁘다.
워커는 하는데 큐에 없다       → 배경 스레드로 돈다. 재배포하면 사라지지만 돌기는 한다.
```

앞의 것을 막는다. 뒤의 것은 사람이 결정할 문제라 여기서 강제하지 않는다.

## 부르는 사람이 없는 종류는 채우지 않는다

[실측 2026-08-10] 여덟 종류 중 **실제로 잡을 만드는 것은 셋**이다. 나머지 다섯은
이름과 계약 문서에만 있다. 그것들의 껍데기를 채우면 `CORRECTIONS.md` #17 이 말한
"목록이 만들어 낸 과제" 가 된다 — 창구가 있다는 것은 누군가 만들었다는 뜻이지 지금
필요하다는 뜻이 아니다.
"""

from __future__ import annotations

import pathlib
import re

import pytest

pytest.importorskip("pydantic")

from veo.contracts.enums import JobType
from veo.jobs.dispatch import QUEUEABLE

_WORKER_TASKS = (
    pathlib.Path(__file__).resolve().parents[3]
    / "worker"
    / "src"
    / "veo_worker"
    / "runtime"
    / "tasks"
    / "__init__.py"
)


def worker_source() -> str:
    if not _WORKER_TASKS.exists():  # pragma: no cover - 워커가 없는 검사 환경
        pytest.skip("워커 소스가 이 환경에 없다")
    return _WORKER_TASKS.read_text(encoding="utf-8")


def skeleton_types(source: str) -> set[JobType]:
    return {
        job_type
        for job_type in JobType
        if f"_run_phase_zero_skeleton(JobType.{job_type.name}" in source
    }


class TestNoSkeletonIsSentToTheQueue:
    def test_every_queueable_type_has_a_real_worker_task(self) -> None:
        skeletons = QUEUEABLE & skeleton_types(worker_source())

        assert not skeletons, (
            "큐로 보내는데 워커가 껍데기다 — 잡이 QUEUED 로 남는다: "
            f"{sorted(one.name for one in skeletons)}"
        )

    def test_the_three_that_actually_run_are_queueable(self) -> None:
        """돈이 나가거나 오래 걸리는 셋. 배경 스레드는 재배포에 사라진다(기획서 E5)."""
        for job_type in (
            JobType.SEO_SCAN,
            JobType.REVERIFICATION,
            JobType.GEO_OBSERVATION_RUN,
        ):
            assert job_type in QUEUEABLE, f"{job_type.name} 이 큐로 가지 않는다"


class TestTypesNobodySubmitsStayEmpty:
    """부르는 사람이 없는 종류의 껍데기를 채우지 않는다 — `CORRECTIONS.md` #17."""

    NOBODY_SUBMITS = (
        JobType.SITE_CRAWL,
        JobType.GEO_READINESS_SCAN,
        JobType.KEYWORD_LOOKUP,
        JobType.COMPETITOR_COMPARISON,
        JobType.REPORT_EXPORT,
    )

    def test_they_are_not_queueable(self) -> None:
        for job_type in self.NOBODY_SUBMITS:
            assert job_type not in QUEUEABLE

    def test_nothing_in_the_api_submits_them(self) -> None:
        """이 목록이 낡으면 이 시험이 알려 준다 — 누가 잡을 만들기 시작하면 실패한다."""
        src = pathlib.Path(__file__).resolve().parents[2] / "src" / "veo"
        code = "\n".join(
            path.read_text(encoding="utf-8")
            for path in src.rglob("*.py")
            # 목록 자체와 이름표는 "만드는 것" 이 아니다.
            if path.name not in {"enums.py", "queues.py", "dispatch.py"}
        )

        for job_type in self.NOBODY_SUBMITS:
            # `submit(... job_type=JobType.X ...)` 모양만 본다. 이름을 언급하는 것과
            # 잡을 만드는 것은 다르다.
            pattern = re.compile(rf"job_type=JobType\.{job_type.name}\b")
            assert not pattern.search(code), (
                f"{job_type.name} 으로 잡을 만드는 코드가 생겼다 — 워커 태스크를 채우고 "
                "이 목록에서 빼야 한다. 껍데기인 채로 큐에 넣으면 QUEUED 로 남는다"
            )
