"""SEO 점수 알고리즘 v2 — 검색 파이프라인 단계별 고정 배점.

## 왜 새로 만드는가

현재(v1) 공식:

    예산   = Σ 심각도계수 (그 영역의 해당되는 검사 전부)
    감점_i = 심각도계수 × 상태배수 × 문제비율 × 신뢰도
    영역점수 = 100 × (1 − Σ감점 / 예산)

**분모가 검사 개수에 따라 늘어난다.** 실증:

    1.2.0 (온페이지 검사 9개, 예산 1.80): title 전면 실패 → 66.7점
    1.6.0 (온페이지 검사 11개, 예산 2.20): title 전면 실패 → 72.7점

같은 사이트, 같은 결함인데 **검사를 추가했더니 6점이 올랐다.** 이미 한 번 고친
결함("적게 수집하면 점수가 올라간다")의 거울상이다.

## v2 의 원칙

1. **배점의 합은 100 으로 고정.** 검사를 추가하려면 다른 검사에서 배점을 가져와야
   한다. 편집자의 명시적 결정이 되고, 변경 이력에 남는다.

2. **배점은 검색 파이프라인 단계에서 나온다.** 검색엔진은 순서대로 동작한다 —
   발견 → 크롤 → 색인 → 해석 → 경쟁 → 클릭. **앞 단계가 막히면 뒤 단계는 무의미하다.**
   noindex 페이지에 완벽한 구조화 데이터를 넣어도 아무 일도 일어나지 않는다.
   이건 의견이 아니라 동작 방식이고, 그래서 객관적 배점 근거가 된다.

3. **심각도 4단계를 배점으로 대체한다.** CRITICAL 이 8개인데 전부 같은 무게일 이유가
   없다. title 과 canonical 은 다른 것을 망가뜨린다.

4. **해당 없음은 같은 단계 안에서 재분배한다.** 그래야 합이 항상 100 이고, 고객마다
   분모가 달라지지 않는다(0-B 절대 평가).

5. **못 잰 것은 점수를 얻지 못한다.** 배점은 분모에 남는다(ADR 0016). 다만 실패로
   보고하지 않는다 — 사이트 결함이 아니라 우리가 못 잰 것이다(0-J).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# 단계 정의 — 배점의 근거
# --------------------------------------------------------------------------- #

STAGES: dict[str, dict] = {
    "S1_BLOCKED": {
        "points": 0,   # 배점이 아니라 **곱셈 게이트**. 아래 GATE_STAGE 참조
        "is_gate": True,
        "name_ko": "색인 차단",
        "why_ko": (
            "실패하면 페이지가 검색 결과에 **존재하지 않는다.** 이후 모든 항목이 "
            "무의미해지므로 다른 어떤 것으로도 보상할 수 없다. 그래서 최대 배점이다."
        ),
    },
    "S2_IDENTITY": {
        "points": 21.4,
        "name_ko": "대표 URL 혼란",
        "why_ko": (
            "색인은 되지만 **어느 주소가 대표인지 엔진이 임의로 고른다.** 트래픽이 "
            "엉뚱한 주소로 가거나 여러 주소로 쪼개져 어느 쪽도 순위를 못 얻는다."
        ),
    },
    "S3_MEANING": {
        "points": 28.6,
        "name_ko": "해석 불가",
        "why_ko": (
            "색인은 되지만 **무엇에 대한 페이지인지 엔진이 모른다.** 검색어와 연결되지 "
            "않으므로 노출 자체가 일어나지 않는다. 차단 다음으로 큰 손실이다."
        ),
    },
    "S4_COMPETE": {
        "points": 28.6,
        "name_ko": "경쟁력",
        "why_ko": (
            "노출은 되지만 **더 나은 페이지에 밀린다.** 즉시 손실은 아니지만 장기적으로 "
            "트래픽 차이가 가장 크게 벌어지는 구간이다."
        ),
    },
    "S5_CLICK": {
        "points": 14.3,
        "name_ko": "클릭·표현",
        "why_ko": (
            "순위는 나오지만 **덜 눌린다.** 검색 결과에 보이는 문구와 리치 결과가 "
            "여기서 결정된다. 순위를 올리는 것보다 싸게 트래픽을 늘리는 구간이다."
        ),
    },
    "S6_HYGIENE": {
        "points": 7.1,
        "name_ko": "위생",
        "why_ko": (
            "검색 성과에 직접 영향이 확인되지 않은 항목. 고쳐서 나쁠 것은 없지만 "
            "**이것 때문에 순위가 바뀌지는 않는다.** 그래서 배점이 작다."
        ),
    },
}

# --------------------------------------------------------------------------- #
# 검사별 배점 — 단계 안에서 다시 나눈다
#
# 나누는 기준 셋:
#   범위   SITE 전역 실패가 URL 단위 실패보다 크다
#   대체   다른 신호로 보완되는가 (title 은 대체 불가, alt 는 문맥으로 보완)
#   확실성 구글이 문서로 명시한 요건인가, 업계 통설인가
# --------------------------------------------------------------------------- #

ALLOCATION: dict[str, tuple[str, float, str]] = {
    # ---- S1 색인 차단 (30) ----
    "seo.http.status_ok": ("S1_BLOCKED", 10, "5xx/4xx 는 색인에서 제거된다. 사이트 전역"),
    "seo.robots.txt_allows_url": ("S1_BLOCKED", 8, "크롤 자체가 막힌다. 사이트 전역"),
    "seo.robots.meta_indexable": ("S1_BLOCKED", 8, "크롤은 되나 색인에서 빠진다"),
    "seo.content.js_render_parity": ("S1_BLOCKED", 4, "렌더링 후에만 내용이 있으면 빈 페이지로 색인"),
    # ---- S2 대표 URL (15) ----
    "seo.canonical.declared_and_consistent": ("S2_IDENTITY", 6, "대표 주소를 엔진이 임의 선택"),
    "seo.canonical.not_cross_domain": ("S2_IDENTITY", 5, "자사 페이지가 남의 도메인으로 귀속"),
    "seo.onpage.no_duplicate_metadata": ("S2_IDENTITY", 2, "같은 제목이면 중복으로 묶일 위험"),
    "seo.content.no_duplicate_bodies": ("S2_IDENTITY", 2, "본문 중복은 대표 선택을 흔든다"),
    # ---- S3 해석 (20) ----
    "seo.onpage.title_present_and_unique": ("S3_MEANING", 6, "주제를 알리는 1순위 신호. 대체 불가"),
    "seo.content.no_thin_signal": ("S3_MEANING", 4, "내용이 없으면 어떤 검색어와도 안 맞는다"),
    "seo.onpage.single_meaningful_h1": ("S3_MEANING", 3, "본문 주제 신호. title 을 보완"),
    "seo.onpage.single_title_element": ("S3_MEANING", 2, "둘이면 엔진이 어느 것을 쓸지 모른다"),
    "seo.sd.matches_visible_content": ("S3_MEANING", 2, "불일치는 구조화 데이터 무시 또는 수동 조치"),
    "seo.onpage.heading_hierarchy": ("S3_MEANING", 1, "문서 구조 이해를 돕는다"),
    "seo.onpage.html_lang_declared": ("S3_MEANING", 1, "언어 판별. 한국어는 대개 자동 인식"),
    "seo.onpage.image_alt_coverage": ("S3_MEANING", 1, "이미지 의미. 문맥으로 일부 보완됨"),
    # ---- S4 경쟁력 (20) ----
    "seo.ux.mobile_viewport": ("S4_COMPETE", 4, "모바일 우선 색인. 국내 병원 검색은 모바일 중심"),
    "seo.security.https_valid": ("S4_COMPETE", 4, "구글이 명시한 순위 요인이자 신뢰 신호"),
    "seo.perf.lcp_lab": ("S4_COMPETE", 3, "Core Web Vitals. 동점일 때 갈린다"),
    "seo.perf.inp_field": ("S4_COMPETE", 2, "실사용자 반응성. 필드 데이터"),
    "seo.crawl.no_orphan_key_pages": ("S4_COMPETE", 2, "내부 링크가 없으면 중요도가 전달 안 됨"),
    "seo.security.certificate_not_expiring": ("S4_COMPETE", 1, "만료 시 사이트 전체 차단. 예방 항목"),
    "seo.content.lazy_loading_safe": ("S4_COMPETE", 1, "잘못 걸면 콘텐츠가 숨는다"),
    "seo.security.no_mixed_content": ("S4_COMPETE", 1, "브라우저 경고로 이탈"),
    "seo.content.internal_link_density": ("S4_COMPETE", 1, "주제 연결 강화"),
    "seo.content.click_depth_reasonable": ("S4_COMPETE", 1, "깊으면 크롤 우선순위가 낮아진다"),
    # ---- S5 클릭·표현 (10) ----
    "seo.onpage.meta_description_quality": ("S5_CLICK", 2, "검색결과에 그대로 노출되는 문구"),
    "seo.sd.naver_supported_type": ("S5_CLICK", 2, "네이버·카카오 공유 미리보기. 국내 병원 핵심 채널"),
    "seo.sd.declared": ("S5_CLICK", 2, "리치 결과의 전제"),
    "seo.sd.required_properties_present": ("S5_CLICK", 1, "속성이 빠지면 리치 결과 미출력"),
    "seo.sd.jsonld_parses": ("S5_CLICK", 1, "문법 오류면 통째로 무시"),
    "seo.sd.google_supported_type": ("S5_CLICK", 1, "지원 타입이라야 리치 결과"),
    "seo.sitemap.discoverable": ("S5_CLICK", 1, "신규·변경 페이지 발견 속도"),
    # ---- S6 위생 (5) ----
    "seo.sitemap.urls_valid": ("S6_HYGIENE", 0.75, "잘못된 URL 은 무시될 뿐"),
    "seo.http.redirect_chain_sane": ("S6_HYGIENE", 0.75, "길면 크롤 예산 낭비"),
    "seo.crawl.no_broken_internal_links": ("S6_HYGIENE", 0.5, "사용자 경험. 색인 영향은 작다"),
    "seo.perf.cls_lab": ("S6_HYGIENE", 0.5, "레이아웃 흔들림"),
    "seo.perf.tbt_lab": ("S6_HYGIENE", 0.5, "실험실 지표. INP 가 대표값"),
    "seo.perf.text_compression": ("S6_HYGIENE", 0.5, "전송량"),
    "seo.onpage.descriptive_anchor_text": ("S6_HYGIENE", 0.4, "링크 맥락"),
    "seo.content.breadcrumb_present": ("S6_HYGIENE", 0.25, "계층 표시"),
    "seo.content.pagination_signals": ("S6_HYGIENE", 0.25, "목록 페이지"),
    "seo.perf.modern_image_format": ("S6_HYGIENE", 0.15, "전송량"),
    "seo.perf.resource_hints": ("S6_HYGIENE", 0.15, "로딩 힌트"),
    "seo.robots.txt_parses_cleanly": ("S6_HYGIENE", 0.15, "의도 전달"),
    "seo.crawl.favicon_declared_and_crawlable": ("S6_HYGIENE", 0.1, "검색결과 아이콘"),
    "seo.html.doctype_standards_mode": ("S6_HYGIENE", 0.05, "렌더링 모드"),
}

STATUS_MULTIPLIER = {"FAIL": 1.0, "WARNING": 0.5, "PASS": 0.0, "UNKNOWN": 1.0}

#: 결함은 대개 템플릿 단위로 생긴다. 40% 가 깨졌다면 40개의 개별 실수가 아니라
#: 템플릿 하나의 문제이고, 나머지 60% 도 같은 위험에 있다. 선형 비율은 이 구조를
#: 반영하지 못한다. 0.7 승은 40% → 53% 로 올려 그 사실을 반영한다.
BREADTH_EXPONENT = 0.7


@dataclass
class CheckInput:
    check_id: str
    status: str
    coverage_ratio: float = 1.0
    confidence: float = 1.0


@dataclass
class Loss:
    check_id: str
    stage: str
    points: float
    status: str
    breadth: float
    lost: float
    why: str


@dataclass
class Result:
    score: float
    losses: list[Loss] = field(default_factory=list)
    stage_scores: dict[str, tuple[float, float]] = field(default_factory=dict)
    unmeasured: list[str] = field(default_factory=list)


def score(inputs: list[CheckInput], *, breadth_exponent: float = BREADTH_EXPONENT) -> Result:
    """점수 = **색인 도달률 × 품질점수**.

    ## 왜 곱셈인가

    덧셈만 쓰면 색인이 완전히 차단된 사이트가 74점을 받는다(실측). 검색에 존재하지
    않는 사이트가 "양호" 등급을 받는 것이다. 검사 배점만큼만 잃기 때문이다.

    실제로는 **앞 단계가 막히면 뒤 단계가 통째로 무의미하다.** noindex 페이지의
    완벽한 구조화 데이터는 아무 일도 하지 않는다. 그래서 색인 차단은 배점이 아니라
    **곱셈 게이트**다.

        도달률 = Π (1 − 차단검사 실패비율)      검색에 들어갈 수 있는 비율
        품질   = 100 − Σ (배점 × 상태 × 범위 × 신뢰도)
        점수   = 도달률 × 품질

    게이트끼리도 곱한다. 페이지는 **모든** 관문을 통과해야 하기 때문이다 —
    robots 가 절반을 막고 상태코드가 20% 실패면 (1−0.5)(1−0.2) = 0.4 다.

    ## 못 잰 항목의 처리가 게이트와 품질에서 다르다

    **게이트**: 곱하지 않는다(×1). 관측하지 않은 차단을 있다고 하면 **없는 결함을
    지어내는 것**이다(0-A). 대신 '색인 가능 여부 확인 불가' 로 표시한다.

    **품질**: 배점을 잃는다(ADR 0016). 재지 못한 항목이 분모에서 빠지면 "4개 중
    1개만 보고 100점" 이 된다.
    """
    by_id = {item.check_id: item for item in inputs}

    stage_members: dict[str, list[str]] = {}
    for check_id, (stage, _, _) in ALLOCATION.items():
        stage_members.setdefault(stage, []).append(check_id)

    losses: list[Loss] = []
    stage_scores: dict[str, tuple[float, float]] = {}
    unmeasured: list[str] = []
    gate_unverified: list[str] = []
    reach = 1.0
    quality = 0.0

    for stage, members in stage_members.items():
        is_gate = STAGES[stage].get("is_gate", False)
        live = [c for c in members if by_id.get(c) and by_id[c].status != "NOT_APPLICABLE"]

        if is_gate:
            blocked_total = 0.0
            for check_id in live:
                item = by_id[check_id]
                if item.status == "UNKNOWN":
                    gate_unverified.append(check_id)
                    continue
                share = STATUS_MULTIPLIER.get(item.status, 1.0) * min(1.0, item.coverage_ratio)
                if share > 0:
                    reach *= 1.0 - share
                    blocked_total += share
                    losses.append(
                        Loss(check_id, stage, 0.0, item.status, round(share, 3),
                             round(share, 3), ALLOCATION[check_id][2])
                    )
            stage_scores[stage] = (round(reach * 100, 2), 100.0)
            continue

        budget = STAGES[stage]["points"]
        if not live:
            stage_scores[stage] = (0.0, 0.0)
            continue
        declared = sum(ALLOCATION[c][1] for c in live)
        scale = budget / declared

        stage_lost = 0.0
        for check_id in live:
            item = by_id[check_id]
            points = ALLOCATION[check_id][1] * scale
            multiplier = STATUS_MULTIPLIER.get(item.status, 1.0)
            if item.status == "UNKNOWN":
                lost = points
                breadth = 1.0
                unmeasured.append(check_id)
            else:
                breadth = min(1.0, item.coverage_ratio) ** breadth_exponent
                lost = points * multiplier * breadth * item.confidence
            if lost > 0:
                losses.append(
                    Loss(check_id, stage, round(points, 3), item.status,
                         round(breadth, 3), round(lost, 3), ALLOCATION[check_id][2])
                )
            stage_lost += lost

        stage_scores[stage] = (round(budget - stage_lost, 2), budget)
        quality += budget - stage_lost

    losses.sort(key=lambda x: -x.lost)
    result = Result(round(reach * quality, 2), losses, stage_scores, unmeasured)
    result.gate_unverified = gate_unverified  # type: ignore[attr-defined]
    result.reach = round(reach, 4)  # type: ignore[attr-defined]
    result.quality = round(quality, 2)  # type: ignore[attr-defined]
    return result


def allocation_report() -> str:
    lines = ["단계          배점   검사수  합계검증"]
    grand = 0.0
    for stage, meta in STAGES.items():
        members = [(c, p) for c, (s, p, _) in ALLOCATION.items() if s == stage]
        total = sum(p for _, p in members)
        grand += meta["points"]
        ok = "OK" if abs(total - meta["points"]) < 1e-6 else f"불일치 {total}"
        lines.append(f"{meta['name_ko']:12} {meta['points']:>5}   {len(members):>3}    {ok}")
    lines.append(f"{'합계':12} {grand:>5}   {len(ALLOCATION):>3}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(allocation_report())
