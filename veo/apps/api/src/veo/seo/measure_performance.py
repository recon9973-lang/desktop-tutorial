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
import threading
import time
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
from veo.seo.perf_cache import PERFORMANCE_CACHE, PerformanceCache

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
class CallRecord:
    """한 번의 PageSpeed 호출에 대해 **관측한** 사실.

    비용이 아니라 **횟수**가 위험이다. PageSpeed 는 하루 25,000회까지 무료이고 돈은
    들지 않지만, 한도를 넘기면 그날의 모든 고객 진단에서 성능이 측정 불가가 된다.
    그래서 이 기록의 목적은 청구서가 아니라 **한도까지 얼마나 남았는가**다.

    캐시 여부는 추측하지 않는다. 응답이 빨랐다고 캐시라고 적으면 그것은 추론이지
    관측이 아니다(0-A). 대신 구글이 응답에 담아 주는 `analysisUTCTimestamp` 를 본다 —
    우리가 요청을 보내기 **전에** 분석된 것이면 새로 돌린 것이 아니다.
    """

    url: str
    latency_ms: int
    #: 값을 받았는가. 실패도 호출이고 한도를 쓴다.
    succeeded: bool
    #: 실패 사유. 성공이면 ``None``.
    failure_code: str | None = None
    #: 구글이 이 분석을 언제 돌렸는가. 우리 요청보다 앞서면 캐시된 결과다.
    analysed_at: str | None = None
    #: 요청을 보낸 시각. 위 값과 비교하는 기준이라 함께 남긴다.
    requested_at: datetime | None = None

    @property
    def was_cache_hit(self) -> bool | None:
        """캐시된 결과였는가. 판단할 근거가 없으면 ``None``.

        ``False`` 로 단정하지 않는다 — "새로 쟀다" 와 "모른다" 는 다른 사실이고,
        모르는 것을 아는 것처럼 적으면 나중에 그 기록을 아무도 믿을 수 없다.
        """
        if self.analysed_at is None or self.requested_at is None:
            return None
        try:
            analysed = datetime.fromisoformat(self.analysed_at.replace("Z", "+00:00"))
        except ValueError:
            return None
        return analysed < self.requested_at


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
    #: 호출 하나하나의 기록. 사용량을 남기는 쪽이 읽는다.
    #:
    #: 여기서 DB 에 쓰지 않는다. 호출은 스레드에서 병렬로 일어나고 세션은 스레드
    #: 안전하지 않다 — 세션을 넘기면 언젠가 조용히 깨진다. 사실만 들고 나오고,
    #: 쓰는 일은 세션을 가진 쪽이 한 번에 한다.
    calls: tuple[CallRecord, ...] = ()

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
    cache: PerformanceCache | None = None,
) -> PerformanceMeasurement:
    """표본 URL 들의 성능을 재고, 수집기가 읽는 payload 로 만든다.

    자격증명이 없으면 **소켓을 열지 않는다.** 상태만 돌려주고, 수집기는 그 상태를
    보고 "측정 불가 — 자격증명 없음" 이라고 적는다. 없는 값을 그럴듯하게 지어내는
    경로가 아예 없다.

    ``cache`` 는 기본이 **꺼짐**이다. 전역 기억을 기본값으로 두면 이 함수를 직접 부르는
    시험들이 서로의 값을 보게 되고, 그때부터 실패가 실행 순서에 따라 달라진다. 캐시는
    운영 경로(:func:`with_performance`)가 명시적으로 건넨다.
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

    # 이미 재 둔 값은 다시 재지 않는다. 크롤과 동시에 미리 잰 대표 주소가 여기서
    # 걸리고(같은 진단 안), 몇 분 전 진단에서 잰 값도 여기서 걸린다(진단 사이).
    # 구글 한 번 호출이 20~60초라, 한 건만 걸려도 체감이 크게 달라진다.
    cached: dict[str, PageSpeedResult] = {}
    to_measure: list[str] = []
    for url in urls:
        hit = None if cache is None else cache.get(url, str(STRATEGY))
        if hit is None:
            to_measure.append(url)
        else:
            cached[url] = hit.value

    results, failures, calls = _measure_all(caller, to_measure, budget_seconds)
    # 새로 잰 것만 기억에 넣는다 — 캐시에서 온 값을 다시 넣으면 잰 시각이 갱신되어
    # 값은 그대로인데 수명만 늘어난다. 그러면 오래된 값이 영원히 살아남는다.
    if cache is not None:
        for url, value in results.items():
            cache.put(url, str(STRATEGY), value)
    results = {**cached, **results}

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
        calls=tuple(calls),
    )


def _measure_all(
    client: PageSpeedClient, urls: list[str], budget_seconds: float
) -> tuple[dict[str, PageSpeedResult], dict[str, str], list[CallRecord]]:
    """병렬로 재고, 예산 안에 돌아온 것만 모은다.

    한 페이지의 실패가 나머지를 죽이지 않는다. 그리고 **실패를 값으로 바꾸지 않는다** —
    돌아오지 않은 페이지는 그냥 없는 것이고, 표본이 얇아지면 그 사실이 점수에 반영된다.
    """
    measured: dict[str, PageSpeedResult] = {}
    failures: dict[str, str] = {}
    calls: list[CallRecord] = []
    # 잴 것이 없으면 스레드 풀을 만들지 않는다. 캐시가 전부 받아 준 경우가 그렇고,
    # 캐시가 잘 들을수록 자주 오는 길이다 — max_workers=0 은 예외를 던진다.
    if not urls:
        return measured, failures, calls

    requested_at = datetime.now(UTC)
    started = time.monotonic()

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
                    calls.append(
                        _record(url, started, requested_at, ok=False, code=type(exc).__name__)
                    )
                    continue
                if outcome.succeeded and isinstance(outcome.value, PageSpeedResult):
                    measured[url] = outcome.value
                    calls.append(
                        _record(
                            url,
                            started,
                            requested_at,
                            ok=True,
                            analysed_at=outcome.value.lab.analysis_timestamp,
                        )
                    )
                elif outcome.failure is not None:
                    failures[url] = str(outcome.failure.error_code)
                    calls.append(
                        _record(
                            url,
                            started,
                            requested_at,
                            ok=False,
                            code=str(outcome.failure.error_code),
                        )
                    )
        except TimeoutError:
            # 예산을 넘긴 페이지는 못 잰 것으로 남는다. 여기서 기다림을 늘리면
            # 진단 요청 자체가 끊기고, 비용은 이미 나간 뒤다(0-G).
            for url in urls:
                if url not in measured and url not in failures:
                    failures[url] = "BUDGET_EXHAUSTED"
                    # 예산을 넘겼어도 **요청은 나갔다.** 한도를 쓴 것은 사실이므로
                    # 기록에서 빼면 안 된다 — 빼면 남은 한도를 실제보다 많게 센다.
                    calls.append(
                        _record(
                            url, started, requested_at, ok=False, code="BUDGET_EXHAUSTED"
                        )
                    )
    return measured, failures, calls


def _record(
    url: str,
    started: float,
    requested_at: datetime,
    *,
    ok: bool,
    code: str | None = None,
    analysed_at: str | None = None,
) -> CallRecord:
    """호출 하나의 사실을 담는다. 지연 시간은 **묶음 시작부터**의 경과다.

    개별 호출의 시작 시각을 스레드 안에서 재지 않는 이유는, 재려면 스레드에서
    공유 자료를 건드려야 하고 그 순간 이 함수가 동시성 문제를 갖게 되기 때문이다.
    한도 관리에 필요한 것은 정확한 개별 지연이 아니라 **호출이 몇 번 나갔는가**다.
    """
    return CallRecord(
        url=url,
        latency_ms=int((time.monotonic() - started) * 1000),
        succeeded=ok,
        failure_code=code,
        analysed_at=analysed_at,
        requested_at=requested_at,
    )


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
) -> tuple[Any, PerformanceMeasurement | None]:
    """수집 문맥에 성능 측정을 채워 돌려준다. 못 재면 문맥을 그대로 돌려준다.

    측정 결과를 **함께** 돌려주는 이유는 사용량 기록 때문이다. 호출은 여기서 일어나고
    DB 세션은 라우터가 가지고 있다. 세션을 여기로 끌어오면 스레드 안에서 쓰이게 되고
    (SQLAlchemy 세션은 스레드 안전하지 않다) 언젠가 조용히 깨진다. 사실만 넘긴다.

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
        return context, None

    # 표본을 고르려면 관측이 필요하고, 관측은 수집기가 만든다. 여기서 다시 만들지
    # 않는다 — 두 벌이 서로 다른 페이지 목록을 갖는 순간 표본 정책이 깨진다(0-D).
    site = PerformanceUxCollector().observe(context)
    if not site.has_pages:
        return context, None

    # 여기서만 기억을 켠다 — 크롤과 동시에 미리 잰 대표 주소가 이 자리에서 걸린다.
    measurement = measure_performance(
        lab_sample(context, site), credentials=resolved, client=client, cache=PERFORMANCE_CACHE
    )
    if not measurement.payloads:
        return context, measurement

    filled = dataclasses.replace(
        context,
        provider_states={**context.provider_states, **measurement.states},
        provider_payloads={**context.provider_payloads, **measurement.payloads},
    )
    return filled, measurement


