"""Running a scan for somebody who has not signed up.

Two rules shape every line below.

**One engine.** The scan calls :func:`veo.seo.service.run_seo_scan` and
:func:`veo.geo.service.run_geo_readiness` — the same functions the console calls, over
the same published specification. There is no lightweight public scorer. If the free
scan and the paid scan disagreed about one URL, the product would have lied to somebody,
and the person it lied to would find out at exactly the moment they paid.

What differs is scope, and only scope: at most ``public_max_urls_per_scan`` pages, no
provider credentials, no rendering. Every one of those reductions shows up in the answer
as ``UNKNOWN`` outcomes, which lower coverage and confidence rather than the score. The
free result is a *smaller measurement*, not a *cheaper* one.

**Anonymous means anonymous.** Nothing here opens a database session, reads an
organization, or writes a row belonging to a customer. The only state a public scan
creates is one result held under a hashed, expiring token. That is why the keyword
lookup here calls the Naver client directly instead of :class:`KeywordService`: the
service's job includes recording the query against an organization, and a public caller
has no organization to record it against. The numbers come from the same client and the
same parser, so they cannot disagree; the opportunity score and the trend history stay
in the console, which is a difference of scope, not of method.

The URL is caller-supplied, which makes this module the SSRF surface. Every fetch goes
through :class:`SafeFetcher`, which validates through :class:`UrlGuard` and pins the
connection to the validated address. Nothing here fetches any other way.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Protocol, final, runtime_checkable
from urllib.parse import urlsplit

import httpx

from veo.collect.contract import CollectionContext
from veo.common.security.fetcher import FetchedDocument, FetchError, SafeFetcher
from veo.common.security.limits import FetchLimitError
from veo.common.security.url_guard import UrlGuard, UrlRejectedError
from veo.contracts.enums import ErrorCode, ProviderState, UrlImportance, ValueQuality
from veo.contracts.envelope import ApiError
from veo.core.settings import Settings, get_settings
from veo.geo.service import GEO_SPEC_ID, GeoReadinessReport, run_geo_readiness
from veo.keywords.normalize import normalize_keyword
from veo.providers.naver.credentials import searchad_from_settings
from veo.providers.naver.errors import UnknownValue
from veo.providers.naver.searchad import NaverSearchAdClient, SearchAdKeywordMetrics, SearchCount
from veo.public.limits import (
    TARGET_HOST_WINDOW_SECONDS,
    Bucket,
    HostBudgetExceeded,
    HostBudgetGuard,
    LimitScope,
    RateLimiter,
)
from veo.public.schemas import (
    MAX_PUBLIC_FINDINGS,
    PublicCheckRow,
    PublicExposureBlock,
    PublicFinding,
    PublicGeoScanPayload,
    PublicKeywordEntry,
    PublicKeywordLookupPayload,
    PublicPreviews,
    PublicResultPayload,
    PublicScoreBlock,
    PublicSeoScanPayload,
    PublicStage,
    PublicStatusCounts,
)
from veo.public.tokens import IssuedToken, fingerprint, issue_token, looks_like_token
from veo.scoring import CheckOutcome, CheckStatus, ScoreResult, ScoringSpec, latest_published
from veo.scoring.improvements import rank_improvements
from veo.seo.fix_examples import code_example_for
from veo.seo.measure_performance import with_performance
from veo.seo.parsing.html import parse_html
from veo.seo.service import SPEC_ID as SEO_SPEC_ID
from veo.seo.service import run_seo_scan

__all__ = [
    "MAX_PUBLIC_KEYWORDS",
    "PUBLIC_PROVIDER_STATES",
    "InMemoryPublicResultStore",
    "PublicRefusal",
    "PublicResultStore",
    "PublicScanService",
    "StoredPublicResult",
    "UsageRecorder",
    "build_public_context",
]

#: 무료 진단이 쓴 외부 API 호출을 적는 콜백의 형태. 구현은 이 패키지 밖에 산다 —
#: 익명 표면은 DB 를 임포트조차 하지 못한다(test_isolation).
UsageRecorder = Callable[[Sequence[Any]], None]

#: Every provider the engines can read, switched off. An anonymous caller does not get
#: VEO's paid API quota spent on them, and the checks that need a provider answer
#: ``UNKNOWN`` with a stated reason rather than being quietly skipped.
#:
#: 예외 하나 — GOOGLE_PAGESPEED. 하루 25,000회까지 정말 0원이고(usage/record.py),
#: 공개 진단은 1장이라 호출도 1회다. 그래서 SEO 스캔은 여기 DISABLED 를 초기값으로
#: 두되 ``with_performance`` 가 실측에 성공하면 그 상태로 덮어쓴다. 서버에 키가
#: 없으면 이 초기값 그대로가 정직한 결과다.
PUBLIC_PROVIDER_STATES: Final[Mapping[str, ProviderState]] = {
    "GOOGLE_PAGESPEED": ProviderState.DISABLED_NO_CREDENTIAL,
    "GOOGLE_CRUX": ProviderState.DISABLED_NO_CREDENTIAL,
    "GOOGLE_SEARCH_CONSOLE": ProviderState.DISABLED_NO_CREDENTIAL,
    "NAVER_SEARCH_ADVISOR": ProviderState.DISABLED_NO_CREDENTIAL,
    "INDEXNOW": ProviderState.DISABLED_NO_CREDENTIAL,
    "BACKLINK_INDEX": ProviderState.DISABLED_NO_CREDENTIAL,
    "BRAND_MENTIONS": ProviderState.DISABLED_NO_CREDENTIAL,
    "CONTENT_HISTORY": ProviderState.DISABLED_NO_CREDENTIAL,
}

#: A free keyword lookup is one provider call. The console's ceiling is 20; the public
#: one is smaller because it is paid for by nobody.
MAX_PUBLIC_KEYWORDS: Final = 5

_RESULT_NOT_FOUND_KO = (
    "요청하신 진단 결과를 찾을 수 없습니다. 공유 링크는 일정 기간이 지나면 만료됩니다."
)

_UNREACHABLE_KO = (
    "입력하신 주소에서 응답을 받지 못했습니다. 주소가 맞는지, 사이트가 정상적으로 열리는지 "
    "확인한 뒤 다시 시도해 주세요."
)


class PublicRefusal(Exception):
    """A public request VEO will not serve, with the answer already rendered.

    Carrying the :class:`ApiError` rather than a bare message keeps the Korean sentence,
    the machine-readable code and the retry hint together, so the router cannot lose one
    of the three on the way out.
    """

    def __init__(self, status_code: int, error: ApiError) -> None:
        self.status_code = status_code
        self.error = error
        super().__init__(f"{error.code}: {error.message}")


# --------------------------------------------------------------------------- #
# The expiring result store
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class StoredPublicResult:
    """One shareable result, keyed by the token's fingerprint rather than the token."""

    fingerprint: str
    payload: PublicResultPayload
    expires_at: datetime


