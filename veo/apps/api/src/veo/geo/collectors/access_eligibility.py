"""접근·검색 적격성 — can a crawler reach this page, and is it allowed to.

The category exists to separate three things that look alike from the outside and are
completely different to act on:

* the page is broken or private (HTTP error, authentication) — nothing else matters;
* the page is deliberately kept out of search (``noindex``) — a decision, sometimes the
  right one, which is why an intentionally excluded URL is *not applicable* here;
* the site turns away crawlers. And that splits again: turning away a **search** crawler
  costs the site its place in AI answers, while turning away a **training** crawler is a
  business decision about one's own text. VEO records the second and never charges for it.
"""

from __future__ import annotations

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
)
from veo.geo.reporting import DIRECT, HIGH, MEDIUM, finding, observed, snippet_evidence
from veo.geo.robots import RobotsPolicy, parse_robots
from veo.geo.view import TargetView, build_view
from veo.scoring import CheckOutcome, CheckStatus

CHECK_IDS = frozenset(
    {
        "geo.access.http_status_ok",
        "geo.access.no_auth_required",
        "geo.access.indexable",
        "geo.access.search_bots_allowed",
        "geo.access.training_bot_policy_declared",
        "geo.access.not_blocked_by_edge",
        "geo.access.content_visible_without_js",
    }
)

#: Statuses that mean "an intermediary refused", as opposed to "the origin answered".
_REFUSAL_STATUSES = frozenset({403, 429})

#: Strings a CDN interstitial leaves in the body when it turns a crawler away.
_CHALLENGE_MARKERS = (
    "attention required",
    "cf-browser-verification",
    "checking your browser",
    "captcha",
    "you have been blocked",
    "access denied",
    "ddos protection",
)

_EDGE_HEADERS = ("cf-ray", "x-akamai-transformed", "x-sucuri-id", "x-iinfo")

#: Below this much visible text, a page has effectively said nothing without JavaScript.
_THIN_CONTENT_CHARACTERS = 200

_APP_SHELL_IDS = ("root", "app", "__next", "__nuxt", "main-app")


