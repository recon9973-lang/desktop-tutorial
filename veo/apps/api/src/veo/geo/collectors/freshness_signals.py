"""최신성·변경 신호 — and the difference between a fresh page and a fresh date.

A ``dateModified`` that moves while the bytes stay identical is not a freshness signal.
It is a claim that something changed, made to a reader who cannot check, and once an
answer engine learns that a site's dates do not track its content the dates stop being
worth anything. Detecting it needs history: the same URL, seen before, with the hash of
what it said then.

Without that history the honest answer is UNKNOWN. It costs no points, lowers coverage,
and leaves "we have not been able to check this yet" visible on the screen — which is
what a first scan should say.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
    not_applicable_outcome,
    unknown_outcome,
)
from veo.collect.sample import absent_in_sample_outcome
from veo.geo.entity_graph import EntityGraph
from veo.geo.pagekind import KINDS_EXPECTING_DATES
from veo.geo.parsing import PageDocument
from veo.geo.reporting import (
    DIRECT,
    HIGH,
    LOW,
    MEDIUM,
    finding,
    observed,
    sample_scope,
    snippet_evidence,
)
from veo.geo.view import TargetView, build_view
from veo.scoring import CheckOutcome, CheckStatus

CHECK_IDS = frozenset(
    {
        "geo.fresh.dates_present",
        "geo.fresh.dates_truthful",
        "geo.fresh.sitemap_lastmod_reliable",
        "geo.fresh.no_stale_claims",
    }
)

CONTENT_HISTORY_PROVIDER = "content_history"

_LASTMOD_PATTERN = re.compile(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", re.IGNORECASE)
_LOC_PATTERN = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)

#: "2019년 기준" — a figure explicitly anchored to a year that has since passed.
_ANCHORED_YEAR = re.compile(r"(\d{4})\s*년\s*(?:기준|현재|말\s*기준|자료)")
#: "2020년 12월까지" — a promise with an end date.
_DEADLINE = re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(?:\d{1,2}\s*일\s*)?까지")

#: A figure anchored more than this many years back is stale rather than historical.
_STALE_YEAR_DISTANCE = 2


class FreshnessSignalsCollector:
    """Observes dates, and whether they can be believed."""

    category_id = "freshness_signals"

    @property
    def check_ids(self) -> frozenset[str]:
        return CHECK_IDS

    def collect(self, context: CollectionContext) -> CollectionResult:
        view = build_view(context)
        page = view.page
        evidence: list[EvidenceRecord] = list(view.evidence)
        issues: list[IssueDraft] = []
        outcomes: list[CheckOutcome] = []
        base = view.evidence_ids

        published, modified = _declared_dates(page, view.graph)
        expects_dates = view.kind in KINDS_EXPECTING_DATES

        # -- dates present ------------------------------------------------ #
        if not expects_dates:
            outcomes.append(
                not_applicable_outcome(
                    "geo.fresh.dates_present",
                    f"{view.kind} 유형의 페이지에는 발행·수정일 표기가 필요하지 않습니다.",
                    evidence_ids=base,
                )
            )
        else:
            value = {"published": published, "modified": modified}
            if published and modified:
                status, note = CheckStatus.PASS, "발행일과 수정일이 모두 표시됩니다."
            elif published or modified:
                status, note = CheckStatus.WARNING, "발행일과 수정일 중 하나만 표시됩니다."
            else:
                status, note = CheckStatus.FAIL, "발행일도 수정일도 표시되지 않습니다."
            outcomes.append(
                observed(
                    "geo.fresh.dates_present",
                    status,
                    confidence_level=DIRECT,
                    note_ko=note,
                    evidence_ids=base,
                    observed_value=value,
                )
            )
            if status is CheckStatus.FAIL:
                issues.append(
                    finding(
                        "geo.fresh.dates_present",
                        title_ko="발행일과 수정일이 없습니다",
                        summary_ko="내용이 언제 쓰였고 언제 갱신됐는지 알 수 없습니다.",
                        remediation_ko=(
                            "datePublished와 dateModified를 구조화 데이터와 본문에 함께 표기하세요."
                        ),
                        remediation_owner="DEVELOPER",
                        urls=[view.url],
                        evidence_ids=base,
                    )
                )

        # -- dates truthful ------------------------------------------------ #
        truthful_outcome, truthful_issue, truthful_evidence = self._truthfulness_outcome(
            context, view, modified, base
        )
        outcomes.append(truthful_outcome)
        evidence.extend(truthful_evidence)
        if truthful_issue is not None:
            issues.append(truthful_issue)

        # -- sitemap --------------------------------------------------------- #
        outcomes.append(self._sitemap_outcome(context, view.url, modified, evidence))

        # -- stale claims ------------------------------------------------------ #
        outcomes.append(self._stale_outcome(page, context, base))
        if outcomes[-1].status is CheckStatus.FAIL:
            issues.append(
                finding(
                    "geo.fresh.no_stale_claims",
                    title_ko="오래된 시점에 묶인 정보가 남아 있습니다",
                    summary_ko="지난 연도를 기준으로 삼은 수치나 이미 지난 기한이 본문에 있습니다.",
                    remediation_ko="기준 연도와 기한을 갱신하거나 문장에서 제거하세요.",
                    remediation_owner="BUSINESS_OWNER",
                    urls=[view.url],
                    evidence_ids=base,
                )
            )

        return CollectionResult(
            outcomes=tuple(outcomes), evidence=tuple(evidence), issues=tuple(issues)
        )

    # ------------------------------------------------------------------ #

    def _truthfulness_outcome(
        self,
        context: CollectionContext,
        view: TargetView,
        modified: str,
        evidence_ids: tuple[str, ...],
    ) -> tuple[CheckOutcome, IssueDraft | None, list[EvidenceRecord]]:
        if not modified:
            return (
                not_applicable_outcome(
                    "geo.fresh.dates_truthful",
                    "수정일 표기가 없어 진실성을 평가할 대상이 없습니다.",
                    evidence_ids=evidence_ids,
                ),
                None,
                [],
            )
        if not context.provider_is_enabled(CONTENT_HISTORY_PROVIDER):
            return (
                unknown_outcome(
                    "geo.fresh.dates_truthful",
                    "이전 수집 이력이 없어 날짜가 실제 변경과 맞는지 확인할 수 없습니다.",
                    evidence_ids=evidence_ids,
                ),
                None,
                [],
            )

        history = _history_for(context, view.url)
        if not history or view.document is None:
            return (
                unknown_outcome(
                    "geo.fresh.dates_truthful",
                    "이 URL의 이전 수집 기록이 없어 비교할 대상이 없습니다.",
                    evidence_ids=evidence_ids,
                ),
                None,
                [],
            )

        previous = history[-1]
        previous_hash = str(previous.get("content_hash") or "")
        previous_modified = _date_part(str(previous.get("declared_modified") or ""))
        content_changed = previous_hash != view.document.content_hash
        date_changed = previous_modified != _date_part(modified)

        value = {
            "content_changed": content_changed,
            "declared_modified_changed": date_changed,
            "previous_modified": previous_modified,
            "current_modified": _date_part(modified),
        }
        record = snippet_evidence(
            view.url,
            "content_hash_history",
            f"{previous_hash} -> {view.document.content_hash}",
            detail=value,
        )

        if date_changed and not content_changed:
            outcome = observed(
                "geo.fresh.dates_truthful",
                CheckStatus.FAIL,
                confidence_level=HIGH,
                note_ko="본문 바이트가 그대로인데 수정일만 앞당겨졌습니다.",
                evidence_ids=(*evidence_ids, record.evidence_id),
                observed_value=value,
            )
            issue = finding(
                "geo.fresh.dates_truthful",
                title_ko="내용 변경 없이 수정일만 갱신됐습니다",
                summary_ko=(
                    f"이전 수집({previous_modified})과 현재({_date_part(modified)}) 사이에 "
                    "본문 해시가 전혀 바뀌지 않았습니다."
                ),
                remediation_ko="실제로 내용을 고쳤을 때만 dateModified를 갱신하세요.",
                remediation_owner="DEVELOPER",
                urls=[view.url],
                evidence_ids=(record.evidence_id,),
                business_impact_ko="날짜 신호 전체의 신뢰가 떨어집니다.",
                reverification_note_ko="다음 수집에서 해시와 수정일이 함께 움직이는지 확인합니다.",
            )
            return outcome, issue, [record]

        if content_changed and not date_changed:
            return (
                observed(
                    "geo.fresh.dates_truthful",
                    CheckStatus.WARNING,
                    confidence_level=HIGH,
                    note_ko="본문은 바뀌었는데 수정일이 그대로입니다.",
                    evidence_ids=(*evidence_ids, record.evidence_id),
                    observed_value=value,
                ),
                None,
                [record],
            )
        return (
            observed(
                "geo.fresh.dates_truthful",
                CheckStatus.PASS,
                confidence_level=HIGH,
                note_ko="수정일이 실제 본문 변경과 함께 움직입니다.",
                evidence_ids=(*evidence_ids, record.evidence_id),
                observed_value=value,
            ),
            None,
            [record],
        )

    def _sitemap_outcome(
        self,
        context: CollectionContext,
        target_url: str,
        modified: str,
        evidence: list[EvidenceRecord],
    ) -> CheckOutcome:
        if not context.sitemap_documents:
            # "sitemap 이 없다" 와 "우리가 sitemap 을 못 가져왔다" 는 다른 사실이다.
            # 사이트 전체를 돌고도 못 찾았다면 정말 없는 것이고, 일부만 봤다면 못 잰
            # 것이다. 뒤쪽을 해당 없음으로 접으면 덜 재는 편이 유리해진다.
            return absent_in_sample_outcome(
                sample_scope(context),
                "geo.fresh.sitemap_lastmod_reliable",
                absent_ko=(
                    "사이트 전체를 수집했으나 sitemap이 없어 lastmod를 평가할 "
                    "대상이 없습니다."
                ),
                subject_ko="sitemap",
            )

        entries: list[tuple[str, str]] = []
        for url, body in context.sitemap_documents.items():
            record = snippet_evidence(url, "sitemap_document", body, excerpt=body[:400])
            evidence.append(record)
            locations = _LOC_PATTERN.findall(body)
            stamps = _LASTMOD_PATTERN.findall(body)
            entries.extend(zip(locations, stamps, strict=False))
            if len(locations) > len(stamps):
                return observed(
                    "geo.fresh.sitemap_lastmod_reliable",
                    CheckStatus.WARNING,
                    confidence_level=DIRECT,
                    note_ko="lastmod가 없는 URL이 sitemap에 있습니다.",
                    evidence_ids=(record.evidence_id,),
                    observed_value={"urls": len(locations), "lastmod": len(stamps)},
                )

        evidence_ids = tuple(r.evidence_id for r in evidence if r.kind == "sitemap_document")
        today = context.collected_at.date()
        future = [stamp for _, stamp in entries if _is_after(stamp, today)]
        if future:
            return observed(
                "geo.fresh.sitemap_lastmod_reliable",
                CheckStatus.FAIL,
                confidence_level=DIRECT,
                note_ko="미래 날짜의 lastmod가 있어 값을 신뢰할 수 없습니다.",
                evidence_ids=evidence_ids,
                observed_value={"future_lastmod": future[:5]},
            )

        declared = _date_part(modified)
        for location, stamp in entries:
            if location == target_url and declared and _date_part(stamp) != declared:
                return observed(
                    "geo.fresh.sitemap_lastmod_reliable",
                    CheckStatus.WARNING,
                    confidence_level=MEDIUM,
                    note_ko="sitemap의 lastmod와 페이지의 수정일이 다릅니다.",
                    evidence_ids=evidence_ids,
                    observed_value={"sitemap": _date_part(stamp), "page": declared},
                )
        return observed(
            "geo.fresh.sitemap_lastmod_reliable",
            CheckStatus.PASS,
            confidence_level=DIRECT,
            note_ko="sitemap의 lastmod가 페이지 수정일과 어긋나지 않습니다.",
            evidence_ids=evidence_ids,
        )

    def _stale_outcome(
        self, page: PageDocument, context: CollectionContext, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        text = page.content_text
        today = context.collected_at.date()

        stale_years = [
            year
            for year in (int(m.group(1)) for m in _ANCHORED_YEAR.finditer(text))
            if today.year - year > _STALE_YEAR_DISTANCE
        ]
        expired = [
            match.group(0)
            for match in _DEADLINE.finditer(text)
            if _deadline_has_passed(match.group(1), match.group(2), today)
        ]
        value = {"anchored_years": stale_years, "expired_deadlines": expired}

        if stale_years or expired:
            return observed(
                "geo.fresh.no_stale_claims",
                CheckStatus.FAIL,
                confidence_level=LOW,
                note_ko="이미 지난 시점에 묶인 수치나 기한이 본문에 남아 있습니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )
        return observed(
            "geo.fresh.no_stale_claims",
            CheckStatus.PASS,
            confidence_level=LOW,
            note_ko="시간에 묶인 정보가 현재 기준에서 어긋나지 않습니다.",
            evidence_ids=evidence_ids,
            observed_value=value,
        )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _declared_dates(page: PageDocument, graph: EntityGraph) -> tuple[str, str]:
    published = page.property_value("article:published_time")
    modified = page.property_value("article:modified_time")

    for node in graph.nodes:
        published = published or str(node.raw.get("datePublished") or "")
        modified = modified or str(node.raw.get("dateModified") or "")

    stamps = [t.datetime_attribute for t in page.timestamps if t.datetime_attribute]
    if not published and stamps:
        published = stamps[0]
    if not modified and len(stamps) > 1:
        modified = stamps[-1]
    return published, modified


def _history_for(context: CollectionContext, url: str) -> Sequence[Mapping[str, Any]]:
    payload = context.provider_payloads.get(CONTENT_HISTORY_PROVIDER)
    if not isinstance(payload, dict):
        return ()
    entries = payload.get(url)
    if not isinstance(entries, list):
        return ()
    return [entry for entry in entries if isinstance(entry, dict)]


def _date_part(value: str) -> str:
    return value[:10] if value else ""


def _is_after(value: str, today: date) -> bool:
    stamp = _to_date(value)
    return stamp is not None and stamp > today


def _deadline_has_passed(year: str, month: str, today: date) -> bool:
    try:
        stated = date(int(year), int(month), 1)
    except ValueError:
        return False
    return stated < today.replace(day=1)


def _to_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


__all__ = ["CHECK_IDS", "CONTENT_HISTORY_PROVIDER", "FreshnessSignalsCollector"]