@runtime_checkable
class PublicResultStore(Protocol):
    def put(self, result: StoredPublicResult) -> None: ...

    def get(
        self, fingerprint_value: str, *, now: datetime
    ) -> StoredPublicResult | None: ...


@final
class InMemoryPublicResultStore:
    """Results held in this process until they expire.

    **Limitation, stated plainly:** a restart drops every shared link, and one API
    process cannot read another's. Redis is the production backing — the same one the
    rate limiter needs — and it is not built here.

    An expired entry is deleted on read rather than returned and filtered, so a stale
    result cannot survive a bug in the caller's expiry check.
    """

    __slots__ = ("_results",)

    def __init__(self) -> None:
        self._results: dict[str, StoredPublicResult] = {}

    def put(self, result: StoredPublicResult) -> None:
        self._results[result.fingerprint] = result

    def get(self, fingerprint_value: str, *, now: datetime) -> StoredPublicResult | None:
        stored = self._results.get(fingerprint_value)
        if stored is None:
            return None
        if now >= stored.expires_at:
            del self._results[fingerprint_value]
            return None
        return stored

    def stored_keys(self) -> tuple[str, ...]:
        """The fingerprints held. Used by tests to prove tokens are not kept."""
        return tuple(self._results)


# --------------------------------------------------------------------------- #
# Context assembly
# --------------------------------------------------------------------------- #


