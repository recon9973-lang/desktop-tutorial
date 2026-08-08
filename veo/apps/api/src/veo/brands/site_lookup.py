"""홈페이지를 한 장 받아 :mod:`veo.brands.discovery` 에 넘긴다.

`discovery` 는 글자만 읽는다 — 망을 타지 않아 시험이 쉽다. 망을 타는 부분은 여기
한 곳에 모은다.

## 조립을 이 안에서 하는 이유

호스트 예산은 **가드 안에서** 부과되어야 한다. 바깥에서 받은 `SafeFetcher` 를 그대로
쓰면 리다이렉트가 그 계산을 우회한다(크롤러가 같은 이유로 같은 조립을 한다,
`seo/crawl.py`). 등록 화면에서 부르는 창구라고 남의 서버에 더 무르게 굴 이유가 없다.

## 한 장만 받는다

크롤이 아니다. 등록하려는 주소 **그 한 장**만 받는다. 상호·전화·소재지·대표자는
대개 첫 화면과 바닥글에 함께 있고, 없으면 없는 대로 사람이 채운다 — 후보를 더
그러모으려고 남의 사이트를 헤집지 않는다.

## 받지 못한 것은 받지 못한 것으로 남긴다

읽기에 실패하면 빈 후보에 사유를 붙여 돌려준다. 예외로 터뜨리지 않는다 — 사이트가
안 열리는 것은 등록을 막을 일이 아니라 **직접 입력하면 되는 일**이다.
"""

from __future__ import annotations

import httpx

from veo.brands.discovery import SiteIdentityDraft, read_identity_draft
from veo.common.security.egress_kr import korean_egress
from veo.common.security.fetcher import FetchError, SafeFetcher
from veo.common.security.limits import ContentTypeNotAllowedError, FetchLimitError
from veo.common.security.pacing import HostPacer
from veo.common.security.retry_via_kr import RetryViaKorea
from veo.common.security.url_guard import UrlGuard, UrlRejectedError
from veo.core.settings import Settings, get_settings
from veo.public.limits import (
    TARGET_HOST_WINDOW_SECONDS,
    HostBudgetExceeded,
    HostBudgetGuard,
    InMemoryRateLimiter,
    RateLimiter,
)

__all__ = ["SiteIdentityReader"]

#: HTML 이 아닌 것을 받았을 때. PDF·이미지 주소를 홈페이지로 등록하는 일이 있다.
_NOT_HTML_KO = "홈페이지가 아니라 다른 종류의 파일입니다. 대표 주소를 넣어 주십시오."


class SiteIdentityReader:
    """주소 하나를 받아 식별 후보를 돌려준다. 저장하지 않는다."""

    __slots__ = ("_fetcher",)

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        guard: UrlGuard | None = None,
        limiter: RateLimiter | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved = settings or get_settings()
        budgeted = HostBudgetGuard(
            guard or UrlGuard(),
            limiter=limiter or InMemoryRateLimiter(),
            limit=resolved.console_target_host_limit_per_hour,
            window_seconds=TARGET_HOST_WINDOW_SECONDS,
            pacer=HostPacer(
                min_interval_seconds=resolved.crawl_min_interval_seconds,
                slots=resolved.console_crawl_concurrency,
            ),
        )
        # 해외에서 막히는 거래처가 있다. 관문 페이지를 만나면 한국에서 한 번 더 받는다
        # — 진단이 쓰는 것과 **같은 통로**다. 다른 통로를 쓰면 진단은 읽는 사이트를
        # 등록 화면만 못 읽는 일이 생긴다.
        self._fetcher = RetryViaKorea(
            SafeFetcher(guard=budgeted, transport=transport),
            egress=korean_egress(resolved),
            guard=budgeted,
        )

    def read(self, url: str) -> SiteIdentityDraft:
        """``url`` 한 장을 받아 후보를 읽는다. 실패해도 예외를 내지 않는다."""
        try:
            document = self._fetcher.fetch(url)
        except UrlRejectedError as exc:
            return _nothing(url, f"이 주소로는 접속하지 않습니다: {exc}")
        except HostBudgetExceeded:
            return _nothing(url, "같은 사이트를 너무 자주 불렀습니다. 잠시 후 다시 시도하십시오.")
        except ContentTypeNotAllowedError:
            # `SafeFetcher` 가 이미 막는다. 그쪽 문구("분석할 수 없는 형식의 응답입니다")
            # 는 진단용이라, 등록 화면에서는 무엇을 고치면 되는지로 바꿔 말한다.
            return _nothing(url, _NOT_HTML_KO)
        except (FetchError, FetchLimitError, httpx.HTTPError) as exc:
            return _nothing(url, f"홈페이지를 읽지 못했습니다({type(exc).__name__}).")

        if document.status >= 400:
            return _nothing(url, f"홈페이지가 {document.status} 로 응답했습니다.")

        return read_identity_draft(document.text(), url=document.final_url or url)


def _nothing(url: str, why_ko: str) -> SiteIdentityDraft:
    """후보 없음 + 사유. 빈 목록만 돌려주면 "사이트에 정보가 없다" 로 읽힌다."""
    return SiteIdentityDraft(url=url, candidates=(), notes_ko=(why_ko,))
