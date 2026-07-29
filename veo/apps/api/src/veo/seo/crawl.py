"""콘솔 진단의 수집 단계.

무료 공개 진단은 한 페이지만 본다(`public_max_urls_per_scan = 1`). 한 페이지로는
내부 링크·중복 메타데이터·클릭 깊이처럼 **사이트를 봐야 판정되는 항목**이 전부
UNKNOWN 으로 남고, 측정 범위가 60% 근처에서 멈춘다. 그 상태의 보고서를 고객에게
낼 수는 없다.

그래서 콘솔은 더 많이 본다. **더 많이 보는 것 말고는 아무것도 바꾸지 않는다** —
SSRF 차단, 대상 호스트 예산, 응답 크기·시간 상한은 공개 진단과 같은 구현을 쓴다.
로그인했다는 사실은 남의 서버를 두드려도 된다는 뜻이 아니고, 계정은 탈취된다.
"""

from __future__ import annotations

from collections.abc import Sequence
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

_UNREACHABLE_KO = (
    "대상 사이트에서 응답을 받지 못했습니다. 주소와 사이트 상태를 확인해 주십시오. "
    "이 결과는 VEO 의 오류가 아니라 대상 쪽 상태입니다."
)


class CrawlRefusal(Exception):
    """수집을 시작하지 못했거나 끝내지 못한 이유. 라우터가 그대로 응답으로 옮긴다."""

    def __init__(self, status_code: int, error: ApiError) -> None:
        super().__init__(error.message)
        self.status_code = status_code
        self.error = error


@final
class ConsoleCrawler:
    """진단 대상 페이지와 robots.txt 를 가져온다. 그 밖의 요청은 보내지 않는다."""

    __slots__ = ("_fetcher", "_max_urls")

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
        self._max_urls = max_urls or resolved.console_max_urls_per_scan
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

    def collect(
        self, urls: Sequence[str]
    ) -> tuple[tuple[FetchedDocument, ...], str | None]:
        targets = self._accept(urls)
        documents = tuple(self._fetch(url) for url in targets)
        return documents, self._fetch_robots(documents[0].final_url)

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
