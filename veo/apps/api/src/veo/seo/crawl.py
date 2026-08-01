"""콘솔 진단의 수집 단계.

무료 공개 진단은 한 페이지만 본다(`public_max_urls_per_scan = 1`). 한 페이지로는
내부 링크·중복 메타데이터·클릭 깊이처럼 **사이트를 봐야 판정되는 항목**이 전부
UNKNOWN 으로 남고, 측정 범위가 60% 근처에서 멈춘다. 그 상태의 보고서를 고객에게
낼 수는 없다.

그래서 콘솔은 더 많이 본다. **더 많이 보는 것 말고는 아무것도 바꾸지 않는다** —
SSRF 차단, 대상 호스트 예산, 응답 크기·시간 상한은 공개 진단과 같은 구현을 쓴다.
로그인했다는 사실은 남의 서버를 두드려도 된다는 뜻이 아니고, 계정은 탈취된다.

주소를 **찾는** 일은 `discovery.py` 가 하고, 여기서는 찾은 주소를 가져오는 일만 한다.
가져오기와 발견을 나눠 두면 발견 규칙을 네트워크 없이 시험할 수 있다.

수집 실패를 다루는 규칙
-----------------------
**진입 페이지를 못 가져오면 진단이 성립하지 않는다.** 그때는 예전처럼 거절한다.
그 밖의 페이지는 다르다. 사이트 전체를 도는 동안 404 나 시간 초과가 한 장도 없는
사이트는 없고, 그것 때문에 진단 전체를 502 로 버리면 **사이트가 클수록 진단이 실패할
확률이 올라간다.** 못 가져온 페이지는 이유와 함께 결과에 남고, 나머지로 채점한다.
그것이 "몇 장을 보고 내린 판단인가" 에 답할 수 있는 유일한 형태다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import final
from urllib.parse import urlsplit

import httpx

from veo.common.security.fetcher import FetchedDocument, FetchError, SafeFetcher
from veo.common.security.limits import FetchLimitError
from veo.common.security.url_guard import UrlGuard, UrlRejectedError
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiError
from veo.core.settings import Settings, get_settings
from veo.public.limits import (
    TARGET_HOST_WINDOW_SECONDS,
    HostBudgetExceeded,
    HostBudgetGuard,
    InMemoryRateLimiter,
    RateLimiter,
)
from veo.seo.discovery import (
    DiscoveredUrl,
    DiscoverySource,
    build_frontier,
    links_on_page,
    sitemap_candidates,
    sitemap_index_targets,
    urls_in_sitemaps,
)
from veo.seo.parsing.robots import RobotsFile, parse_robots
from veo.seo.parsing.urls import normalise_url
from veo.seo.template_groups import group_key

_UNREACHABLE_KO = (
    "대상 사이트에서 응답을 받지 못했습니다. 주소와 사이트 상태를 확인해 주십시오. "
    "이 결과는 VEO 의 오류가 아니라 대상 쪽 상태입니다."
)


def _apply_group_sampling(
    frontier: Sequence[DiscoveredUrl],
    group_fetched: Mapping[str, int],
    sample_cap: int,
) -> tuple[tuple[DiscoveredUrl, ...], dict[str, int]]:
    """그룹당 표본 상한을 넘는 주소를 프런티어에서 덜어낸다.

    사람이 직접 지정한 주소(SEED)는 덜어내지 않는다 — 시킨 일이지 우리가 넓힌
    범위가 아니고, 직원이 특정 글을 진단하려는 경우가 실제로 있다.

    같은 배치 안의 같은 그룹도 함께 센다. 배치 단위로만 세면 첫 배치에 그룹 전체가
    들어올 때 상한이 무의미해진다.
    """
    kept: list[DiscoveredUrl] = []
    skipped: dict[str, int] = {}
    planned: dict[str, int] = dict(group_fetched)
    for record in frontier:
        key = None if record.source is DiscoverySource.SEED else group_key(record.url)
        if key is None:
            kept.append(record)
            continue
        if planned.get(key, 0) >= sample_cap:
            skipped[key] = skipped.get(key, 0) + 1
            continue
        planned[key] = planned.get(key, 0) + 1
        kept.append(record)
    return tuple(kept), skipped


class CrawlRefusal(Exception):
    """수집을 시작하지 못했거나 끝내지 못한 이유. 라우터가 그대로 응답으로 옮긴다."""

    def __init__(self, status_code: int, error: ApiError) -> None:
        super().__init__(error.message)
        self.status_code = status_code
        self.error = error


@final
@dataclass(frozen=True, slots=True)
class CrawlFailure:
    """가져오지 못한 주소 하나와 그 이유.

    이유를 한국어 한 문장으로 남기는 것은 화면에 그대로 띄우기 위해서다. "측정 불가"
    만 있고 왜인지가 없으면 고장으로 읽힌다.
    """

    url: str
    reason_ko: str


@final
@dataclass(frozen=True, slots=True)
class CrawlOutcome:
    """한 번의 수집이 실제로 무엇을 봤는가.

    문서만 돌려주면 "몇 장을 보려 했는데 몇 장을 봤는가" 가 사라진다. 그 둘이 다르다는
    사실 자체가 진단의 신뢰도이므로 함께 돌려준다.
    """

    documents: tuple[FetchedDocument, ...]
    robots_txt: str | None = None
    sitemaps: Mapping[str, str] = field(default_factory=dict)
    discovered: Mapping[str, DiscoveredUrl] = field(default_factory=dict)
    failures: tuple[CrawlFailure, ...] = ()
    robots_blocked: tuple[str, ...] = ()
    budget_exhausted: bool = False
    """대상 호스트 예산이 바닥나 크롤을 일찍 멈췄는가. 사이트가 작아서 적게 본 것과
    우리가 더 못 본 것은 다른 사실이다."""
    collapsed_urls: tuple[str, ...] = ()
    """가져와 보니 **이미 가진 페이지**였던 주소들.

    리다이렉트는 요청을 보내야만 알 수 있다. 실측에서 25번 가져온 것 가운데 15번이 같은
    페이지(`/`)로 떨어졌고, 그래서 채점기가 실제로 본 것은 11장이었다. 그때 "25장을
    봤다" 고 세면 측정 범위를 부풀리는 것이 된다 — 우리가 보지 않은 것을 본 것처럼
    말하는 형태다.

    같은 곳으로 떨어진 주소는 문서로 세지 않고 여기에 남긴다. 그 사실 자체도 진단
    재료다: 서로 다른 주소 열다섯 개가 한 페이지로 모인다면 그 사이트에 볼 것이 있다.
    """
    discovery_exhausted: bool = False
    """가져올 주소가 없어져서 멈췄는가 — 상한이나 예산에 걸려 멈춘 것이 아니라.

    이 값이 페이지 간 비교 검사의 판정을 가른다. 한 장만 있을 때 그것이 "사이트가 한
    장짜리" 인지 "우리가 한 장만 봤는지" 를 여기서만 알 수 있고, 두 답은 점수에서
    정반대로 움직인다(ADR 0016). 기본값이 거짓인 것은 의도한 것이다 — 확인하지 않은
    것을 확인한 것으로 접으면 안 된다.

    템플릿 그룹 표본으로 건너뛴 주소가 하나라도 있으면 이 값은 참이 될 수 없다 —
    표본은 수집 전략이지 "다 봤다" 가 아니다."""
    sampled_out: Mapping[str, int] = field(default_factory=dict)
    """템플릿 그룹 표본 상한에 걸려 **가져오지 않은** 주소 수, 그룹 키별.

    블로그형 자동 생성 페이지는 그룹당 표본 몇 장이면 템플릿 결함이 잡히므로
    (docs/research/SEO_SCORING_V3_PAGES.md §9), 나머지는 요청을 보내지 않고 여기
    수를 남긴다. 실패도 차단도 아니다 — 우리가 안 본 것이고, 그 사실이 결과에
    고지로 나간다."""
    group_fetched: Mapping[str, int] = field(default_factory=dict)
    """그룹 키별로 실제 가져온 표본 수. ``sampled_out`` 과 짝으로 읽는다."""

    @property
    def attempted(self) -> int:
        return len(self.documents) + len(self.failures)

    @property
    def primary(self) -> FetchedDocument | None:
        return self.documents[0] if self.documents else None


@final
class ConsoleCrawler:
    """진단 대상 페이지·robots.txt·사이트맵을 가져온다. 그 밖의 요청은 보내지 않는다."""

    __slots__ = (
        "_concurrency",
        "_fetcher",
        "_group_sample",
        "_max_depth",
        "_max_sitemaps",
        "_max_urls",
        "_settings",
    )

    def __init__(
        self,
        *,
        guard: UrlGuard | None = None,
        transport: httpx.BaseTransport | None = None,
        limiter: RateLimiter | None = None,
        settings: Settings | None = None,
        max_urls: int | None = None,
    ) -> None:
        resolved = settings or get_settings()
        self._settings = resolved
        self._max_urls = max_urls or resolved.console_max_urls_per_scan
        self._max_depth = resolved.console_crawl_max_depth
        self._max_sitemaps = resolved.console_crawl_max_sitemaps
        self._group_sample = max(1, resolved.console_crawl_group_sample)
        self._concurrency = max(1, resolved.console_crawl_concurrency)
        # 공개 진단과 같은 조립이다. 호스트 예산은 **가드 안에서** 부과되어야 한다 —
        # 서비스에서 제출된 URL 로 부과하면 리다이렉트가 그 계산을 우회하고, 실제로
        # 10회 제한에 80회를 흘려보내는 것이 재현된 적이 있다.
        self._fetcher = SafeFetcher(
            guard=HostBudgetGuard(
                guard or UrlGuard(),
                limiter=limiter or InMemoryRateLimiter(),
                limit=resolved.console_target_host_limit_per_hour,
                window_seconds=TARGET_HOST_WINDOW_SECONDS,
            ),
            transport=transport,
        )

    # ------------------------------------------------------------- 주소를 받아 가져오기

    def collect(
        self, urls: Sequence[str]
    ) -> tuple[tuple[FetchedDocument, ...], str | None]:
        """지정된 주소만 가져온다. 스스로 찾아 돌지 않는다.

        발견 크롤(:meth:`crawl`)이 생기기 전부터 있던 경로다. 직원이 볼 주소를 정확히
        알고 있을 때는 이쪽이 맞다 — 사이트가 링크로 잇지 않은 페이지를 일부러 진단할
        수 있어야 하고, 그때 우리가 찾은 다른 페이지를 섞으면 시키지 않은 일이 된다.
        """
        targets = self._accept(urls)
        documents = tuple(self._fetch(url) for url in targets)
        return documents, self._fetch_robots(documents[0].final_url)

    # ------------------------------------------------------------- 스스로 찾아 돌기

    def crawl(
        self, entry_url: str, *, extra_urls: Sequence[str] = (), max_urls: int | None = None
    ) -> CrawlOutcome:
        """진입 주소에서 시작해 사이트맵과 내부 링크를 따라 넓이 우선으로 돈다.

        진입 페이지 실패만 예외를 올린다. 그 밖의 실패는 결과에 담긴다.
        """
        limit = max(1, max_urls or self._settings.console_crawl_max_urls)
        entry = normalise_url(entry_url)

        primary = self._fetch(entry)
        entry_url_final = normalise_url(primary.final_url)

        robots_txt = self._fetch_robots(primary.final_url)
        robots = parse_robots(robots_txt) if robots_txt is not None else None

        sitemaps, budget_exhausted = self._collect_sitemaps(entry_url_final, robots)

        documents: list[FetchedDocument] = [primary]
        discovered: dict[str, DiscoveredUrl] = {
            entry_url_final: DiscoveredUrl(url=entry_url_final, source=DiscoverySource.SEED)
        }
        failures: list[CrawlFailure] = []
        blocked: list[str] = []
        collapsed: list[str] = []
        group_fetched: dict[str, int] = {}
        sampled_out: dict[str, int] = {}
        # 이미 **최종 주소로** 가진 페이지. 요청 주소로만 걸러 내면 리다이렉트가 같은
        # 페이지를 여러 번 데려온다.
        collected_finals: set[str] = {entry_url_final}
        seen: set[str] = {entry, entry_url_final}

        pending: list[DiscoveredUrl] = [
            *urls_in_sitemaps(entry_url_final, sitemaps),
            *links_on_page(primary.final_url, primary.text()),
        ]
        seeds: tuple[str, ...] = tuple(extra_urls)

        # 상한·예산에 걸리지 않고 "더 볼 것이 없어서" 멈췄을 때만 참이 된다. 아래
        # 어느 `break` 로 나갔는지가 그 답이므로, 나가는 자리마다 명시적으로 정한다.
        discovery_exhausted = False

        for depth in range(1, self._max_depth + 1):
            if budget_exhausted or len(documents) >= limit:
                break  # 상한에 걸렸다 — 아직 볼 것이 남아 있을 수 있다
            remaining_budget = limit - len(documents)
            # 상한으로 자르지 않고 후보 전체를 본다 — 잘린 프런티어로는 "더
            # 있었는가" 도, 그룹마다 몇 장을 건너뛰는가도 셀 수 없다. 가져오는
            # 것은 아래에서 상한까지만 자른다.
            frontier, blocked_now = build_frontier(
                entry_url_final,
                seeds=seeds if depth == 1 else (),
                discovered=pending,
                robots=robots,
                limit=max(remaining_budget + 1, len(pending) + len(seeds)),
                seen=seen,
            )
            blocked.extend(blocked_now)
            seen.update(blocked_now)
            # 템플릿 그룹 표본 — **페이지 상한을 넘길 사이트에서만** 켠다.
            #
            # 상한 안에 드는 사이트는 전부 본다. 전량을 볼 수 있는데 표본을 쓰면
            # 결함 비율이 희석된다 — 실측(2026-08-02, chamsarang)에서 게시판 결함
            # canonical 60% 가 표본 후 23% 로 왜곡되며 점수가 71.8→77.6 으로 올랐다.
            # 덜 재서 점수가 오르는 것은 이 제품이 금지하는 방향이다. 표본은 전량의
            # 대체가 아니라 **잘림(무작정 앞에서 자르기)의 대체**다: 어차피 다 못 볼
            # 사이트에서 블로그형 그룹을 표본으로 줄이고, 아낀 예산으로 고정 페이지를
            # 전부 본다. 표본 판정의 그룹 일반화는 명세 1.9.0 의 몫이다.
            would_overflow = len(frontier) > remaining_budget
            if would_overflow or sampled_out:
                frontier, skipped_now = _apply_group_sampling(
                    frontier, group_fetched, self._group_sample
                )
                for key, count in skipped_now.items():
                    sampled_out[key] = sampled_out.get(key, 0) + count
            # 여유분 하나는 넘침 감지용이었다. 실제로 가져올 것은 상한까지다.
            frontier = frontier[:remaining_budget]
            if not frontier:
                # 표본 상한 때문에 비었다면 "다 봤다" 가 아니다 — 안 본 주소가 있다.
                discovery_exhausted = not sampled_out
                break
            seen.update(record.url for record in frontier)

            fetched, round_failures, budget_exhausted = self._fetch_many(frontier)
            failures.extend(round_failures)
            pending = []
            for record, document in fetched:
                final = normalise_url(document.final_url)
                group = group_key(record.url)
                if group is not None:
                    group_fetched[group] = group_fetched.get(group, 0) + 1
                # 리다이렉트가 이미 가진 페이지로 데려왔다. 문서로 세지 않는다 —
                # 세면 같은 페이지를 여러 장으로 계산해 측정 범위가 부풀려진다.
                if final in collected_finals:
                    collapsed.append(record.url)
                    seen.add(final)
                    continue
                collected_finals.add(final)
                seen.add(final)
                documents.append(document)
                discovered[final] = record
                pending.extend(links_on_page(document.final_url, document.text()))
        else:
            # 깊이 상한까지 다 썼다. 마지막 판에서 찾은 주소 가운데 아직 안 본 것이
            # 하나도 없으면 결과적으로는 다 본 것이다. 표본으로 건너뛴 주소가 있다면
            # 결과적으로도 다 본 것이 아니다.
            remaining, _ = build_frontier(
                entry_url_final,
                discovered=pending,
                robots=robots,
                limit=1,
                seen=seen,
            )
            discovery_exhausted = (
                not remaining and not budget_exhausted and not sampled_out
            )

        return CrawlOutcome(
            documents=tuple(documents),
            robots_txt=robots_txt,
            sitemaps=sitemaps,
            discovered=discovered,
            failures=tuple(failures),
            robots_blocked=tuple(blocked),
            collapsed_urls=tuple(collapsed),
            budget_exhausted=budget_exhausted,
            discovery_exhausted=discovery_exhausted,
            sampled_out=sampled_out,
            group_fetched=group_fetched,
        )

    # ------------------------------------------------------------- 내부

    def _accept(self, urls: Sequence[str]) -> tuple[str, ...]:
        if not urls:
            raise CrawlRefusal(
                422,
                ApiError.of(
                    ErrorCode.VALIDATION_FAILED, "진단할 주소를 한 개 이상 입력해 주십시오."
                ),
            )
        if len(urls) > self._max_urls:
            raise CrawlRefusal(
                422,
                ApiError.of(
                    ErrorCode.VALIDATION_FAILED,
                    f"한 번에 최대 {self._max_urls}개 주소까지 수집합니다. "
                    f"{len(urls)}개를 입력하셨습니다.",
                ),
            )
        return tuple(url.strip() for url in urls)

    def _fetch(self, url: str) -> FetchedDocument:
        try:
            return self._fetcher.fetch(url)
        except HostBudgetExceeded as exc:
            raise CrawlRefusal(429, exc.decision.as_api_error()) from exc
        except UrlRejectedError as exc:
            # 거절 사유는 규칙 이름만 말하고 그 뒤의 주소는 말하지 않는다. 그래야
            # 거절 응답이 VEO 내부망을 탐지하는 도구가 되지 않는다.
            raise CrawlRefusal(
                422, ApiError.of(ErrorCode.TARGET_URL_REJECTED, exc.decision.message_ko)
            ) from exc
        except FetchLimitError as exc:
            raise CrawlRefusal(
                422, ApiError.of(ErrorCode.TARGET_URL_REJECTED, exc.message_ko)
            ) from exc
        except (FetchError, httpx.HTTPError) as exc:
            # `httpx` 는 스트림 컨텍스트에 **진입할 때** 연결 오류를 던지므로 fetcher 자신의
            # except 절이 못 본다. 죽어 있는 고객 사이트가 500 이 되면 안 된다.
            raise CrawlRefusal(
                502,
                ApiError.of(
                    ErrorCode.PROVIDER_UNAVAILABLE, _UNREACHABLE_KO, retry_after_seconds=60
                ),
            ) from exc

    def _fetch_many(
        self, frontier: Sequence[DiscoveredUrl]
    ) -> tuple[tuple[tuple[DiscoveredUrl, FetchedDocument], ...], tuple[CrawlFailure, ...], bool]:
        """한 단계의 주소들을 동시에 가져온다. 한 장의 실패는 그 장만의 실패다.

        수집은 거의 전부 응답을 기다리는 시간이라 병렬이 그대로 이득이다. 동시에 여는
        수는 `console_crawl_concurrency` 가 정하고, 그것은 우리 속도가 아니라 **대상
        서버가 한순간에 받는 부하**다.

        **결과 순서는 frontier 순서로 되돌린다.** 먼저 끝난 순서로 두면 같은 사이트를
        같은 자료로 두 번 진단해도 문서 순서가 달라지고, 그러면 증거 목록과 화면이 흔들려
        "왜 이 점수가 나왔는가" 에 같은 답을 두 번 줄 수 없다.

        호스트 예산이 바닥나는 것은 실패로 세지 않는다. 예산 검사는 요청을 보내기 **전**에
        걸리므로 대상 서버는 그 사실을 모르고, 우리가 못 본 것은 페이지의 결함이 아니다.
        """
        if not frontier:
            return (), (), False
        workers = min(self._concurrency, len(frontier))
        if workers <= 1:
            return self._fetch_many_serially(frontier)

        slots: list[tuple[DiscoveredUrl, FetchedDocument] | None] = [None] * len(frontier)
        failed: list[tuple[int, CrawlFailure]] = []
        budget_exhausted = False

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="veo-crawl") as pool:
            pending = {
                pool.submit(self._fetcher.fetch, record.url): (index, record)
                for index, record in enumerate(frontier)
            }
            for future in as_completed(pending):
                index, record = pending[future]
                try:
                    slots[index] = (record, future.result())
                except HostBudgetExceeded:
                    budget_exhausted = True
                except (UrlRejectedError, FetchLimitError, FetchError, httpx.HTTPError) as exc:
                    failed.append(
                        (index, CrawlFailure(url=record.url, reason_ko=_failure_reason(exc)))
                    )

        collected = tuple(slot for slot in slots if slot is not None)
        failures = tuple(failure for _, failure in sorted(failed, key=lambda item: item[0]))
        return collected, failures, budget_exhausted

    def _fetch_many_serially(
        self, frontier: Sequence[DiscoveredUrl]
    ) -> tuple[tuple[tuple[DiscoveredUrl, FetchedDocument], ...], tuple[CrawlFailure, ...], bool]:
        """동시 요청 수가 1일 때의 경로. 병렬 결과를 의심할 때 비교 대상이 된다."""
        collected: list[tuple[DiscoveredUrl, FetchedDocument]] = []
        failures: list[CrawlFailure] = []

        for record in frontier:
            try:
                collected.append((record, self._fetcher.fetch(record.url)))
            except HostBudgetExceeded:
                # 예산이 바닥났으면 남은 주소도 전부 같은 이유로 거절당한다. 여기서 멈춘다.
                return tuple(collected), tuple(failures), True
            except (UrlRejectedError, FetchLimitError, FetchError, httpx.HTTPError) as exc:
                failures.append(CrawlFailure(url=record.url, reason_ko=_failure_reason(exc)))

        return tuple(collected), tuple(failures), False

    def _collect_sitemaps(
        self, entry_url: str, robots: RobotsFile | None
    ) -> tuple[dict[str, str], bool]:
        """robots.txt 가 선언한 사이트맵, 없으면 관례 경로. index 는 한 단계 따라간다.

        사이트맵을 못 읽는 것은 진단 결과이지 수집의 실패가 아니다 — 사이트맵 항목이
        그 사실을 판정한다. 그래서 여기서는 조용히 넘어가고 실패 목록에도 넣지 않는다.
        """
        found: dict[str, str] = {}
        budget_exhausted = False
        queue = list(sitemap_candidates(entry_url, robots))
        seen: set[str] = set(queue)
        followed_index = False

        while queue and len(found) < self._max_sitemaps and not budget_exhausted:
            candidate = queue.pop(0)
            try:
                document = self._fetcher.fetch(candidate)
            except HostBudgetExceeded:
                budget_exhausted = True
                break
            except (UrlRejectedError, FetchLimitError, FetchError, httpx.HTTPError):
                continue
            if document.status != 200:
                continue

            body = document.text()
            found[normalise_url(document.final_url)] = body

            if followed_index:
                continue
            targets = sitemap_index_targets(
                document.final_url, body, limit=self._max_sitemaps
            )
            if targets:
                followed_index = True
                queue.extend(target for target in targets if target not in seen)
                seen.update(targets)

        return found, budget_exhausted

    def _fetch_robots(self, page_url: str) -> str | None:
        """robots.txt 는 없을 수 있다. 없다는 사실과 못 읽었다는 사실을 구분한다.

        호스트는 페이지가 **실제로 도착한** 주소에서 뽑는다. 리다이렉트된 진단이 원래
        입력한 호스트의 robots.txt 를 읽으면 엉뚱한 사이트의 규칙으로 판정하게 된다.

        여기서 예산이 초과되어도 예외를 올리지 않는다. 페이지는 이미 가져왔고, 정직한
        응답은 robots 의존 항목이 UNKNOWN 인 진단 결과이지 이미 한 일을 버리는 429 가
        아니다. 어느 쪽이든 요청 자체는 보내지 않는다.
        """
        parts = urlsplit(page_url)
        if not parts.scheme or not parts.netloc:
            return None
        try:
            document = self._fetcher.fetch(f"{parts.scheme}://{parts.netloc}/robots.txt")
        except (
            HostBudgetExceeded,
            UrlRejectedError,
            FetchLimitError,
            FetchError,
            httpx.HTTPError,
        ):
            # 읽지 못한 것은 `None`. 빈 문자열은 "내용이 없는 파일" 이라는 다른 뜻이다.
            return None
        if document.status != 200:
            # 404 는 "규칙 파일이 없다" 이지 "모든 것이 막혀 있다" 가 아니다.
            return None
        return document.text()


def _failure_reason(exc: Exception) -> str:
    """수집 실패를 화면에 그대로 띄울 한 문장으로.

    예외 종류를 그대로 내보내지 않는다. 진단 결과를 읽는 사람은 개발자만이 아니다.
    """
    if isinstance(exc, UrlRejectedError):
        return exc.decision.message_ko
    if isinstance(exc, FetchLimitError):
        return exc.message_ko
    return "이 주소에서 응답을 받지 못했습니다."


__all__ = [
    "ConsoleCrawler",
    "CrawlFailure",
    "CrawlOutcome",
    "CrawlRefusal",
]
