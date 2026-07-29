"""크롤링·색인 가능성 — can a search engine fetch this URL and keep it?

The ten checks here answer the only question that comes before every other question. A
site that fails one of the blockers is not "scoring badly at SEO"; it is invisible, and
the specification's caps exist so that a failure here cannot be averaged away by good
marks elsewhere. This module does not know about those caps — it reports what it saw.
"""

from __future__ import annotations

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    IssueDraft,
    not_applicable_outcome,
    unknown_outcome,
)
from veo.scoring import CheckOutcome, CheckStatus
from veo.seo.collectors.base import (
    DIRECT,
    NO_DOCUMENTS_KO,
    EvidenceLedger,
    SeoCollector,
    all_unknown,
    issue,
    outcome,
    site_outcome,
    url_ratio_outcome,
)
from veo.seo.observation import PageObservation, SiteObservation
from veo.seo.parsing import (
    CRAWLER_AGENT_NAME,
    CRAWLER_LABELS_KO,
    REPORTED_CRAWLERS,
    host_of,
    normalise_url,
    path_of,
    registrable_domain,
    resolve,
    same_site,
)

#: Hops beyond this many are a chain worth shortening. An observation threshold, not a
#: points threshold: it decides what VEO reports, never what the finding costs.
MAX_SANE_HOPS = 2

#: Directives in ``meta robots`` or ``X-Robots-Tag`` that keep a page out of the index.
#: 색인을 막는 지시자. **지시자 하나로 서 있을 때만** 해당한다.
#:
#: 부분 문자열로 찾으면 안 된다. `max-image-preview:none` 은 구글이 문서화한 값인데
#: `none` 을 품고 있어서, 멀쩡한 사이트가 "색인 차단" BLOCKER 판정을 받고 25점 상한에
#: 걸린다. 실제로 그렇게 동작했다.
_BLOCKING_DIRECTIVES = frozenset({"noindex", "none"})


def _blocks_indexing(value: str) -> bool:
    """`content` 를 쉼표로 나눠 **지시자 단위**로 본다.

    `key:value` 형태(`max-snippet:-1`, `max-image-preview:none`)는 값이 무엇이든 색인을
    막지 않는다. 색인을 막는 것은 `noindex` 와 `none` 이 **그 자체로** 하나의 지시자로
    쓰였을 때뿐이다.
    """
    for token in value.lower().split(","):
        directive = token.strip()
        if directive in _BLOCKING_DIRECTIVES:
            return True
    return False


class CrawlIndexabilityCollector(SeoCollector):
    category_id = "crawl_indexability"
    check_id_list = (
        "seo.http.status_ok",
        "seo.http.redirect_chain_sane",
        "seo.robots.txt_allows_url",
        "seo.robots.meta_indexable",
        "seo.canonical.declared_and_consistent",
        "seo.canonical.not_cross_domain",
        "seo.sitemap.discoverable",
        "seo.sitemap.urls_valid",
        "seo.crawl.no_orphan_key_pages",
        "seo.crawl.no_broken_internal_links",
    )

    def collect(self, context: CollectionContext) -> CollectionResult:
        site = self.observe(context)
        if not site.has_pages:
            return all_unknown(self.check_id_list, NO_DOCUMENTS_KO)

        ledger = EvidenceLedger()
        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []
        notes: list[str] = []

        for step in (
            _status_ok,
            _redirect_chain,
            _robots_allows,
            _meta_indexable,
            _canonical_consistent,
            _canonical_not_cross_domain,
            _sitemap_discoverable,
            _sitemap_urls_valid,
            _orphan_key_pages,
            _broken_internal_links,
        ):
            produced, produced_issues = step(context, site, ledger)
            outcomes.append(produced)
            issues.extend(produced_issues)

        if site.robots is None:
            notes.append("robots.txt를 수집하지 못해 크롤링 허용 여부를 확인하지 못했습니다.")

        return CollectionResult(
            outcomes=tuple(outcomes),
            evidence=ledger.records(),
            issues=tuple(issues),
            notes_ko=tuple(notes),
        )


# --------------------------------------------------------------------------- #
# seo.http.status_ok
# --------------------------------------------------------------------------- #


