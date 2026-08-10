"""공개 진단 리미터는 **프로세스 안**에 산다 — 프로세스가 하나라서 맞다.

## 무엇이 실제 상태인가

기획서 E6 은 *"공개 레이트리미터 프로세스 내 인메모리 — 워커 2개면 실효 한도 2배"* 를
중간 심각도로 적어 두었다. [실측 2026-08-10] 재보니 —

```
infra/docker/api.Dockerfile   uvicorn … (--workers 없음)   → 프로세스 1
railway.json                  numReplicas 없음             → 복제본 1
```

프로세스가 하나면 인메모리 리미터가 **정확하다.** Redis 로 빼면 얻는 것은 없고,
새 의존성과 새 실패 모드(브로커가 죽으면 공개 진단이 멈춘다)가 는다.

## 그러면 왜 시험이 있나

**리미터가 지키는 것은 우리 서버가 아니라 남의 서버다.** 호스트 버킷은 우리가 진단하러
가는 **거래처가 아닌 사이트**를 보호한다 — 그 사이트 주인은 우리와 계약한 적이 없고,
우리가 얼마나 두드릴지 정한 적도 없다.

프로세스를 둘로 늘리면 그 약속이 **조용히 두 배로 깨진다.** 그리고 그 변화는
`--workers 4` 한 줄이나 `numReplicas: 2` 한 줄로 들어온다 — 성능을 올리려는 평범한
작업이고, 그때 남의 서버를 떠올릴 이유가 없다.

이 시험이 그 자리를 지킨다.

같은 모양의 관문 —
`test_vault_is_needed_when_a_second_org_appears.py`(조직이 둘이 되는 순간),
`test_queueable_matches_the_worker.py`(껍데기를 큐로 보내는 것).
"""

from __future__ import annotations

import pathlib
import re

import pytest

pytest.importorskip("pydantic")

#: `veo/` 뿌리. 이 파일은 `veo/apps/api/tests/public/` 에 있다.
_REPO = pathlib.Path(__file__).resolve().parents[4]

_SHARE_THE_LIMITER_FIRST = (
    "프로세스가 둘 이상이 됩니다. **리미터를 먼저 공유 저장소로 옮겨야 합니다** — "
    "지금 리미터는 프로세스 안의 사전이라, 프로세스가 N 개면 실효 한도가 N 배가 "
    "됩니다.\n"
    "그 한도는 우리 서버가 아니라 **우리가 진단하러 가는 남의 사이트**를 지킵니다. "
    "그 주인은 우리와 계약한 적이 없고 얼마나 두드릴지 정한 적도 없습니다.\n"
    "옮길 자리: `veo/public/limits.py` 의 `RateLimiter` 프로토콜 뒤에 Redis 구현을 "
    "끼웁니다 — `settings.redis_url` 이 이미 있습니다"
    "(`veo/public/INTEGRATION_REQUEST.md` §4)."
)


class TestOneProcessIsWhatMakesTheInMemoryLimiterCorrect:
    def test_the_container_runs_a_single_uvicorn_process(self) -> None:
        dockerfile = (_REPO / "infra" / "docker" / "api.Dockerfile").read_text(encoding="utf-8")

        # `--workers N` 이 들어오면 한 컨테이너 안에서 프로세스가 갈라진다.
        assert not re.search(r"--workers\s", dockerfile), _SHARE_THE_LIMITER_FIRST

    def test_railway_does_not_ask_for_replicas(self) -> None:
        railway = (_REPO / "railway.json").read_text(encoding="utf-8")

        # 복제본을 늘리면 컨테이너 자체가 여럿이 된다 — 사전은 각자 따로 산다.
        assert "numReplicas" not in railway, _SHARE_THE_LIMITER_FIRST


class TestTheSeamIsAlreadyThere:
    """다음 사람이 처음부터 짓지 않도록, 갈아끼울 자리가 있다는 사실을 못박는다."""

    def test_the_limiter_is_a_protocol_not_a_hardcoded_class(self) -> None:
        from veo.public.limits import RateLimiter

        assert hasattr(RateLimiter, "acquire")

    def test_a_redis_url_setting_already_exists(self) -> None:
        from veo.core.settings import Settings

        assert "redis_url" in Settings.model_fields, (
            "옮길 때 새 설정을 만들 필요가 없다 — 이미 있다"
        )


class TestWhatTheLimiterActuallyProtects:
    def test_it_charges_a_bucket_per_target_host(self) -> None:
        """이 사실이 사라지면 위 시험들의 이유가 사라진다.

        호스트 버킷이 없어지면 남는 것은 우리 자원을 지키는 버킷뿐이고, 그때는
        프로세스가 늘어도 남에게 해가 가지 않는다.
        """
        source = (
            _REPO / "apps" / "api" / "src" / "veo" / "public" / "limits.py"
        ).read_text(encoding="utf-8")

        assert "public_target_host_limit_per_hour" in source