class AccessEligibilityCollector:
    """Observes reachability, indexability and crawler permission."""

    category_id = "access_eligibility"

    @property
    def check_ids(self) -> frozenset[str]:
        return CHECK_IDS

    def collect(self, context: CollectionContext) -> CollectionResult:
        view = build_view(context)
        evidence: list[EvidenceRecord] = list(view.evidence)
        outcomes: list[CheckOutcome] = []
        issues: list[IssueDraft] = []

        base_ids = view.evidence_ids

        # -- reachability ------------------------------------------------ #
        if view.document is None:
            for check_id in (
                "geo.access.http_status_ok",
                "geo.access.no_auth_required",
                "geo.access.not_blocked_by_edge",
                "geo.access.content_visible_without_js",
                "geo.access.indexable",
            ):
                outcomes.append(
                    observed(
                        check_id,
                        CheckStatus.UNKNOWN,
                        confidence_level=DIRECT,
                        note_ko="대상 URL의 응답을 수집하지 못했습니다.",
                    )
                )
        else:
            status = view.document.status
            if 200 <= status < 300:
                http_status = CheckStatus.PASS
                http_note = f"HTTP {status} 정상 응답입니다."
            elif 300 <= status < 400:
                http_status = CheckStatus.WARNING
                http_note = f"HTTP {status} 리다이렉트가 끝나지 않았습니다."
            else:
                http_status = CheckStatus.FAIL
                http_note = f"HTTP {status} 응답이라 AI 답변 엔진이 내용을 사용할 수 없습니다."
            outcomes.append(
                observed(
                    "geo.access.http_status_ok",
                    http_status,
                    confidence_level=DIRECT,
                    note_ko=http_note,
                    evidence_ids=base_ids,
                    observed_value={"status": status},
                )
            )
            if http_status is CheckStatus.FAIL:
                issues.append(
                    finding(
                        "geo.access.http_status_ok",
                        title_ko=f"대상 URL이 HTTP {status}를 반환합니다",
                        summary_ko=(
                            f"{view.url} 이 HTTP {status}로 응답합니다. 응답이 정상으로 "
                            "돌아오기 전에는 다른 개선이 노출로 이어지지 않습니다."
                        ),
                        remediation_ko="원본 서버 오류 또는 잘못된 라우팅을 먼저 해결하세요.",
                        remediation_owner="DEVELOPER",
                        urls=[view.url],
                        evidence_ids=base_ids,
                        business_impact_ko="AI 답변과 검색 결과 양쪽에서 페이지가 사라집니다.",
                        reverification_note_ko="복구 후 같은 URL을 재수집해 200 응답을 확인합니다.",
                    )
                )

            outcomes.append(self._auth_outcome(view, base_ids))
            if outcomes[-1].status is CheckStatus.FAIL:
                issues.append(
                    finding(
                        "geo.access.no_auth_required",
                        title_ko="인증이 있어야 볼 수 있는 페이지입니다",
                        summary_ko=(
                            "공개 크롤러가 로그인 없이 내용을 읽을 수 없습니다. 회원 전용 "
                            "페이지라면 정상이지만, 공개 콘텐츠라면 노출이 완전히 막힙니다."
                        ),
                        remediation_ko=(
                            "공개해야 할 내용이라면 인증 없이 접근 가능한 URL로 분리하세요."
                        ),
                        remediation_owner="DEVELOPER",
                        urls=[view.url],
                        evidence_ids=base_ids,
                    )
                )

            outcomes.append(self._edge_outcome(view, base_ids))
            outcomes.append(self._javascript_outcome(view, base_ids))
            outcomes.append(self._indexable_outcome(view, base_ids))

        # -- robots ------------------------------------------------------ #
        if context.robots_txt is None:
            reason = "robots.txt를 읽지 못해 크롤러 허용 여부를 확인할 수 없습니다."
            outcomes.append(
                observed(
                    "geo.access.search_bots_allowed",
                    CheckStatus.UNKNOWN,
                    confidence_level=DIRECT,
                    note_ko=reason,
                )
            )
            outcomes.append(
                observed(
                    "geo.access.training_bot_policy_declared",
                    CheckStatus.UNKNOWN,
                    confidence_level=DIRECT,
                    note_ko=reason,
                )
            )
        else:
            record = snippet_evidence(
                _robots_url(view.url),
                "robots_txt",
                context.robots_txt,
                excerpt=context.robots_txt[:400],
            )
            evidence.append(record)
            policy = parse_robots(context.robots_txt)
            search_outcome, search_issue = self._search_bots_outcome(
                policy, view.path, view.url, (record.evidence_id,)
            )
            outcomes.append(search_outcome)
            if search_issue is not None:
                issues.append(search_issue)
            outcomes.append(self._training_policy_outcome(policy, (record.evidence_id,)))

        return CollectionResult(
            outcomes=tuple(outcomes),
            evidence=tuple(evidence),
            issues=tuple(issues),
            notes_ko=(
                "학습용 크롤러 차단은 사업 판단이며 준비도 점수에 영향을 주지 않습니다.",
            ),
        )

    # ------------------------------------------------------------------ #
    # Individual checks
    # ------------------------------------------------------------------ #

    def _auth_outcome(self, view: TargetView, evidence_ids: tuple[str, ...]) -> CheckOutcome:
        challenge = view.header("www-authenticate")
        if view.status == 401 or challenge:
            return observed(
                "geo.access.no_auth_required",
                CheckStatus.FAIL,
                confidence_level=DIRECT,
                note_ko="인증을 요구하는 응답이라 공개 크롤러가 내용을 읽을 수 없습니다.",
                evidence_ids=evidence_ids,
                observed_value={
                    "status": view.status,
                    "authenticate_header": bool(challenge),
                },
            )
        if view.page.has_password_field and len(view.page.content_text) < _THIN_CONTENT_CHARACTERS:
            return observed(
                "geo.access.no_auth_required",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="로그인 폼만 있고 본문이 거의 없어 로그인 장벽으로 보입니다.",
                evidence_ids=evidence_ids,
            )
        return observed(
            "geo.access.no_auth_required",
            CheckStatus.PASS,
            confidence_level=DIRECT,
            note_ko="인증 없이 본문에 접근할 수 있습니다.",
            evidence_ids=evidence_ids,
        )

    def _edge_outcome(self, view: TargetView, evidence_ids: tuple[str, ...]) -> CheckOutcome:
        body = view.page.body_text.lower()
        markers = [marker for marker in _CHALLENGE_MARKERS if marker in body]
        edge_headers = [name for name in _EDGE_HEADERS if view.header(name)]
        if view.header("server").lower().startswith("cloudflare"):
            edge_headers.append("server")

        if view.status in _REFUSAL_STATUSES and (markers or edge_headers):
            return observed(
                "geo.access.not_blocked_by_edge",
                CheckStatus.FAIL,
                confidence_level=HIGH,
                note_ko="WAF/CDN이 정상 크롤러에게 차단 화면을 반환하고 있습니다.",
                evidence_ids=evidence_ids,
                observed_value={"status": view.status, "edge_headers": edge_headers},
            )
        if view.status in _REFUSAL_STATUSES:
            return observed(
                "geo.access.not_blocked_by_edge",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="접근이 거부됐지만 CDN 차단인지 원본 정책인지 구분되지 않습니다.",
                evidence_ids=evidence_ids,
            )
        return observed(
            "geo.access.not_blocked_by_edge",
            CheckStatus.PASS,
            confidence_level=HIGH,
            note_ko="차단 페이지 없이 원본 응답이 전달됐습니다.",
            evidence_ids=evidence_ids,
        )

    def _javascript_outcome(
        self, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        raw_length = len(view.page.content_text)
        rendered = view.context.rendered_dom.get(view.url)

        if rendered:
            from veo.geo.parsing import parse_html

            rendered_length = len(parse_html(rendered).content_text)
            share = raw_length / rendered_length if rendered_length else 1.0
            value = {"raw_characters": raw_length, "rendered_characters": rendered_length}
            if share < 0.5:
                return observed(
                    "geo.access.content_visible_without_js",
                    CheckStatus.FAIL,
                    confidence_level=HIGH,
                    note_ko="핵심 본문이 JavaScript 실행 뒤에만 나타납니다.",
                    evidence_ids=evidence_ids,
                    observed_value=value,
                )
            if share < 0.8:
                return observed(
                    "geo.access.content_visible_without_js",
                    CheckStatus.WARNING,
                    confidence_level=HIGH,
                    note_ko="본문 일부가 JavaScript 실행 뒤에만 나타납니다.",
                    evidence_ids=evidence_ids,
                    observed_value=value,
                )
            return observed(
                "geo.access.content_visible_without_js",
                CheckStatus.PASS,
                confidence_level=HIGH,
                note_ko="원본 HTML만으로 본문이 전달됩니다.",
                evidence_ids=evidence_ids,
                observed_value=value,
            )

        looks_like_a_shell = any(
            identifier in _APP_SHELL_IDS for identifier in view.page.element_ids
        )
        if raw_length < _THIN_CONTENT_CHARACTERS and looks_like_a_shell:
            return observed(
                "geo.access.content_visible_without_js",
                CheckStatus.FAIL,
                confidence_level=MEDIUM,
                note_ko="원본 HTML이 비어 있는 앱 셸이라 JS 없이는 본문이 없습니다.",
                evidence_ids=evidence_ids,
                observed_value={"raw_characters": raw_length},
            )
        if raw_length < _THIN_CONTENT_CHARACTERS:
            return observed(
                "geo.access.content_visible_without_js",
                CheckStatus.WARNING,
                confidence_level=MEDIUM,
                note_ko="원본 HTML의 본문이 매우 짧아 렌더링 의존 여부를 단정하기 어렵습니다.",
                evidence_ids=evidence_ids,
                observed_value={"raw_characters": raw_length},
            )
        return observed(
            "geo.access.content_visible_without_js",
            CheckStatus.PASS,
            confidence_level=MEDIUM,
            note_ko="원본 HTML만으로 충분한 본문이 확인됩니다.",
            evidence_ids=evidence_ids,
            observed_value={"raw_characters": raw_length},
        )

    def _indexable_outcome(
        self, view: TargetView, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        if view.context.url_importance.get(view.url) == "INTENTIONAL_NOINDEX":
            return observed(
                "geo.access.indexable",
                CheckStatus.NOT_APPLICABLE,
                confidence_level=DIRECT,
                note_ko="의도적으로 색인에서 제외한 URL이라 평가 대상이 아닙니다.",
                evidence_ids=evidence_ids,
            )

        declarations = [
            view.page.meta("robots"),
            view.page.meta("googlebot"),
            view.header("x-robots-tag"),
        ]
        blocking = [value for value in declarations if "noindex" in value.lower()]
        if blocking:
            return observed(
                "geo.access.indexable",
                CheckStatus.FAIL,
                confidence_level=DIRECT,
                note_ko="noindex가 선언되어 검색 적격성이 없습니다.",
                evidence_ids=evidence_ids,
                observed_value={"declarations": blocking},
            )
        return observed(
            "geo.access.indexable",
            CheckStatus.PASS,
            confidence_level=DIRECT,
            note_ko="색인을 막는 선언이 없습니다.",
            evidence_ids=evidence_ids,
        )

    def _search_bots_outcome(
        self, policy: RobotsPolicy, path: str, url: str, evidence_ids: tuple[str, ...]
    ) -> tuple[CheckOutcome, IssueDraft | None]:
        blocked = policy.blocked_search_agents(path)
        if not blocked:
            return (
                observed(
                    "geo.access.search_bots_allowed",
                    CheckStatus.PASS,
                    confidence_level=DIRECT,
                    note_ko="검색 목적 크롤러가 모두 허용되어 있습니다.",
                    evidence_ids=evidence_ids,
                ),
                None,
            )
        outcome = observed(
            "geo.access.search_bots_allowed",
            CheckStatus.FAIL,
            confidence_level=DIRECT,
            note_ko=f"검색 목적 크롤러 {len(blocked)}종이 robots.txt에서 차단되어 있습니다.",
            evidence_ids=evidence_ids,
            observed_value={"blocked_agents": list(blocked)},
        )
        issue = finding(
            "geo.access.search_bots_allowed",
            title_ko="검색 목적 AI 크롤러가 robots.txt에서 차단되어 있습니다",
            summary_ko=(
                "차단된 크롤러: " + ", ".join(blocked) + ". 학습용 크롤러 차단과 달리 "
                "검색 목적 크롤러 차단은 답변 노출 자체를 막습니다."
            ),
            remediation_ko=(
                "학습 차단은 유지하더라도 검색 목적 크롤러는 Allow로 되돌리세요."
            ),
            remediation_owner="DEVELOPER",
            urls=[_robots_url(url)],
            evidence_ids=evidence_ids,
            business_impact_ko="AI 답변에서 페이지가 근거로 사용될 수 없습니다.",
            fix_example="User-agent: OAI-SearchBot\nAllow: /",
            reverification_note_ko="robots.txt 재수집 후 차단 목록이 비는지 확인합니다.",
        )
        return outcome, issue

    def _training_policy_outcome(
        self, policy: RobotsPolicy, evidence_ids: tuple[str, ...]
    ) -> CheckOutcome:
        declared = policy.declared_training_agents()
        if declared:
            return observed(
                "geo.access.training_bot_policy_declared",
                CheckStatus.PASS,
                confidence_level=DIRECT,
                note_ko=(
                    "학습용 크롤러 정책이 명시되어 있습니다: " + ", ".join(declared) + ". "
                    "차단 여부는 사업 판단이며 감점 대상이 아닙니다."
                ),
                evidence_ids=evidence_ids,
                observed_value={"declared_agents": list(declared)},
            )
        return observed(
            "geo.access.training_bot_policy_declared",
            CheckStatus.WARNING,
            confidence_level=DIRECT,
            note_ko=(
                "학습용 크롤러에 대한 방침이 robots.txt에 없습니다. 정보 항목이므로 "
                "점수에는 영향이 없습니다."
            ),
            evidence_ids=evidence_ids,
        )


def _robots_url(url: str) -> str:
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


__all__ = ["CHECK_IDS", "AccessEligibilityCollector"]