def _status_ok(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    failing = [page for page in site.pages if not page.is_ok]
    evidence = [
        ledger.page_snippet(page, "http_response", f"{page.status} {page.url}")
        for page in (failing or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.http.status_ok",
        affected=failing,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value={page.url: page.status for page in failing} or None,
        clean_note_ko="수집한 모든 URL이 2xx로 응답했습니다.",
        affected_note_ko=f"{len(failing)}개 URL이 2xx가 아닌 상태로 응답했습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.http.status_ok",
            title_ko="일부 URL이 정상 응답하지 않습니다",
            summary_ko=(
                f"수집한 {len(site.pages)}개 URL 가운데 {len(failing)}개가 2xx가 아닌 상태 코드로 "
                "응답했습니다. 검색엔진은 이 URL의 내용을 가져갈 수 없습니다."
            ),
            affected_urls=[page.url for page in failing],
            evidence_ids=evidence,
            remediation_ko=(
                "해당 URL이 삭제된 페이지라면 410 또는 404를 유지하되 내부 링크와 사이트맵에서 "
                "제거하고, 위치가 바뀐 페이지라면 새 주소로 301 리다이렉트를 설정하십시오."
            ),
            reverification_ko="수정 후 해당 URL을 다시 수집해 상태 코드가 2xx인지 확인합니다.",
            business_impact_ko="색인에서 빠지면 해당 페이지로 들어오던 검색 유입이 사라집니다.",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.http.redirect_chain_sane
# --------------------------------------------------------------------------- #


def _redirect_chain(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    looping: list[PageObservation] = []
    long_chain: list[PageObservation] = []
    detail: dict[str, object] = {}

    for page in site.pages:
        hops = page.document.hops
        seen: list[str] = []
        repeated: str | None = None
        for hop in hops:
            url = normalise_url(hop.url)
            if url in seen:
                repeated = url
                break
            seen.append(url)
        if repeated is not None:
            looping.append(page)
            detail[page.url] = {"loop_at": repeated, "hops": len(hops)}
        elif len(hops) > MAX_SANE_HOPS:
            long_chain.append(page)
            detail[page.url] = {"hops": len(hops)}

    affected = looping + long_chain
    evidence = [
        ledger.of(
            "redirect_chain",
            url=page.url,
            payload=" -> ".join(f"{hop.status} {hop.url}" for hop in page.document.hops),
            excerpt=" -> ".join(f"{hop.status} {hop.url}" for hop in page.document.hops),
            detail={"hops": len(page.document.hops)},
        )
        for page in (affected or site.pages[:1])
    ]

    result = url_ratio_outcome(
        "seo.http.redirect_chain_sane",
        affected=affected,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=detail or None,
        clean_note_ko="리다이렉트 체인이 짧고 루프가 없습니다.",
        affected_note_ko=(
            f"{len(looping)}개 URL에서 루프, {len(long_chain)}개 URL에서 긴 체인을 확인했습니다."
        ),
        warning=not looping,
    )
    if result.status is CheckStatus.PASS:
        return result, []

    affected_urls: list[str] = []
    for page in affected:
        affected_urls.append(page.url)
        affected_urls.extend(normalise_url(hop.url) for hop in page.document.hops)

    return result, [
        issue(
            context,
            "seo.http.redirect_chain_sane",
            title_ko="리다이렉트가 반복되거나 지나치게 깁니다",
            summary_ko=(
                f"{len(looping)}개 URL에서 같은 주소로 되돌아오는 리다이렉트 루프가, "
                f"{len(long_chain)}개 URL에서 {MAX_SANE_HOPS}단계를 넘는 체인이 확인되었습니다."
            ),
            affected_urls=affected_urls,
            evidence_ids=evidence,
            remediation_ko=(
                "리다이렉트 규칙을 한 곳에 모아 출발지에서 최종 주소로 한 번에 이동하도록 "
                "정리하고, 서로를 가리키는 규칙 쌍은 한쪽을 제거하십시오."
            ),
            reverification_ko="규칙 정리 후 해당 URL을 다시 수집해 홉이 한 단계인지 확인합니다.",
            business_impact_ko="루프에 걸린 URL은 크롤링 자체가 끝나지 않아 색인되지 않습니다.",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.robots.txt_allows_url
# --------------------------------------------------------------------------- #


def _robots_allows(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    if site.robots is None:
        return (
            unknown_outcome(
                "seo.robots.txt_allows_url",
                "robots.txt를 수집하지 못했습니다. 파일이 없는 것과 확인하지 못한 것은 다르므로 "
                "허용으로 단정하지 않습니다.",
            ),
            [],
        )

    robots_evidence = ledger.of(
        "robots_txt",
        url=None,
        payload=site.robots.raw,
        excerpt=site.robots.raw[:500],
        detail={"groups": len(site.robots.groups), "sitemaps": len(site.robots.sitemaps)},
    )

    blocked: list[PageObservation] = []
    evidence = [robots_evidence]
    detail: dict[str, dict[str, object]] = {}

    blocked_agents: set[str] = set()
    for page in site.pages:
        # `veo-bot` 이 들어갈 수 있다는 사실은 고객에게 아무 의미가 없다. 물어야 하는
        # 것은 **우리가 보고서에 쓰는 검색엔진**이 들어갈 수 있는가다. 특히 Yeti —
        # 병원 고객의 주력 유입원인 네이버를 통째로 막아 둔 robots.txt 가 "허용" 으로
        # 통과하던 것이 이 검사의 가장 큰 구멍이었다.
        refusals = {
            agent: site.robots.decide(path_of(page.url), user_agent=agent)
            for agent in REPORTED_CRAWLERS
        }
        refused = {agent: d for agent, d in refusals.items() if not d.allowed}
        if not refused:
            continue
        blocked.append(page)
        blocked_agents.update(refused)
        decision = next(iter(refused.values()))
        detail[page.url] = {
            "matched_rule": decision.matched_rule,
            "line": decision.line_number,
            "group": list(decision.group_agents),
            "blocked_agents": sorted(refused),
        }
        evidence.append(
            ledger.of(
                "matched_rule",
                url=page.url,
                payload=f"{decision.matched_rule} @L{decision.line_number}",
                excerpt=decision.reason_ko,
                detail={"line_number": decision.line_number},
            )
        )

    result = url_ratio_outcome(
        "seo.robots.txt_allows_url",
        affected=blocked,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=detail or None,
        clean_note_ko=(
            "robots.txt가 "
            + "·".join(CRAWLER_LABELS_KO.get(a, a) for a in REPORTED_CRAWLERS)
            + " 크롤러의 수집을 막지 않습니다."
        ),
        # 어느 검색엔진이 막혔는지가 곧 조치 대상이다. "차단됨" 만으로는 어디를 고쳐야
        # 할지 알 수 없고, 국내 사이트는 대개 한쪽만 막혀 있다.
        affected_note_ko=(
            f"{len(blocked)}개 URL이 robots.txt 규칙으로 차단되어 있습니다. 차단된 크롤러: "
            + ", ".join(CRAWLER_LABELS_KO.get(a, a) for a in sorted(blocked_agents))
        ),
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    rules = ", ".join(str(value.get("matched_rule")) for value in detail.values())
    return result, [
        issue(
            context,
            "seo.robots.txt_allows_url",
            title_ko="robots.txt가 주요 URL의 크롤링을 막고 있습니다",
            summary_ko=(
                f"{len(blocked)}개 URL이 robots.txt 규칙에 걸려 크롤링되지 않습니다. "
                + "차단된 크롤러는 "
                + ", ".join(CRAWLER_LABELS_KO.get(a, a) for a in sorted(blocked_agents))
                + f"이고, 적용된 규칙은 {rules}입니다."
            ),
            affected_urls=[page.url for page in blocked],
            evidence_ids=evidence,
            remediation_ko=(
                "공개해야 하는 경로를 막는 Disallow 규칙을 제거하거나, 더 구체적인 Allow 규칙을 "
                "같은 그룹에 추가해 해당 경로만 허용하십시오. 관리자 경로처럼 실제로 막아야 하는 "
                "규칙은 그대로 두십시오."
            ),
            reverification_ko="robots.txt 수정 후 해당 경로가 허용되는지 다시 확인합니다.",
            business_impact_ko=(
                "크롤링이 막힌 URL은 내용이 아무리 좋아도 검색 결과에 나오지 않습니다."
            ),
            fix_example="User-agent: *\nAllow: /\nDisallow: /admin/",
        )
    ]


# --------------------------------------------------------------------------- #
# seo.robots.meta_indexable
# --------------------------------------------------------------------------- #


def _meta_indexable(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    candidates = [page for page in site.pages if page.importance != "INTENTIONAL_NOINDEX"]
    if not candidates:
        return (
            not_applicable_outcome(
                "seo.robots.meta_indexable",
                "수집한 URL이 모두 의도적으로 색인에서 제외한 페이지입니다.",
            ),
            [],
        )

    blocked: list[PageObservation] = []
    evidence: list[str] = []
    detail: dict[str, object] = {}

    for page in candidates:
        meta = page.raw.meta_robots or ""
        header = (page.header("x-robots-tag") or "").lower()
        sources = [source for source in (meta, header) if source]
        if not any(_blocks_indexing(source) for source in sources):
            continue
        blocked.append(page)
        detail[page.url] = {"meta_robots": meta or None, "x_robots_tag": header or None}
        if meta:
            evidence.append(
                ledger.page_snippet(page, "dom_snippet", f'<meta name="robots" content="{meta}">')
            )
        if header:
            evidence.append(
                ledger.of(
                    "http_headers",
                    url=page.url,
                    payload=f"x-robots-tag: {header}",
                    excerpt=f"x-robots-tag: {header}",
                )
            )

    if not evidence:
        evidence = [ledger.page_snippet(site.pages[0], "dom_snippet", "meta robots 없음")]

    result = url_ratio_outcome(
        "seo.robots.meta_indexable",
        affected=blocked,
        evaluated=candidates,
        evidence_ids=evidence,
        observed_value=detail or None,
        clean_note_ko="색인을 막는 meta robots나 X-Robots-Tag가 없습니다.",
        affected_note_ko=f"{len(blocked)}개 URL이 noindex로 색인에서 제외되고 있습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.robots.meta_indexable",
            title_ko="noindex 지시어가 색인을 막고 있습니다",
            summary_ko=(
                f"{len(blocked)}개 URL에 noindex 지시어가 남아 있습니다. meta robots 태그나 "
                "X-Robots-Tag 응답 헤더 가운데 하나만 있어도 색인에서 제외됩니다."
            ),
            affected_urls=[page.url for page in blocked],
            evidence_ids=evidence,
            remediation_ko=(
                "공개해야 하는 페이지에서 noindex 지시어를 제거하십시오. 개발·스테이징 환경의 "
                "설정이 그대로 넘어온 경우가 많으므로 배포 설정도 함께 확인하십시오."
            ),
            reverification_ko=(
                "배포 후 해당 URL의 응답 헤더와 head 영역에 noindex가 없는지 확인합니다."
            ),
            business_impact_ko="noindex가 남아 있는 동안에는 검색 결과에서 완전히 사라집니다.",
            fix_example='<meta name="robots" content="index, follow">',
        )
    ]


# --------------------------------------------------------------------------- #
# seo.canonical.declared_and_consistent
# --------------------------------------------------------------------------- #


def _canonical_consistent(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    inconsistent: list[PageObservation] = []
    evidence: list[str] = []
    reasons: dict[str, str] = {}

    declared_alternates = {
        page.url: {code: normalise_url(href) for code, href in page.raw.hreflang}
        for page in site.pages
        if page.raw.hreflang
    }

    for page in site.pages:
        problem = _canonical_problem(page, site, declared_alternates)
        if problem is None:
            continue
        inconsistent.append(page)
        reasons[page.url] = problem
        evidence.append(
            ledger.page_snippet(
                page,
                "dom_snippet",
                f'<link rel="canonical" href="{page.raw.canonical}"> — {problem}',
            )
        )

    if not evidence:
        evidence = [
            ledger.page_snippet(
                site.pages[0],
                "dom_snippet",
                f'<link rel="canonical" href="{site.pages[0].raw.canonical}">',
            )
        ]

    result = url_ratio_outcome(
        "seo.canonical.declared_and_consistent",
        affected=inconsistent,
        evaluated=list(site.pages),
        evidence_ids=evidence,
        observed_value=reasons or None,
        clean_note_ko="canonical이 선언되어 있고 다른 신호와 어긋나지 않습니다.",
        affected_note_ko=(
            f"{len(inconsistent)}개 URL의 canonical이 누락되었거나 다른 신호와 어긋납니다."
        ),
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.canonical.declared_and_consistent",
            title_ko="canonical 선언이 없거나 다른 신호와 어긋납니다",
            summary_ko=(
                f"{len(inconsistent)}개 URL에서 문제가 확인되었습니다: "
                + "; ".join(f"{url} — {reason}" for url, reason in list(reasons.items())[:5])
            ),
            affected_urls=[page.url for page in inconsistent],
            evidence_ids=evidence,
            remediation_ko=(
                "각 페이지 head에 자기 자신을 가리키는 절대 주소 canonical을 하나만 두십시오. "
                "hreflang을 함께 쓰는 경우 canonical은 같은 언어판 자기 주소를 가리켜야 하며, "
                "언어판끼리는 서로를 모두 alternate로 선언해야 합니다."
            ),
            reverification_ko=(
                "수정 후 각 URL의 canonical과 hreflang 집합을 다시 수집해 비교합니다."
            ),
            business_impact_ko=(
                "신호가 어긋나면 검색엔진이 어느 주소를 대표로 볼지 스스로 골라, 원하지 않는 "
                "페이지가 노출될 수 있습니다."
            ),
            fix_example='<link rel="canonical" href="https://example.kr/ko/">',
        )
    ]


def _canonical_problem(
    page: PageObservation,
    site: SiteObservation,
    declared_alternates: dict[str, dict[str, str]],
) -> str | None:
    if page.raw.canonical is None:
        return "canonical이 선언되지 않았습니다"
    if page.raw.canonical_count > 1:
        return f"canonical이 {page.raw.canonical_count}개 선언되어 있습니다"

    target = resolve(page.url, page.raw.canonical)
    if target is None:
        return "canonical 주소를 해석할 수 없습니다"

    destination = site.page(target)
    if destination is not None and not destination.is_ok:
        return f"canonical 대상이 {destination.status}로 응답합니다"

    alternates = declared_alternates.get(page.url)
    if alternates:
        self_reference = [code for code, href in alternates.items() if href == page.url]
        if not self_reference:
            return "hreflang 집합에 자기 자신이 없습니다"
        if target != page.url:
            return "hreflang 자기 참조가 있는데 canonical은 다른 언어판을 가리킵니다"
        for href in alternates.values():
            sibling = site.page(href)
            if sibling is None:
                continue
            sibling_alternates = declared_alternates.get(sibling.url, {})
            if page.url not in sibling_alternates.values():
                return f"{sibling.url}의 hreflang이 이 페이지를 되가리키지 않습니다"
    return None


# --------------------------------------------------------------------------- #
# seo.canonical.not_cross_domain
# --------------------------------------------------------------------------- #


def _canonical_not_cross_domain(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    declared = [page for page in site.pages if page.raw.canonical]
    if not declared:
        return (
            unknown_outcome(
                "seo.canonical.not_cross_domain",
                "canonical을 선언한 URL이 없어 도메인 일치 여부를 확인할 수 없습니다.",
            ),
            [],
        )

    crossing: list[PageObservation] = []
    evidence: list[str] = []
    detail: dict[str, str] = {}

    for page in declared:
        target = resolve(page.url, page.raw.canonical or "")
        if target is None or same_site(page.url, target):
            continue
        crossing.append(page)
        detail[page.url] = target
        evidence.append(
            ledger.page_snippet(
                page, "dom_snippet", f'<link rel="canonical" href="{page.raw.canonical}">'
            )
        )

    if not evidence:
        evidence = [
            ledger.page_snippet(
                declared[0],
                "dom_snippet",
                f'<link rel="canonical" href="{declared[0].raw.canonical}">',
            )
        ]

    result = url_ratio_outcome(
        "seo.canonical.not_cross_domain",
        affected=crossing,
        evaluated=declared,
        evidence_ids=evidence,
        observed_value=detail or None,
        clean_note_ko="canonical이 모두 자사 도메인을 가리킵니다.",
        affected_note_ko=f"{len(crossing)}개 URL의 canonical이 외부 도메인을 가리킵니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    domains = ", ".join(sorted({registrable_domain(host_of(url)) for url in detail.values()}))
    return result, [
        issue(
            context,
            "seo.canonical.not_cross_domain",
            title_ko="canonical이 외부 도메인을 가리킵니다",
            summary_ko=(
                f"{len(crossing)}개 URL의 canonical이 {domains} 도메인을 대표 주소로 지정하고 "
                "있습니다. 자사 페이지의 색인 권한을 외부 사이트에 넘기는 설정입니다."
            ),
            affected_urls=[page.url for page in crossing],
            evidence_ids=evidence,
            remediation_ko=(
                "canonical 주소를 자사 도메인의 해당 페이지 주소로 정정하십시오. 블로그 등에 "
                "동일 원고를 함께 올린 경우, 외부 채널 쪽에서 자사 페이지를 canonical로 지정하는 "
                "것이 맞는 방향입니다."
            ),
            reverification_ko="정정 후 canonical 호스트가 자사 도메인과 같은지 다시 확인합니다.",
            business_impact_ko=(
                "검색엔진이 외부 주소를 대표로 삼아 자사 페이지가 검색 결과에서 밀려납니다."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# seo.sitemap.*
# --------------------------------------------------------------------------- #


def _sitemap_discoverable(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    from_robots = tuple(site.robots.sitemaps) if site.robots else ()
    fetched = tuple(site.sitemaps)
    found = bool(from_robots or fetched)

    evidence = [
        ledger.of(
            "robots_txt",
            url=None,
            payload=site.robots.raw if site.robots else "robots.txt 미수집",
            excerpt=(
                "Sitemap: " + ", ".join(from_robots)
                if from_robots
                else "robots.txt에 Sitemap 선언 없음"
            ),
            detail={"declared": list(from_robots)},
        )
    ]
    for url in fetched:
        evidence.append(
            ledger.of(
                "http_response",
                url=url,
                payload=context.sitemap_documents[url],
                excerpt=f"사이트맵 응답 수신: {url}",
            )
        )

    result = site_outcome(
        "seo.sitemap.discoverable",
        passed=found,
        evidence_ids=evidence,
        observed_value={"robots_declared": list(from_robots), "fetched": list(fetched)},
        note=(
            "robots.txt 또는 관례 경로에서 사이트맵을 확인했습니다."
            if found
            else "robots.txt와 관례 경로 어디에서도 사이트맵을 찾지 못했습니다."
        ),
    )
    if found:
        return result, []

    return result, [
        issue(
            context,
            "seo.sitemap.discoverable",
            title_ko="사이트맵을 찾을 수 없습니다",
            summary_ko=(
                "robots.txt에 Sitemap 선언이 없고 /sitemap.xml 관례 경로에서도 사이트맵을 "
                "받지 못했습니다. 검색엔진이 URL 목록을 통째로 받을 방법이 없습니다."
            ),
            affected_urls=[site.entry_url],
            evidence_ids=evidence,
            remediation_ko=(
                "사이트맵을 생성해 /sitemap.xml에 두고 robots.txt 마지막 줄에 "
                "`Sitemap: https://도메인/sitemap.xml`을 추가하십시오."
            ),
            reverification_ko="robots.txt를 다시 수집해 Sitemap 선언과 사이트맵 응답을 확인합니다.",
            business_impact_ko=(
                "새로 만든 페이지가 검색엔진에 알려지기까지 걸리는 시간이 크게 늘어납니다."
            ),
            fix_example="Sitemap: https://example.kr/sitemap.xml",
        )
    ]


def _sitemap_urls_valid(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    locations = site.sitemap_locations
    if not locations:
        return (
            unknown_outcome(
                "seo.sitemap.urls_valid",
                "읽을 수 있는 사이트맵이 없어 등록된 URL의 유효성을 확인하지 못했습니다.",
            ),
            [],
        )

    evidence = [
        ledger.of(
            "sitemap_document",
            url=url,
            payload=context.sitemap_documents[url],
            excerpt=f"{parsed.kind}: {len(parsed.locations)}개 URL",
            detail={"kind": parsed.kind, "count": len(parsed.locations)},
        )
        for url, parsed in site.sitemaps.items()
    ]

    invalid: dict[str, str] = {}
    for location in locations:
        reason = _sitemap_location_problem(location, site)
        if reason is not None:
            invalid[location] = reason

    if invalid:
        evidence.append(
            ledger.of(
                "http_response",
                url=site.entry_url,
                payload="\n".join(f"{url}: {reason}" for url, reason in invalid.items()),
                excerpt="; ".join(f"{url} — {reason}" for url, reason in list(invalid.items())[:5]),
                detail={"invalid": len(invalid), "total": len(locations)},
            )
        )

    result = outcome(
        "seo.sitemap.urls_valid",
        CheckStatus.PASS if not invalid else CheckStatus.FAIL,
        confidence_level=DIRECT,
        affected=float(len(invalid)),
        evaluated=float(len(locations)),
        evidence_ids=evidence,
        observed_value=invalid or None,
        note=(
            f"사이트맵에 등록된 {len(locations)}개 URL이 모두 유효합니다."
            if not invalid
            else f"등록된 {len(locations)}개 URL 가운데 {len(invalid)}개가 유효하지 않습니다."
        ),
    )
    if not invalid:
        return result, []

    return result, [
        issue(
            context,
            "seo.sitemap.urls_valid",
            title_ko="사이트맵에 유효하지 않은 URL이 있습니다",
            summary_ko=(
                f"사이트맵에 등록된 {len(locations)}개 URL 가운데 {len(invalid)}개가 "
                "정상 응답하지 않거나 색인할 수 없는 주소입니다."
            ),
            affected_urls=list(invalid),
            evidence_ids=evidence,
            remediation_ko=(
                "사이트맵에는 200으로 응답하고 색인 가능한 자사 도메인 URL만 남기십시오. "
                "삭제된 페이지, robots.txt로 막은 경로, 외부 도메인 주소는 제외해야 합니다."
            ),
            reverification_ko="사이트맵을 다시 생성한 뒤 등록된 URL을 재수집해 상태를 확인합니다.",
            business_impact_ko=(
                "유효하지 않은 URL이 많으면 사이트맵 전체의 신뢰도가 떨어져 처리 우선순위가 "
                "밀립니다."
            ),
        )
    ]


def _sitemap_location_problem(location: str, site: SiteObservation) -> str | None:
    if not same_site(site.entry_url, location):
        return "외부 도메인 주소입니다"
    page = site.page(location)
    if page is not None and not page.is_ok:
        return f"{page.status}로 응답합니다"
    if site.robots is not None:
        decision = site.robots.decide(path_of(location), user_agent=CRAWLER_AGENT_NAME)
        if not decision.allowed:
            return f"robots.txt에서 차단되어 있습니다 ({decision.matched_rule})"
    if page is not None:
        meta = page.raw.meta_robots or ""
        header = (page.header("x-robots-tag") or "").lower()
        if any(d in meta for d in _BLOCKING_DIRECTIVES) or any(
            d in header for d in _BLOCKING_DIRECTIVES
        ):
            return "noindex로 색인에서 제외되어 있습니다"
    return None


# --------------------------------------------------------------------------- #
# seo.crawl.*
# --------------------------------------------------------------------------- #


def _orphan_key_pages(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    candidates = [page for page in site.key_pages if page.url != site.entry_url]
    if not candidates:
        return (
            unknown_outcome(
                "seo.crawl.no_orphan_key_pages",
                "진입 URL 외에 수집된 주요 페이지가 없어 내부 링크 도달성을 판단하지 못했습니다.",
            ),
            [],
        )

    orphans = [page for page in candidates if not site.inbound.get(page.url)]
    evidence = [
        ledger.of(
            "link_graph",
            url=site.entry_url,
            payload="\n".join(
                f"{source} -> {target}"
                for source, targets in site.outbound.items()
                for target in targets
            )
            or "내부 링크 없음",
            excerpt=f"수집 페이지 {len(site.pages)}개, 내부 링크 "
            f"{sum(len(t) for t in site.outbound.values())}개",
            detail={"orphans": [page.url for page in orphans]},
        )
    ]

    result = url_ratio_outcome(
        "seo.crawl.no_orphan_key_pages",
        affected=orphans,
        evaluated=candidates,
        evidence_ids=evidence,
        observed_value=[page.url for page in orphans] or None,
        clean_note_ko="주요 페이지가 모두 내부 링크로 도달 가능합니다.",
        affected_note_ko=f"{len(orphans)}개 주요 페이지로 향하는 내부 링크가 없습니다.",
    )
    if result.status is not CheckStatus.FAIL:
        return result, []

    return result, [
        issue(
            context,
            "seo.crawl.no_orphan_key_pages",
            title_ko="내부 링크가 없는 주요 페이지가 있습니다",
            summary_ko=(
                f"{len(orphans)}개 주요 페이지가 수집한 어떤 페이지에서도 링크되지 않습니다. "
                "사이트맵에 있더라도 내부 링크가 없으면 중요도가 낮게 평가됩니다."
            ),
            affected_urls=[page.url for page in orphans],
            evidence_ids=evidence,
            remediation_ko=(
                "해당 페이지를 주요 메뉴나 관련 문서 본문에서 링크하십시오. 링크 문구에는 "
                "페이지 주제를 담아 무엇에 대한 문서인지 드러나게 작성합니다."
            ),
            reverification_ko="링크 추가 후 재수집해 해당 URL에 유입 링크가 잡히는지 확인합니다.",
            business_impact_ko="유입 링크가 없는 페이지는 크롤링 빈도와 평가가 함께 낮아집니다.",
        )
    ]


def _broken_internal_links(
    context: CollectionContext, site: SiteObservation, ledger: EvidenceLedger
) -> tuple[CheckOutcome, list[IssueDraft]]:
    linked_targets = {target for targets in site.outbound.values() for target in targets}
    checked = len(linked_targets) + len(site.broken_targets)
    if checked == 0:
        return (
            unknown_outcome(
                "seo.crawl.no_broken_internal_links",
                "수집 범위 안에서 확인할 수 있는 내부 링크가 없어 판단하지 못했습니다.",
            ),
            [],
        )

    evidence = [
        ledger.of(
            "link_graph",
            url=site.entry_url,
            payload="\n".join(
                f"{target} <- {', '.join(sources)}"
                for target, sources in site.broken_targets.items()
            )
            or "끊어진 내부 링크 없음",
            excerpt=f"확인한 내부 링크 대상 {checked}개, 오류 응답 {len(site.broken_targets)}개",
            detail={"broken": list(site.broken_targets)},
        )
    ]
    for target in site.broken_targets:
        page = site.page(target)
        if page is not None:
            evidence.append(
                ledger.page_snippet(page, "http_response", f"{page.status} {page.url}")
            )

    result = outcome(
        "seo.crawl.no_broken_internal_links",
        CheckStatus.PASS if not site.broken_targets else CheckStatus.FAIL,
        confidence_level=DIRECT,
        affected=float(len(site.broken_targets)),
        evaluated=float(checked),
        evidence_ids=evidence,
        observed_value={
            target: list(sources) for target, sources in site.broken_targets.items()
        }
        or None,
        note=(
            "내부 링크가 모두 정상 응답하는 URL을 가리킵니다."
            if not site.broken_targets
            else f"{len(site.broken_targets)}개 내부 링크 대상이 오류로 응답합니다."
        ),
    )
    if not site.broken_targets:
        return result, []

    sources = sorted({source for values in site.broken_targets.values() for source in values})
    return result, [
        issue(
            context,
            "seo.crawl.no_broken_internal_links",
            title_ko="내부 링크가 오류 페이지를 가리킵니다",
            summary_ko=(
                f"{len(site.broken_targets)}개 대상이 4xx 또는 5xx로 응답하는데도 "
                f"{len(sources)}개 페이지에서 계속 링크되고 있습니다."
            ),
            affected_urls=list(site.broken_targets) + sources,
            evidence_ids=evidence,
            remediation_ko=(
                "링크를 현재 살아 있는 주소로 교체하거나, 대체할 문서가 없으면 링크를 "
                "제거하십시오. "
                "주소만 바뀐 경우에는 기존 주소에 301 리다이렉트를 설정하는 편이 낫습니다."
            ),
            reverification_ko="수정 후 재수집해 해당 대상이 2xx로 응답하는지 확인합니다.",
            business_impact_ko=(
                "오류 페이지로 이어지는 링크는 방문자가 이탈하는 지점이 되고 크롤링 예산도 "
                "낭비합니다."
            ),
        )
    ]


__all__ = ["MAX_SANE_HOPS", "CrawlIndexabilityCollector"]