def prewarm(target_url: str, *, credentials: PageSpeedCredentials | None = _UNSET,
            cache: PerformanceCache | None = PERFORMANCE_CACHE) -> threading.Thread | None:
    """대표 주소의 성능 측정을 **크롤과 동시에** 시작한다.

    지금까지 순서는 크롤을 끝내고 → 성능을 쟀다. 실측(2026-08-03)으로 172장 크롤이
    47초, 성능이 약 130초였고 둘이 나란히 이어져 180초가 됐다. 그런데 대표 주소는
    크롤이 시작되는 순간 이미 알고 있다 — 기다릴 이유가 없다.

    **효과의 한계를 분명히 한다.** 표본 다섯 장은 이미 병렬로 잰다. 그래서 다섯 중
    하나를 미리 재 둬도 전체 시간은 *가장 느린 한 장*이 정하고, 미리 잰 그 장이 마침
    가장 느렸을 때만 줄어든다(2026-08-03 실측으로 확인). 이 함수의 확실한 이득은
    **재진단**이다 — 캐시에 남은 값이 다음 진단에서 그대로 쓰인다.

    표본 전체를 미리 재지는 않는다. 나머지 네 장은 **어느 페이지가 중요한지**를 크롤이
    알려 준 뒤에야 정해지고, 그 선택은 채점하는 쪽과 같은 함수가 해야 한다(0-D). 여기서
    미리 골라 버리면 "잰 페이지" 와 "재려던 페이지" 가 어긋난다.

    실패해도 조용하다. 미리 재기는 **덤**이라, 실패하면 원래 순서대로 나중에 재면 된다 —
    그래서 여기서 나는 문제로 진단을 멈추지 않는다.

    돌려주는 스레드를 기다릴 필요는 없다. 결과는 캐시에 들어가고, 나중 측정이 그것을
    집어 간다. 아직 안 끝났으면 그때 그냥 다시 잰다.
    """
    # `with_performance` 와 같은 이유로 함수 안에서 읽는다: 기본값이 "설정에서 읽기" 면
    # 시험이 개발자 컴퓨터의 .env 를 타고 진짜 구글로 나간다(0-F).
    from veo.providers.google.credentials import pagespeed_from_settings

    resolved = pagespeed_from_settings().credentials if credentials is _UNSET else credentials
    if resolved is None or cache is None or not target_url.strip():
        return None

    def _work() -> None:
        try:
            client = PageSpeedClient(credentials=resolved)
            outcome = client.measure(target_url, strategy=STRATEGY)
            if outcome.succeeded and isinstance(outcome.value, PageSpeedResult):
                cache.put(target_url, str(STRATEGY), outcome.value)
        except Exception:
            return

    thread = threading.Thread(target=_work, name="veo-perf-prewarm", daemon=True)
    thread.start()
    return thread
