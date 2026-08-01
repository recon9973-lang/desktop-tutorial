"""성능을 실제로 재는 자리 — 어댑터와 스캔 파이프라인을 잇는다.

이 모듈이 생기기 전까지 PageSpeed 어댑터는 **호출자가 하나도 없었다.** 완성돼 있고
시험도 있었지만 아무도 부르지 않았고, 그래서 키를 넣어도 화면에는 계속 "측정 불가"
가 나왔다. 0-E: 부를 수 없는 기능은 없는 기능이다.

## 여기서 지키는 것 넷

**하나. 자격증명은 서버가 스스로 읽는다.** 이전에는 요청 본문의 `provider_states` 를
그대로 믿었다. 브라우저가 "우리 PageSpeed 켜졌어요" 라고 말하면 서버가 그대로
받아들이는 구조였고, 조직 간 격리 관점에서도 옳지 않다. 이제 켜졌는지 아닌지는
서버에 있는 자격증명만이 결정한다.

**둘. 표본은 `lab_sample` 하나로 고른다.** 재는 쪽과 채점하는 쪽이 각자 고르면
"잰 페이지" 와 "재려던 페이지" 가 어긋나고, 그 어긋남은 조용히 점수를 올린다 —
잰 것만 분모에 들어가기 때문이다.

**셋. 못 잰 것을 지어내지 않는다.** 한 페이지가 실패해도 나머지는 계속 재고, 실패한
페이지는 payload 에 넣지 않는다. 그 결과가 표본 문턱에 걸리면 검사는 측정 불가가
되고 배점을 잃는다 — 그것이 정직한 결과다.

**넷. 실사용자 값은 사이트 전체를 한 번만 받는다.** 구글은 같은 응답에
`originLoadingExperience` 로 사이트 전체 값을 함께 준다(2026-08-01 실측, seoul.go.kr:
페이지 값 LCP 1041ms·INP 96ms / 사이트 전체 값 LCP 1011ms·INP 122ms). 페이지마다
따로 받을 이유가 없다.

## 시간

한 장에 16~60초다(실측 16.0 / 24.1 / 28.3 / 59.8). 다섯 장을 차례로 재면 최악 5분이라
요청 안에서 할 수 없다(0-G). 그래서 **병렬로 던지고 전체 예산을 둔다.** 예산을 넘긴
페이지는 못 잰 것으로 남고, 위의 셋째 규칙이 그 뒤를 맡는다.
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from veo.contracts.enums import ProviderState
from veo.providers.google.credentials import PageSpeedCredentials
from veo.providers.google.crux import FieldScope, field_payload, normalize_loading_experience
from veo.providers.google.pagespeed import (
    PageSpeedClient,
    PageSpeedResult,
    Strategy,
    lab_payload,
)

__all__ = [
    "PerformanceMeasurement",
    "measure_performance",
    "with_performance",
]

#: 한 진단이 성능 측정에 쓸 수 있는 전체 시간.
#:
#: 다섯 장을 병렬로 던지므로 대개 가장 느린 한 장의 시간에 가깝다. 실측 최댓값이
#: 59.8초였으니 그 두 배를 둔다 — 여유가 없으면 느린 사이트가 늘 측정 불가가 되고,
#: **느린 사이트야말로 이 지표가 필요한 곳**이다.
TOTAL_BUDGET_SECONDS: Final = 120.0

#: "인자를 주지 않았다" 와 "자격증명이 없다" 를 구분하는 표식.
#:
#: `None` 을 기본값으로 쓰면 둘이 같아진다 — 시험이 "키 없음" 을 표현할 방법이 없고,
#: 그러면 개발자 .env 를 타고 진짜 네트워크로 나간다.
_UNSET: Any = object()

#: 국내 병원 검색은 모바일 중심이다. 명세의 mobile_viewport 검사가 같은 전제 위에 있다.
STRATEGY: Final = Strategy.MOBILE


@dataclass(frozen=True, slots=True)
class PerformanceMeasurement:
    """성능 측정 결과. 제공자 상태와 payload 를 함께 들고 다닌다.

    상태를 payload 와 같이 두는 이유: 둘이 어긋나면 "연동은 켜졌는데 값이 없다" 와
    "연동이 없다" 를 화면이 구분하지 못한다. 둘은 고객에게 전혀 다른 말이다.
    """

    states: Mapping[str, ProviderState]
    payloads: Mapping[str, Mapping[str, Any]]
    #: 재려고 계획한 URL. 실제로 값을 받은 것과 다를 수 있다.
    planned: tuple[str, ...]
    #: 값을 받은 URL.
    measured: tuple[str, ...]
    #: 값을 못 받은 URL 과 그 이유.
    #:
    #: 조용히 빼면 "느려서 열리지 않았다" 와 "우리 쪽이 터졌다" 가 구분되지 않는다.
    #: 앞은 고객에게 알릴 사실이고 뒤는 우리가 고칠 일이라 같은 자리에 두면 안 된다.
    failures: Mapping[str, str] = field(default_factory=dict)

    @property
    def attempted(self) -> int:
        return len(self.planned)


def measure_performance(
    urls: list[str],
    *,
    credentials: PageSpeedCredentials | None,
    unavailable_state: ProviderState = ProviderState.DISABLED_NO_CREDENTIAL,
    client: PageSpeedClient | None = None,
    budget_seconds: float = TOTAL_BUDGET_SECONDS,
) -> PerformanceMeasurement:
    """표본 URL 들의 성능을 재고, 수집기가 읽는 payload 로 만든다.

    자격증명이 없으면 **소켓을 열지 않는다.** 상태만 돌려주고, 수집기는 그 상태를
    보고 "측정 불가 — 자격증명 없음" 이라고 적는다. 없는 값을 그럴듯하게 지어내는
    경로가 아예 없다.
    """
    if credentials is None or not urls:
        return PerformanceMeasurement(
            states={
                "GOOGLE_PAGESPEED": unavailable_state,
                "GOOGLE_CRUX": unavailable_state,
            },
            payloads={},
            planned=tuple(urls),
            measured=(),
        )

    caller = client or PageSpeedClient(credentials=credentials)
    results, failures = _measure_all(caller, urls, budget_seconds)

    lab = lab_payload(result.lab for result in results.values())
    field = field_payload(_field_measurements(results))

    return PerformanceMeasurement(
        states={
            "GOOGLE_PAGESPEED": ProviderState.ENABLED,
            "GOOGLE_CRUX": ProviderState.ENABLED,
        },
        payloads={"GOOGLE_PAGESPEED": lab, "GOOGLE_CRUX": field},
        planned=tuple(urls),
        measured=tuple(results),
        failures=dict(failures),
    )


def _measure_all(
    client: PageSpeedClient, urls: list[str], budget_seconds: float
) -> tuple[dict[str, PageSpeedResult], dict[str, str]]:
    """병렬로 재고, 예산 안에 돌아온 것만 모은다.

    한 페이지의 실패가 나머지를 죽이지 않는다. 그리고 **실패를 값으로 바꾸지 않는다** —
    돌아오지 않은 페이지는 그냥 없는 것이고, 표본이 얇아지면 그 사실이 점수에 반영된다.
    """
    measured: dict[str, PageSpeedResult] = {}
    failures: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)) as pool:
        futures = {
            pool.submit(client.measure, url, strategy=STRATEGY): url for url in urls
        }
        try:
            for future in concurrent.futures.as_completed(futures, timeout=budget_seconds):
                url = futures[future]
                try:
                    outcome = future.result()
                except Exception as exc:
                    # 삼키지 않는다. 왜 못 쟀는지를 잃으면 "느려서 열리지 않았다" 와
                    # "우리 쪽이 터졌다" 가 구분되지 않는다. 앞은 고객에게 알릴
                    # 사실이고 뒤는 우리가 고칠 일이라 같은 자리에 두면 안 된다.
                    failures[url] = type(exc).__name__
                    continue
                if outcome.succeeded and isinstance(outcome.value, PageSpeedResult):
                    measured[url] = outcome.value
                elif outcome.failure is not None:
                    failures[url] = str(outcome.failure.error_code)
        except TimeoutError:
            # 예산을 넘긴 페이지는 못 잰 것으로 남는다. 여기서 기다림을 늘리면
            # 진단 요청 자체가 끊기고, 비용은 이미 나간 뒤다(0-G).
            for url in urls:
                if url not in measured and url not in failures:
                    failures[url] = "BUDGET_EXHAUSTED"
    return measured, failures


def _field_measurements(results: Mapping[str, PageSpeedResult]) -> list[Any]:
    """URL 범위 값에 사이트 전체(origin) 값을 한 번만 더한다.

    같은 origin 을 페이지 수만큼 넣으면 payload 에 같은 사실이 여러 번 들어가고,
    수집기는 그것을 여러 페이지의 판정으로 오해할 수 있다. 첫 응답의 것 하나만 쓴다.
    """
    measurements = [result.field for result in results.values()]

    for result in results.values():
        origin = getattr(result, "origin_field", None)
        if origin is not None:
            measurements.append(origin)
            break
    return measurements


def origin_field_from(
    payload: Mapping[str, Any], *, url: str, collected_at: datetime | None = None
) -> Any:
    """``originLoadingExperience`` 를 사이트 전체 범위 측정으로 옮긴다.

    어댑터가 URL 범위만 읽고 있었다. 같은 응답에 사이트 전체 값이 함께 오는데도
    버리고 있었던 셈이고, 그것을 쓰면 **실사용자 지표에는 표본 문제가 사라진다.**
    """
    block = payload.get("originLoadingExperience")
    if not isinstance(block, Mapping):
        return None
    return normalize_loading_experience(
        block,
        url=block.get("id") or url,
        scope=FieldScope.ORIGIN,
        collected_at=collected_at or datetime.now(UTC),
    )


def with_performance(
    context: Any,
    *,
    credentials: PageSpeedCredentials | None = _UNSET,
    client: PageSpeedClient | None = None,
) -> Any:
    """수집 문맥에 성능 측정을 채워 돌려준다. 못 재면 문맥을 그대로 돌려준다.

    순서가 이 함수의 전부다.

    1. 문맥이 먼저 있어야 **어느 페이지가 중요한지** 알 수 있다(중요도는 명세가 정한다).
    2. 그 중요도로 표본을 고른다 — `lab_sample` 로, 채점하는 쪽과 **같은 함수**로.
    3. 표본만 잰다.
    4. 결과를 문맥에 넣는다.

    2번을 여기서 다시 구현하지 않는 것이 핵심이다. 재는 쪽과 채점하는 쪽이 각자 고르면
    "잰 페이지" 와 "재려던 페이지" 가 어긋나고, 그 어긋남은 조용히 점수를 올린다.

    자격증명이 없으면 **문맥을 손대지 않는다.** `context_from_crawl` 이 이미 설정에서
    provider 상태를 읽어 DISABLED 로 넣어 두었고, 그 상태 그대로가 정직한 결과다 —
    수집기는 그것을 보고 "측정 불가: 자격증명 없음" 이라고 적는다.
    """
    import dataclasses

    from veo.providers.google.credentials import pagespeed_from_settings
    from veo.seo.collectors.performance_ux import PerformanceUxCollector, lab_sample

    # 자격증명을 인자로 받는 이유는 시험 때문만이 아니다. 기본값이 "설정에서 읽기" 면
    # **시험이 개발자 컴퓨터의 .env 를 타고 진짜 구글로 나간다.** 실제로 그렇게 나갔고,
    # 그 시험은 네트워크가 없는 CI 에서 다르게 행동한다(0-F).
    resolved = pagespeed_from_settings().credentials if credentials is _UNSET else credentials
    if resolved is None:
        return context

    # 표본을 고르려면 관측이 필요하고, 관측은 수집기가 만든다. 여기서 다시 만들지
    # 않는다 — 두 벌이 서로 다른 페이지 목록을 갖는 순간 표본 정책이 깨진다(0-D).
    site = PerformanceUxCollector().observe(context)
    if not site.has_pages:
        return context

    measurement = measure_performance(
        lab_sample(context, site), credentials=resolved, client=client
    )
    if not measurement.payloads:
        return context

    return dataclasses.replace(
        context,
        provider_states={**context.provider_states, **measurement.states},
        provider_payloads={**context.provider_payloads, **measurement.payloads},
    )
