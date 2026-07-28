#!/usr/bin/env python
"""Run a live SEO and GEO readiness diagnosis against a real site.

Every fetch goes through :class:`SafeFetcher`, so the SSRF guard applies here exactly as
it does in the product: the address is validated once and the connection is pinned to it,
and each redirect is re-validated.

VEO identifies itself, honours ``robots.txt`` for its own crawling, and pauses between
requests. A diagnostic tool that hammers the site it is diagnosing is a bad tool.

    python scripts/diagnose.py https://example.com --pages 5
"""

from __future__ import annotations

import argparse
import sys
import time
from urllib.parse import urljoin, urlparse

from veo.collect.contract import CollectionContext
from veo.common.security.fetcher import (
    DEFAULT_USER_AGENT,
    FetchedDocument,
    FetchError,
    SafeFetcher,
)
from veo.common.security.url_guard import UrlGuard, UrlRejectedError
from veo.core.settings import get_provider_credentials
from veo.geo.service import run_geo_readiness
from veo.scoring import CheckStatus, latest_published
from veo.seo.parsing.robots import parse_robots
from veo.seo.service import run_seo_scan

BAR = "─" * 78


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VEO 실사이트 진단")
    parser.add_argument("url", help="진단할 URL")
    parser.add_argument("--pages", type=int, default=5, help="가져올 최대 페이지 수")
    parser.add_argument("--delay", type=float, default=1.0, help="요청 간 대기 시간(초)")
    parser.add_argument("--show-passing", action="store_true", help="통과 항목도 출력")
    args = parser.parse_args(argv)

    fetcher = SafeFetcher(guard=UrlGuard())

    print(f"\n{BAR}\nVEO 진단  ·  {args.url}")
    print(f"수집기: {DEFAULT_USER_AGENT}\n{BAR}")

    robots_txt = _fetch_robots(fetcher, args.url)
    rules = parse_robots(robots_txt or "")

    documents: dict[str, FetchedDocument] = {}
    primary = _fetch(fetcher, args.url)
    if primary is None:
        print("\n대상 URL을 가져오지 못했습니다. 진단을 중단합니다.")
        return 1
    documents[primary.final_url] = primary

    for url in _internal_links(primary, limit=args.pages - 1):
        if url in documents:
            continue
        if rules is not None and not _allowed(rules, url):
            print(f"  robots.txt 가 금지 — 건너뜀: {url}")
            continue
        time.sleep(args.delay)
        document = _fetch(fetcher, url)
        if document is not None:
            documents[document.final_url] = document

    sitemaps = _fetch_sitemaps(fetcher, args.url, rules, delay=args.delay)

    print(f"\n수집 완료: {len(documents)}개 문서, robots.txt "
          f"{'있음' if robots_txt else '없음'}, sitemap {len(sitemaps)}개")

    provider_states = get_provider_credentials().states()
    enabled = [name for name, state in provider_states.items() if str(state) == "ENABLED"]
    print(f"활성 제공자: {', '.join(enabled) if enabled else '없음'}")

    _report_seo(args.url, documents, primary, robots_txt, sitemaps, provider_states,
                args.show_passing)
    _report_geo(args.url, documents, primary, robots_txt, sitemaps, provider_states,
                args.show_passing)

    print(f"\n{BAR}")
    print("점수는 검색 순위 예측이 아니라 기술·구조 준비도입니다.")
    print("자격증명이 없는 항목은 0점이 아니라 '측정 불가'이며 coverage에 반영됩니다.")
    print(BAR)
    return 0


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #


def _fetch(fetcher: SafeFetcher, url: str) -> FetchedDocument | None:
    try:
        document = fetcher.fetch(url)
    except UrlRejectedError as exc:
        print(f"  차단됨 ({exc}): {url}")
        return None
    except FetchError as exc:
        print(f"  가져오기 실패 ({type(exc).__name__}): {url}")
        return None

    hops = " → ".join(f"{hop.status}@{hop.resolved_ip}" for hop in document.hops)
    print(f"  {document.status}  {document.final_url}  [{hops}]  {len(document.body)}B")
    return document


def _fetch_robots(fetcher: SafeFetcher, url: str) -> str | None:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    document = _fetch(fetcher, robots_url)
    if document is None or document.status != 200:
        return None
    return document.text()