def build_public_context(
    *,
    target_url: str,
    spec: ScoringSpec,
    documents: Sequence[FetchedDocument],
    robots_txt: str | None,
    collected_at: datetime,
    locale: str = "ko-KR",
) -> CollectionContext:
    """Assemble the collection context a public scan is scored from.

    Exposed rather than inlined so a test can build the identical context, hand it to
    the internal engine directly, and prove the two agree. If this were private, "the
    public scan uses the same engine" would be a claim instead of an assertion.
    """
    by_url = {document.final_url: document for document in documents}
    primary = documents[0] if documents else None
    return CollectionContext(
        target_url=target_url,
        spec=spec,
        documents=by_url,
        primary_document=primary,
        robots_txt=robots_txt,
        sitemap_documents={},
        rendered_dom={},
        provider_states=dict(PUBLIC_PROVIDER_STATES),
        provider_payloads={},
        url_importance={
            document.final_url: UrlImportance.CONVERSION_OR_HOME.value
            for document in documents
        },
        locale=locale,
        collected_at=collected_at,
    )


# --------------------------------------------------------------------------- #
# The service
# --------------------------------------------------------------------------- #


@final
class PublicScanService:
    """Scoped scans for anonymous callers, with the limits applied before the work."""

    def __init__(
        self,
        *,
        limiter: RateLimiter,
        results: PublicResultStore,
        guard: UrlGuard | None = None,
        transport: httpx.BaseTransport | None = None,
        settings: Settings | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        searchad: NaverSearchAdClient | None = None,
        performance: Callable[[Any], tuple[Any, Any | None]] = with_performance,
    ) -> None:
        self._limiter = limiter
        self._results = results
        self._settings = settings or get_settings()
        self._clock = clock
        self._searchad = searchad or NaverSearchAdClient(credentials=searchad_from_settings())
        # 주입 지점인 이유: 기본값(설정에서 키 읽기)을 시험이 그대로 쓰면 개발자
        # 컴퓨터의 .env 를 타고 진짜 구글로 나간다 — 실제로 있었던 사고다(0-F).
        self._performance = performance

        # The service builds its own fetcher rather than accepting one, and it is worth
        # saying why: the target-host budget is charged inside the guard, so a caller who
        # passed in a plain ``SafeFetcher`` would silently disable the one control that
        # stops VEO being pointed at a third party. Taking the guard and the transport —
        # the two pieces a test or a deployment legitimately needs to vary — and
        # assembling the rest here makes that impossible to get wrong.
        # ``public_target_host_limit_per_hour``, not ``public_rate_limit_per_hour``. The
        # two count different units — the caller buckets charge once per scan, this one
        # charges once per outbound request — so one setting could never have meant both.
        self._fetcher = SafeFetcher(
            guard=HostBudgetGuard(
                guard or UrlGuard(),
                limiter=limiter,
                limit=self._settings.public_target_host_limit_per_hour,
                window_seconds=TARGET_HOST_WINDOW_SECONDS,
            ),
            transport=transport,
        )

    # ------------------------------------------------------------- scans

    def run_seo_scan(
        self,
        *,
        urls: Sequence[str],
        client_ip: str,
        session_id: str,
        record_usage: UsageRecorder | None = None,
    ) -> PublicSeoScanPayload:
        """SEO readiness for at most ``public_max_urls_per_scan`` pages.

        성능(PageSpeed)도 잰다 — 콘솔만 배선하고 공개 경로를 빼먹어서, 키가 있는데도
        무료 진단의 성능 4항목이 상시 측정 불가였다(2026-08-02 라이브에서 확인).
        공개 진단은 1장이므로 호출도 1회다. 유료 한도를 쓴 사실은 ``record_usage``
        콜백으로 라우터에 넘긴다 — DB 세션은 라우터의 것이고, 여기로 끌어오면
        스레드 밖에서 쓰이게 된다(measure_performance 모듈 문서와 같은 이유).
        """
        targets = self._accept_targets(urls)
        self._charge_caller(client_ip=client_ip, session_id=session_id)

        spec = latest_published(SEO_SPEC_ID)
        collected_at = self._now()
        documents, robots_txt = self._collect(targets)
        context = build_public_context(
            target_url=targets[0],
            spec=spec,
            documents=documents,
            robots_txt=robots_txt,
            collected_at=collected_at,
        )
        context, performance = self._performance(context)
        result = run_seo_scan(context)
        issued = self._issue()

        if performance is not None and performance.calls and record_usage is not None:
            record_usage(performance.calls)

        payload = PublicSeoScanPayload(
            target_url=targets[0],
            scanned_url_count=len(documents),
            summary_ko=result.summary_ko,
            score=_score_block(spec, result.score),
            reach=result.score.reach,
            stages=_stages(spec, result.score),
            checks=_check_rows(
                spec,
                result.score,
                {item.check_id: item.reason_ko for item in result.unknown_checks},
            ),
            counts=_status_counts(spec, result.score.outcomes),
            previews=_previews(documents[0] if documents else None),
            top_findings=_findings(spec, result.score.outcomes),
            total_finding_count=_finding_total(result.score.outcomes),
            unmeasured_check_count=len(result.unknown_checks),
            result_token=issued.token,
            result_expires_at=issued.expires_at,
        )
        self._remember(issued, payload)
        return payload

    def run_geo_readiness(
        self, *, urls: Sequence[str], client_ip: str, session_id: str
    ) -> PublicGeoScanPayload:
        """GEO readiness, with the exposure status kept beside the score and not in it."""
        targets = self._accept_targets(urls)
        self._charge_caller(client_ip=client_ip, session_id=session_id)

        spec = latest_published(GEO_SPEC_ID)
        collected_at = self._now()
        documents, robots_txt = self._collect(targets)
        context = build_public_context(
            target_url=targets[0],
            spec=spec,
            documents=documents,
            robots_txt=robots_txt,
            collected_at=collected_at,
        )
        report = run_geo_readiness(context, spec=spec)
        issued = self._issue()

        payload = PublicGeoScanPayload(
            target_url=targets[0],
            scanned_url_count=len(documents),
            summary_ko=report.summary_ko(),
            readiness=_score_block(spec, report.score),
            reach=report.score.reach,
            stages=_stages(spec, report.score),
            checks=_check_rows(spec, report.score),
            counts=_status_counts(spec, report.score.outcomes),
            exposure=_exposure_block(report),
            top_findings=_findings(spec, report.score.outcomes),
            total_finding_count=_finding_total(report.score.outcomes),
            unmeasured_check_count=_unknown_total(report.score.outcomes),
            result_token=issued.token,
            result_expires_at=issued.expires_at,
        )
        self._remember(issued, payload)
        return payload

    # --------------------------------------------------------- keywords

    def lookup_keywords(
        self, *, keywords: Sequence[str], client_ip: str, session_id: str
    ) -> PublicKeywordLookupPayload:
        """Naver's published monthly search counts, and nothing recorded anywhere.

        With no credential configured the client reports ``DISABLED_NO_CREDENTIAL``,
        opens no connection, and the answer carries the state and a Korean explanation
        instead of numbers. That is the honest shape of "how many people search for
        this?" when nobody will say.
        """
        cleaned = self._accept_keywords(keywords)
        self._charge_caller(client_ip=client_ip, session_id=session_id)

        outcome = self._searchad.lookup([normalized for _, normalized in cleaned])
        metrics_by_keyword: dict[str, SearchAdKeywordMetrics] = {}
        notices: list[str] = []
        if isinstance(outcome.value, UnknownValue):
            if outcome.failure is not None:
                notices.append(outcome.failure.reason_ko)
        else:
            for metric in outcome.value.metrics:
                metrics_by_keyword.setdefault(normalize_keyword(metric.keyword), metric)

        entries = [
            _keyword_entry(original, normalized, metrics_by_keyword.get(normalized))
            for original, normalized in cleaned
        ]
        state = self._searchad.state
        if state is not ProviderState.ENABLED and not notices:
            notices.append(
                "네이버 검색광고 연동이 설정되지 않아 검색량을 가져오지 못했습니다. "
                "VEO는 추정값을 실제 수치처럼 표시하지 않습니다."
            )
        return PublicKeywordLookupPayload(
            searchad_state=state.value, keywords=entries, notices_ko=notices
        )

    # ---------------------------------------------------------- results

    def read_result(self, token: str) -> PublicResultPayload:
        """Read a shared result back, or refuse.

        "Never existed", "already expired" and "malformed" produce one identical answer.
        Distinguishing them would turn this endpoint into an oracle that confirms which
        tokens were ever real.
        """
        if not looks_like_token(token):
            raise self._not_found()
        stored = self._results.get(fingerprint(token), now=self._now())
        if stored is None:
            raise self._not_found()
        return stored.payload

    # --------------------------------------------------------- internals

    def _now(self) -> datetime:
        return self._clock()

    def _issue(self) -> IssuedToken:
        return issue_token(
            ttl_seconds=self._settings.public_result_ttl_seconds, now=self._now()
        )

    def _remember(self, issued: IssuedToken, payload: PublicResultPayload) -> None:
        self._results.put(
            StoredPublicResult(
                fingerprint=issued.fingerprint,
                payload=payload,
                expires_at=issued.expires_at,
            )
        )

    def _accept_targets(self, urls: Sequence[str]) -> tuple[str, ...]:
        maximum = self._settings.public_max_urls_per_scan
        if not urls:
            raise PublicRefusal(
                422,
                ApiError.of(
                    ErrorCode.VALIDATION_FAILED, "진단할 주소를 한 개 이상 입력해 주세요."
                ),
            )
        if len(urls) > maximum:
            raise PublicRefusal(
                422,
                ApiError.of(
                    ErrorCode.VALIDATION_FAILED,
                    f"무료 진단은 한 번에 최대 {maximum}개 주소까지 분석합니다. "
                    f"{len(urls)}개를 입력하셨습니다.",
                ),
            )
        return tuple(url.strip() for url in urls)

    def _accept_keywords(self, keywords: Sequence[str]) -> tuple[tuple[str, str], ...]:
        if not keywords:
            raise PublicRefusal(
                422,
                ApiError.of(ErrorCode.VALIDATION_FAILED, "조회할 키워드를 입력해 주세요."),
            )
        if len(keywords) > MAX_PUBLIC_KEYWORDS:
            raise PublicRefusal(
                422,
                ApiError.of(
                    ErrorCode.VALIDATION_FAILED,
                    f"무료 조회는 한 번에 최대 {MAX_PUBLIC_KEYWORDS}개 키워드까지 가능합니다.",
                ),
            )
        cleaned: list[tuple[str, str]] = []
        for keyword in keywords:
            try:
                cleaned.append((keyword, normalize_keyword(keyword)))
            except ValueError as exc:
                raise PublicRefusal(
                    422, ApiError.of(ErrorCode.VALIDATION_FAILED, str(exc))
                ) from exc
        return tuple(cleaned)

    def _charge_caller(self, *, client_ip: str, session_id: str) -> None:
        """Spend one unit of the *caller's* allowance, or refuse without spending any.

        Only the two buckets that describe who is asking. The target-host bucket is
        charged elsewhere — in :class:`HostBudgetGuard`, once per outbound request, keyed
        on the host VEO is actually about to contact. Charging it here, from the
        submitted URL, is exactly the mistake that let a redirect launder eighty requests
        onto a host limited to ten: the key came from the attacker, not from the socket.
        """
        limit = self._settings.public_rate_limit_per_hour
        decision = self._limiter.acquire(
            [
                Bucket(
                    scope=LimitScope.CLIENT_IP,
                    key=client_ip,
                    limit=limit,
                    window_seconds=TARGET_HOST_WINDOW_SECONDS,
                ),
                Bucket(
                    scope=LimitScope.SESSION,
                    key=session_id,
                    limit=limit,
                    window_seconds=TARGET_HOST_WINDOW_SECONDS,
                ),
            ]
        )
        if not decision.allowed:
            raise PublicRefusal(429, decision.as_api_error())

    def _collect(
        self, targets: Sequence[str]
    ) -> tuple[tuple[FetchedDocument, ...], str | None]:
        """Fetch the pages and the site's robots.txt, through the guard, and nothing else."""
        documents = tuple(self._fetch(url) for url in targets)
        return documents, self._fetch_robots(documents[0].final_url)

    def _fetch(self, url: str) -> FetchedDocument:
        try:
            return self._fetcher.fetch(url)
        except HostBudgetExceeded as exc:
            # Raised from inside the guard, before the socket was opened — including on
            # a redirect hop, which is where the amplification would otherwise live.
            raise PublicRefusal(429, exc.decision.as_api_error()) from exc
        except UrlRejectedError as exc:
            # The guard's Korean message names the rule that was broken and never the
            # address behind it, which is what keeps a rejection from being a probe of
            # VEO's own network.
            raise PublicRefusal(
                422, ApiError.of(ErrorCode.TARGET_URL_REJECTED, exc.decision.message_ko)
            ) from exc
        except FetchLimitError as exc:
            raise PublicRefusal(
                422, ApiError.of(ErrorCode.TARGET_URL_REJECTED, exc.message_ko)
            ) from exc
        except (FetchError, httpx.HTTPError) as exc:
            # ``httpx.HTTPError`` is caught alongside VEO's own ``FetchError`` because
            # ``SafeFetcher._stream`` wraps ``client.stream(...)``, and httpx raises a
            # connect error when the returned context manager is *entered*, one frame
            # later — so the fetcher's own except clause never sees it. A dead customer
            # site must not become a 500 on the front page, so it is caught here as
            # well. Filed in INTEGRATION_REQUEST.md #3.
            raise PublicRefusal(
                502,
                ApiError.of(
                    ErrorCode.PROVIDER_UNAVAILABLE,
                    _UNREACHABLE_KO,
                    retry_after_seconds=60,
                ),
            ) from exc

    def _fetch_robots(self, page_url: str) -> str | None:
        """Best effort, from the URL the page fetch actually **landed on**.

        Two things are deliberate. The host comes from ``final_url``, so a redirected
        scan reads the robots.txt of the site it ended up at rather than of the hostname
        that pointed there — which also means this second request is charged to that
        site's budget, like the first one.

        And a budget refusal here is swallowed rather than raised. The page is already
        fetched; the honest response is a scan whose robots-dependent checks report
        ``UNKNOWN``, not a 429 that throws away work already done. Either way VEO does
        not send the request.
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
            return None
        if document.status != 200:
            return None
        return document.text()

    def _not_found(self) -> PublicRefusal:
        return PublicRefusal(404, ApiError.of(ErrorCode.NOT_FOUND, _RESULT_NOT_FOUND_KO))


# --------------------------------------------------------------------------- #
# Payload assembly — specification wording only
# --------------------------------------------------------------------------- #


def _score_block(spec: ScoringSpec, result: ScoreResult) -> PublicScoreBlock:
    band = spec.band_for(result.overall_score) if result.overall_score is not None else None
    return PublicScoreBlock(
        spec_id=result.spec_id,
        spec_version=result.spec_version,
        spec_checksum=result.spec_checksum,
        status=result.status,
        score=result.overall_score,
        band_id=result.band_id,
        band_label_ko=band.label_ko if band else None,
        coverage=result.coverage,
        confidence=result.confidence,
    )


def _stages(spec: ScoringSpec, result: ScoreResult) -> list[PublicStage]:
    """점수를 이루는 영역만, 명세 선언 순서대로. 연동 영역은 점수 밖이라 싣지 않는다."""
    by_id = {category.category_id: category for category in result.categories}
    rows: list[PublicStage] = []
    for declared in spec.categories:
        if not declared.contributes_to_score:
            continue
        scored = by_id.get(declared.id)
        rows.append(
            PublicStage(
                category_id=declared.id,
                name_ko=declared.name_ko,
                score=None if scored is None else scored.score,
                weight=declared.weight,
                is_gate=declared.is_gate,
            )
        )
    return rows


def _check_rows(
    spec: ScoringSpec,
    score: ScoreResult,
    unknown_reasons: Mapping[str, str] | None = None,
) -> list[PublicCheckRow]:
    """전체 검사 목록 — 명세가 아는 모든 검사에 판정·이유·이득·조치 코드를 붙인다.

    무료 결과가 상위 몇 건만 보여주던 것에서 전체 공개로 바꾼 것은 화면 확정
    (2026-08-02)의 결정이다. 숨겨서 얻는 전환보다 다 보여주고 "사이트 전체 진단"
    으로 넘어오게 하는 쪽을 택했다 — 페이지 간 비교 항목은 어차피 여기서 측정
    불가로 남아, 전체 진단의 이유가 화면 자체에 있다.
    """
    outcome_by_id = {outcome.check_id: outcome for outcome in score.outcomes}
    unknown_reason = dict(unknown_reasons or {})
    improvement_by_id = {entry.check_id: entry for entry in rank_improvements(score)}

    rows: list[PublicCheckRow] = []
    for category in spec.categories:
        for check in category.checks:
            outcome = outcome_by_id.get(check.id)
            if outcome is None:
                continue
            status = str(outcome.status.value)
            gain = improvement_by_id.get(check.id)
            rows.append(
                PublicCheckRow(
                    check_id=check.id,
                    title_ko=check.title_ko,
                    category_id=category.id,
                    category_name_ko=category.name_ko,
                    severity=str(check.severity),
                    remediation_owner=check.remediation_owner,
                    status=status,  # type: ignore[arg-type]
                    note_ko=unknown_reason.get(check.id) or outcome.note,
                    gain_points=None if gain is None else gain.gain_points,
                    blocked_by_cap=False if gain is None else gain.blocked_by_cap,
                    outside_score=not category.contributes_to_score,
                    code_example=(
                        code_example_for(check.id)
                        if status in ("FAIL", "WARNING")
                        else None
                    ),
                )
            )
    return rows


def _status_counts(
    spec: ScoringSpec, outcomes: Sequence[CheckOutcome]
) -> PublicStatusCounts:
    counts = dict.fromkeys(("FAIL", "WARNING", "PASS", "UNKNOWN", "NOT_APPLICABLE"), 0)
    known = {check.id for category in spec.categories for check in category.checks}
    for outcome in outcomes:
        if outcome.check_id in known:
            counts[str(outcome.status.value)] = counts.get(str(outcome.status.value), 0) + 1
    return PublicStatusCounts(
        failed=counts["FAIL"],
        warned=counts["WARNING"],
        passed=counts["PASS"],
        unknown=counts["UNKNOWN"],
        not_applicable=counts["NOT_APPLICABLE"],
    )


def _previews(document: FetchedDocument | None) -> PublicPreviews | None:
    """검색결과·공유 카드 미리보기 재료. 값이 없으면 없는 채로 — 부재가 곧 진단이다."""
    if document is None:
        return None
    page = parse_html(document.text())
    og = page.open_graph
    return PublicPreviews(
        serp_title=page.title,
        serp_description=page.meta_description,
        og_title=og.get("og:title"),
        og_description=og.get("og:description"),
        has_og_image=bool((og.get("og:image") or "").strip()),
    )


def _exposure_block(report: GeoReadinessReport) -> PublicExposureBlock:
    return PublicExposureBlock(
        is_blocked=report.is_exposure_blocked,
        status_codes=list(report.gate_status_codes),
        labels_ko=[gate.label_ko for gate in report.gates],
    )


def _findings(spec: ScoringSpec, outcomes: Sequence[CheckOutcome]) -> list[PublicFinding]:
    """The most serious problems, described in the specification's own published words.

    Nothing a collector wrote reaches this list. A collector's ``summary_ko`` reads
    "https://clinic.example/about — 제목 없음", which is exactly right in a console and
    exactly wrong in a payload anyone holding a share link can read.
    """
    ranked = sorted(
        (item for item in outcomes if item.status in _REPORTABLE),
        key=lambda item: (
            -spec.severity_coefficient(spec.check(item.check_id).severity),
            0 if item.status is CheckStatus.FAIL else 1,
            item.check_id,
        ),
    )
    findings: list[PublicFinding] = []
    for outcome in ranked[:MAX_PUBLIC_FINDINGS]:
        check = spec.check(outcome.check_id)
        category = spec.category_of(outcome.check_id)
        findings.append(
            PublicFinding(
                check_id=check.id,
                title_ko=check.title_ko,
                category_id=category.id,
                category_name_ko=category.name_ko,
                severity=str(check.severity),
                remediation_owner=check.remediation_owner,
                status="FAIL" if outcome.status is CheckStatus.FAIL else "WARNING",
            )
        )
    return findings


_REPORTABLE = frozenset({CheckStatus.FAIL, CheckStatus.WARNING})


def _finding_total(outcomes: Sequence[CheckOutcome]) -> int:
    return sum(1 for item in outcomes if item.status in _REPORTABLE)


def _unknown_total(outcomes: Sequence[CheckOutcome]) -> int:
    return sum(1 for item in outcomes if item.status is CheckStatus.UNKNOWN)


def _keyword_entry(
    original: str, normalized: str, metrics: SearchAdKeywordMetrics | None
) -> PublicKeywordEntry:
    if metrics is None:
        missing = ValueQuality.MISSING.value
        return PublicKeywordEntry(
            keyword=original,
            normalized_keyword=normalized,
            monthly_total_quality=missing,
            monthly_pc_quality=missing,
            monthly_mobile_quality=missing,
        )
    return PublicKeywordEntry(
        keyword=original,
        normalized_keyword=normalized,
        monthly_total_searches=_count_value(metrics.monthly_total_searches),
        monthly_total_quality=metrics.monthly_total_searches.quality.value,
        monthly_pc_searches=_count_value(metrics.monthly_pc_searches),
        monthly_pc_quality=metrics.monthly_pc_searches.quality.value,
        monthly_mobile_searches=_count_value(metrics.monthly_mobile_searches),
        monthly_mobile_quality=metrics.monthly_mobile_searches.quality.value,
        competition_label=metrics.competition_label,
    )


def _count_value(count: SearchCount) -> int | None:
    """``None`` unless the provider actually gave a number.

    A suppressed or below-threshold count is not zero, and writing it as zero would read
    to a clinic owner as "nobody searches for this".
    """
    return count.value