def _fetch_sitemaps(
    fetcher: SafeFetcher, url: str, rules: object, *, delay: float
) -> dict[str, str]:
    """Sitemaps declared in robots.txt, falling back to the conventional path.

    Without this the sitemap checks report "측정 불가" and the tool looks like it found a
    problem the site does not have — the diagnosis would be wrong about its own coverage.
    """
    parsed = urlparse(url)
    declared = list(getattr(rules, "sitemaps", ()) or ())
    candidates = declared or [f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"]

    found: dict[str, str] = {}
    for candidate in candidates[:5]:
        time.sleep(delay)
        document = _fetch(fetcher, candidate)
        if document is not None and document.status == 200:
            found[document.final_url] = document.text()
    return found


def _internal_links(document: FetchedDocument, *, limit: int) -> list[str]:
    """Same-host links from the primary page, in document order."""
    from veo.seo.parsing.html import parse_html

    parsed = parse_html(document.text())
    origin = urlparse(document.final_url)
    found: list[str] = []
    for anchor in parsed.links:
        if not anchor.href:
            continue
        absolute = urljoin(document.final_url, anchor.href)
        candidate = urlparse(absolute)
        if candidate.scheme not in {"http", "https"}:
            continue
        if candidate.netloc != origin.netloc:
            continue
        clean = absolute.split("#", 1)[0]
        if clean not in found and clean != document.final_url:
            found.append(clean)
        if len(found) >= limit:
            break
    return found


def _allowed(rules: object, url: str) -> bool:
    """Honour the site's own robots.txt for VEO's crawling.

    The SEO engine separately *reports* on robots.txt; this is VEO obeying it.
    """
    decide = getattr(rules, "decide", None)
    if not callable(decide):
        return True
    return bool(decide(urlparse(url).path or "/", user_agent="veo-bot").allowed)


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def _report_seo(url, documents, primary, robots_txt, sitemaps, provider_states,
                show_passing) -> None:
    spec = latest_published("veo.seo.readiness")
    context = CollectionContext(
        target_url=url,
        spec=spec,
        documents=documents,
        primary_document=primary,
        robots_txt=robots_txt,
        sitemap_documents=sitemaps,
        provider_states=provider_states,
    )
    report = run_seo_scan(context)
    _print_report("SEO 기술 준비도", report, show_passing)


def _report_geo(url, documents, primary, robots_txt, sitemaps, provider_states,
                show_passing) -> None:
    spec = latest_published("veo.geo.readiness")
    context = CollectionContext(
        target_url=url,
        spec=spec,
        documents=documents,
        primary_document=primary,
        robots_txt=robots_txt,
        sitemap_documents=sitemaps,
        provider_states=provider_states,
    )
    report = run_geo_readiness(context)
    _print_report("GEO 준비도 (AI 답변 엔진 대상)", report, show_passing)


def _print_report(title: str, report: object, show_passing: bool) -> None:
    score = report.score  # type: ignore[attr-defined]
    print(f"\n{BAR}\n{title}\n{BAR}")
    print(f"  점수      {score.overall_score}   구간 {score.band_id}")
    if score.overall_score != score.overall_score_before_caps:
        print(f"  상한 적용 전 {score.overall_score_before_caps}")
    print(f"  coverage  {score.coverage}    confidence {score.confidence}")
    print(f"  방법론    {score.spec_id}@{score.spec_version}  ({score.spec_checksum[:12]}…)")

    for cap in score.applied_caps:
        print(f"\n  [상한 {cap.max_overall_score}점] {cap.reason_ko}")
        print(f"      해제 조건: {cap.release_condition_ko}")
    for gate in score.gates:
        print(f"\n  [{gate.status_code}] {gate.label_ko}")

    print("\n  영역별")
    for category in score.categories:
        value = "해당없음" if category.score is None else f"{category.score:6.2f}"
        print(f"    {category.name_ko:22s} {value}  (가중치 {category.weight:g}, "
              f"coverage {category.coverage:.2f})")

    buckets: dict[CheckStatus, list] = {}
    for outcome in score.outcomes:
        buckets.setdefault(outcome.status, []).append(outcome)

    for status, label in (
        (CheckStatus.FAIL, "실패"),
        (CheckStatus.WARNING, "주의"),
        (CheckStatus.UNKNOWN, "측정 불가"),
        (CheckStatus.NOT_APPLICABLE, "해당 없음"),
    ):
        items = buckets.get(status, [])
        if not items:
            continue
        print(f"\n  {label} ({len(items)})")
        for outcome in items:
            note = f" — {outcome.note}" if getattr(outcome, "note", None) else ""
            print(f"    · {outcome.check_id}{note}")

    if show_passing and buckets.get(CheckStatus.PASS):
        print(f"\n  통과 ({len(buckets[CheckStatus.PASS])})")
        for outcome in buckets[CheckStatus.PASS]:
            print(f"    · {outcome.check_id}")

    issues = getattr(report, "issues", ())
    if issues:
        print(f"\n  조치 항목 {len(issues)}건")
        for issue in list(issues)[:8]:
            print(f"    · [{issue.remediation_owner}] {issue.title_ko}")
            print(f"        {issue.remediation_ko}")


if __name__ == "__main__":
    sys.exit(main())
