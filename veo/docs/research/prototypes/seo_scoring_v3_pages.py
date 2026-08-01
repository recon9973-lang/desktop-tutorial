"""SEO 점수 알고리즘 v3 — 2단계 측정: 사이트 점수 아래에 페이지 점수를 단다.

## 왜 새 판이 필요한가

제품 구조가 확정됐다(2026-08-01, 사용자 결정):

    상위 탭  = 사이트 점수   전체 크롤 · 59개 검사 · 1.8.0 산식 그대로
    하위     = 페이지 점수   그 페이지의 URL 범위 검사만 재집계

사이트 점수가 페이지 점수들보다 낮을 수 있고, **그 차이의 이유를 화면이 스스로
설명해야 한다.** "페이지는 다 100점인데 사이트는 78점" 이라는 화면이 설명 없이
나가면 고장으로 읽힌다(0-J). 설명하려면 산식이 먼저 답을 갖고 있어야 한다.

v3 이 더하는 것은 넷이고, **사이트 점수 산식 자체는 한 글자도 바꾸지 않는다**
(같은 입력이면 v2 프로토타입과 같은 점수 — 시험으로 고정).

1. **분해(decompose).** overall_before_caps = 100 − Σ(URL손실) − Σ(SITE손실) 이
   항등식이 되도록 손실을 검사 단위로 귀속한다. 도달률(reach)은 뺄셈 항이 아니라
   **곱셈**이고, 상한(cap)은 **절단**이다 — 둘 다 손실 목록에 넣지 않고 따로 적는다.
2. **페이지 점수.** 그 페이지에서 판정된 URL 범위 검사만으로, 같은 단계 구조와
   고정분모를 페이지 단위로 재정규화해 계산한다.
3. **부재 주장 규칙.** "중복이 없다 · 고아가 없다 · 깨진 링크가 없다" 는 표본으로
   증명되지 않는다. 표본이 전체가 아니면 PASS 대신 UNKNOWN 이다.
4. **재측정.** 페이지 하나만 다시 재면 URL 판정만 갱신되고, SITE 판정은 이전
   전체 진단의 값에 날짜를 달아 유지한다.

## 발견된 결함 — 이 판이 고치는 것

잘린 크롤(100장 상한)에서 부재형 SITE 검사(no_duplicate_*, no_orphan,
no_broken_links)가 PASS 를 단정하고 있었다. **표본으로 존재는 증명되지만 부재는
증명되지 않는다**(0-A). `collect/sample.py` 의 `is_whole_site` 규칙은 옳지만,
수집기가 그 질문을 1장 크롤 경로에서만 묻는다 — 100장 잘린 크롤은 그냥 통과한다.

## 세 가지 '안 잰 것' — 이 판의 핵심 구분

| 상태 | 분모 | 뜻 | 근거 |
|---|---|---|---|
| `NOT_APPLICABLE` | 뺀다 | 이 페이지에 그 항목이 없다 | ADR 0002 |
| `UNKNOWN` | 남긴다, 0점 | 재려 했으나 실패했다 | ADR 0016 |
| `NOT_SAMPLED` (신설) | 뺀다, 별도 표기 | **명세의 표본 정책이 안 재기로 했다** | 0-J |

NOT_SAMPLED 를 UNKNOWN 처럼 분모에 남기면, 성능 표본(상위 5장) 밖의 모든
페이지가 우리 정책 때문에 8.3점어치를 잃는다 — **우리가 안 잰 것을 고객 페이지의
감점으로 돌리는 것**이다(0-J). N/A 처럼 조용히 빼면 "표본 밖" 이라는 사실이
사라진다. 그래서 셋째 상태다: 분모에서 빼되 "표본 밖 — 요청 시 측정" 으로 적는다.

덜 재서 점수를 올리는 유인은 생기지 않는다 — 표본 선정이 명세에 고정돼 있기
때문이다(`sampling.perf_lab`, 중요도 상위 5장). 누가 표본에 들어가는지를 재는
쪽이 고를 수 없으므로 조작할 자리가 없다.

**반론(기록해 둔다).** 절대평가의 원칙은 "못 잰 것은 분모에 남는다"(ADR 0016)이고
NOT_SAMPLED 는 그 예외다. 예외가 늘면 원칙이 죽는다. 그래서 NOT_SAMPLED 는
명세가 표본 정책을 선언한 검사(성능 lab + 실사용자 field)에서만 허용하고, 다른
검사에 쓰면 **오류로 거부한다** — 예외의 경계를 코드가 지킨다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# 명세 축약본 — 1.8.0 의 실제 단계·배점·범위
#
# 숫자는 packages/scoring-specs/specs/veo.seo.readiness/1.8.0.yaml 에서 그대로
# 옮겼다. v2 프로토타입의 ALLOCATION 과 한 숫자도 다르면 안 되고, 시험이 그것을
# v2 파일과 대조해 강제한다. v3 이 더한 정보는 scope(URL|SITE) 하나뿐이다.
#
# 배점 하나하나의 구글 근거(Lighthouse 실측 배점·Search Central 문서·CWV 임계값)와
# "구글 근거 없음 — VEO 판단" 인 항목의 구분은 docs/research/SEO_SCORING_V3_PAGES.md
# §5 배점 근거 대조표에 있다. 근거 없이 숫자를 더하거나 옮기지 마라.
#
# 점수 밖 세 영역(search_engine_integration·observability_outcomes·offpage_entity,
# 검사 10개)은 싣지 않는다 — contributes_to_score: false 라 산식에 나타나지 않는다.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class StageDef:
    """단계 하나. points 는 100점 환산 가중치, raw_budget 은 배점표의 눈금."""

    points: float
    raw_budget: float
    name_ko: str
    is_gate: bool = False


@dataclass(frozen=True)
class CheckDef:
    """검사 하나. scope 가 v3 의 축이다 — URL 은 페이지에서 재집계할 수 있고,
    SITE 는 여러 장을 봐야 하므로 페이지 점수에 절대 들어가지 않는다."""

    stage: str
    points: float
    scope: str  # "URL" | "SITE"
    why: str


@dataclass(frozen=True)
class Spec:
    """명세 한 판. 시험이 배점 재분할(검사 추가) 시나리오를 만들 수 있도록
    함수들이 이것을 인자로 받는다 — 기본값은 1.8.0 축약본."""

    stages: dict[str, StageDef]
    checks: dict[str, CheckDef]

    def stage_members(self, stage: str) -> list[str]:
        return [c for c, d in self.checks.items() if d.stage == stage]

    def url_stage_budget(self, stage: str) -> float:
        """페이지 점수의 단계 고정분모 — 그 단계 URL 범위 검사의 배점 합.

        명세가 정해지면 상수다. 검사를 추가할 때 같은 범위(scope) 안에서 배점을
        재분할하면 이 값이 변하지 않고, 그래서 무관한 페이지의 점수가 흔들리지
        않는다(시험으로 고정). URL 검사가 SITE 검사에서 배점을 가져오면 이 값이
        변한다 — 그것은 페이지 점수의 눈금을 바꾸는 결정이므로 눈에 띄어야 한다.
        """
        return sum(d.points for d in self.checks.values() if d.stage == stage and d.scope == "URL")


_STAGES: dict[str, StageDef] = {
    "S1_BLOCKED": StageDef(0.0, 30.0, "색인 차단", is_gate=True),
    "S2_IDENTITY": StageDef(21.4, 15.0, "대표 URL 혼란"),
    "S3_MEANING": StageDef(28.6, 20.0, "해석 불가"),
    "S4_COMPETE": StageDef(28.6, 20.0, "경쟁력"),
    "S5_CLICK": StageDef(14.3, 10.0, "클릭·표현"),
    "S6_HYGIENE": StageDef(7.1, 5.0, "위생"),
}

_CHECKS: dict[str, CheckDef] = {
    # ---- S1 색인 차단 (30, 관문, 전부 URL — 페이지마다 판정된다) ----
    "seo.http.status_ok": CheckDef("S1_BLOCKED", 10, "URL", "5xx/4xx 는 색인에서 제거된다"),
    "seo.robots.txt_allows_url": CheckDef("S1_BLOCKED", 8, "URL", "크롤 자체가 막힌다"),
    "seo.robots.meta_indexable": CheckDef("S1_BLOCKED", 8, "URL", "크롤은 되나 색인에서 빠진다"),
    "seo.content.js_render_parity": CheckDef("S1_BLOCKED", 4, "URL", "렌더링 후에만 내용이 있으면 빈 페이지로 색인"),
    # ---- S2 대표 URL (15 = URL 11 + SITE 4) ----
    "seo.canonical.declared_and_consistent": CheckDef("S2_IDENTITY", 6, "URL", "대표 주소를 엔진이 임의 선택"),
    "seo.canonical.not_cross_domain": CheckDef("S2_IDENTITY", 5, "URL", "자사 페이지가 남의 도메인으로 귀속"),
    "seo.onpage.no_duplicate_metadata": CheckDef("S2_IDENTITY", 2, "SITE", "같은 제목이면 중복으로 묶일 위험"),
    "seo.content.no_duplicate_bodies": CheckDef("S2_IDENTITY", 2, "SITE", "본문 중복은 대표 선택을 흔든다"),
    # ---- S3 해석 (20 = URL 16 + SITE 4) ----
    "seo.onpage.title_present_and_unique": CheckDef("S3_MEANING", 6, "URL", "주제를 알리는 1순위 신호. 대체 불가"),
    "seo.content.no_thin_signal": CheckDef("S3_MEANING", 4, "SITE", "내용이 없으면 어떤 검색어와도 안 맞는다"),
    "seo.onpage.single_meaningful_h1": CheckDef("S3_MEANING", 3, "URL", "본문 주제 신호. title 을 보완"),
    "seo.onpage.single_title_element": CheckDef("S3_MEANING", 2, "URL", "둘이면 엔진이 어느 것을 쓸지 모른다"),
    "seo.sd.matches_visible_content": CheckDef("S3_MEANING", 2, "URL", "불일치는 구조화 데이터 무시 또는 수동 조치"),
    "seo.onpage.heading_hierarchy": CheckDef("S3_MEANING", 1, "URL", "문서 구조 이해를 돕는다"),
    "seo.onpage.html_lang_declared": CheckDef("S3_MEANING", 1, "URL", "언어 판별. 한국어는 대개 자동 인식"),
    "seo.onpage.image_alt_coverage": CheckDef("S3_MEANING", 1, "URL", "이미지 의미. 문맥으로 일부 보완됨"),
    # ---- S4 경쟁력 (20 = URL 13.5 + SITE 6.5) ----
    "seo.ux.mobile_viewport": CheckDef("S4_COMPETE", 3.5, "URL", "모바일 우선 색인"),
    "seo.security.https_valid": CheckDef("S4_COMPETE", 3, "SITE", "구글이 명시한 순위 요인. 다만 지금은 보편"),
    "seo.perf.lcp_lab": CheckDef("S4_COMPETE", 3, "URL", "Core Web Vitals. 동점일 때 갈린다"),
    "seo.perf.inp_field": CheckDef("S4_COMPETE", 2, "URL", "실사용자 반응성. 필드 데이터"),
    "seo.perf.cls_lab": CheckDef("S4_COMPETE", 2, "URL", "Core Web Vitals 본체"),
    "seo.crawl.no_orphan_key_pages": CheckDef("S4_COMPETE", 1.75, "SITE", "내부 링크가 없으면 중요도가 전달 안 됨"),
    "seo.crawl.crawlable_anchors": CheckDef("S4_COMPETE", 1.5, "URL", "JS 전용 메뉴는 크롤러가 못 따라간다"),
    "seo.security.certificate_not_expiring": CheckDef("S4_COMPETE", 0.75, "SITE", "만료 시 사이트 전체 차단"),
    "seo.content.lazy_loading_safe": CheckDef("S4_COMPETE", 0.75, "URL", "잘못 걸면 콘텐츠가 숨는다"),
    "seo.security.no_mixed_content": CheckDef("S4_COMPETE", 0.75, "URL", "브라우저 경고로 이탈"),
    "seo.content.internal_link_density": CheckDef("S4_COMPETE", 0.5, "SITE", "주제 연결 강화. 업계 통설"),
    "seo.content.click_depth_reasonable": CheckDef("S4_COMPETE", 0.5, "SITE", "크롤 우선순위 휴리스틱"),
    # ---- S5 클릭·표현 (10 = URL 7 + SITE 3) ----
    "seo.onpage.meta_description_quality": CheckDef("S5_CLICK", 2, "URL", "검색결과에 그대로 노출되는 문구"),
    "seo.sd.naver_supported_type": CheckDef("S5_CLICK", 2, "URL", "네이버·카카오 공유 미리보기"),
    "seo.sd.declared": CheckDef("S5_CLICK", 2, "SITE", "리치 결과의 전제"),
    "seo.sd.required_properties_present": CheckDef("S5_CLICK", 1, "URL", "속성이 빠지면 리치 결과 미출력"),
    "seo.sd.jsonld_parses": CheckDef("S5_CLICK", 1, "URL", "문법 오류면 통째로 무시"),
    "seo.sd.google_supported_type": CheckDef("S5_CLICK", 1, "URL", "지원 타입이라야 리치 결과"),
    "seo.sitemap.discoverable": CheckDef("S5_CLICK", 1, "SITE", "신규·변경 페이지 발견 속도"),
    # ---- S6 위생 (5 = URL 2.4 + SITE 2.6) ----
    "seo.sitemap.urls_valid": CheckDef("S6_HYGIENE", 0.75, "SITE", "잘못된 URL 은 무시될 뿐"),
    "seo.http.redirect_chain_sane": CheckDef("S6_HYGIENE", 0.75, "URL", "길면 크롤 예산 낭비"),
    "seo.crawl.no_broken_internal_links": CheckDef("S6_HYGIENE", 0.6, "SITE", "사용자 경험. 색인 영향은 작다"),
    "seo.perf.tbt_lab": CheckDef("S6_HYGIENE", 0.5, "URL", "실험실 지표. INP 가 대표값"),
    "seo.perf.text_compression": CheckDef("S6_HYGIENE", 0.5, "URL", "전송량. LCP 의 원인이라 최소 배점"),
    "seo.onpage.descriptive_anchor_text": CheckDef("S6_HYGIENE", 0.5, "SITE", "링크 맥락"),
    "seo.content.breadcrumb_present": CheckDef("S6_HYGIENE", 0.25, "SITE", "계층 표시"),
    "seo.content.pagination_signals": CheckDef("S6_HYGIENE", 0.25, "SITE", "목록 페이지"),
    "seo.html.charset_declared": CheckDef("S6_HYGIENE", 0.3, "URL", "인코딩 추측 실패 시 본문 전체가 깨져 색인"),
    "seo.perf.modern_image_format": CheckDef("S6_HYGIENE", 0.15, "URL", "전송량. LCP 의 원인이라 최소 배점"),
    "seo.perf.resource_hints": CheckDef("S6_HYGIENE", 0.15, "URL", "로딩 힌트. LCP 의 원인이라 최소 배점"),
    "seo.robots.txt_parses_cleanly": CheckDef("S6_HYGIENE", 0.15, "SITE", "의도 전달"),
    "seo.crawl.favicon_declared_and_crawlable": CheckDef("S6_HYGIENE", 0.1, "SITE", "검색결과 아이콘"),
    "seo.html.doctype_standards_mode": CheckDef("S6_HYGIENE", 0.05, "URL", "렌더링 모드"),
}

SPEC_1_8_0 = Spec(stages=_STAGES, checks=_CHECKS)

#: 실험실 성능 — 상위 5장만 실측한다(sampling.perf_lab). 그 밖 페이지에서는
#: NOT_SAMPLED. 여섯 검사 배점 합 6.3.
PERF_LAB_CHECKS = frozenset({
    "seo.perf.lcp_lab",
    "seo.perf.cls_lab",
    "seo.perf.tbt_lab",
    "seo.perf.text_compression",
    "seo.perf.modern_image_format",
    "seo.perf.resource_hints",
})

#: 실사용자 성능 — 구글이 모아 둔 origin(사이트 전체) 값이다. 사이트 점수에서만
#: 쓰고 페이지에는 붙이지 않는다(범위 혼합 금지, methodology §3.1). 페이지에서는
#: 항상 NOT_SAMPLED. 배점 2. 6.3 + 2 = 8.3 — "상위 5장 × 성능 8.3점" 의 실체다.
PERF_FIELD_CHECKS = frozenset({"seo.perf.inp_field"})

#: NOT_SAMPLED 를 허용하는 유일한 집합. 다른 검사에 쓰면 오류다 — 예외의 경계를
#: 코드가 지키지 않으면 "안 재기로 했다" 가 아무 데나 붙어 절대평가가 죽는다.
NOT_SAMPLED_ALLOWED = PERF_LAB_CHECKS | PERF_FIELD_CHECKS

#: 부재형 검사 — "~이 없다" 를 주장하는 검사. 존재는 표본으로 증명되지만
#: 부재는 전체를 봐야만 증명된다. 이 목록이 absence_claim 의 적용 대상이다.
ABSENCE_CHECKS = frozenset({
    "seo.onpage.no_duplicate_metadata",
    "seo.content.no_duplicate_bodies",
    "seo.crawl.no_orphan_key_pages",
    "seo.crawl.no_broken_internal_links",
})

STATUS_MULTIPLIER = {"FAIL": 1.0, "WARNING": 0.5, "PASS": 0.0, "UNKNOWN": 1.0}

#: v2 와 동일. 결함은 대개 템플릿 단위로 생기므로 40% → 53% 로 올린다.
BREADTH_EXPONENT = 0.7

NOT_SAMPLED_NOTE_KO = (
    "표본 밖 — 요청 시 측정합니다. 명세의 표본 정책(중요도 상위 페이지)이 재지 "
    "않기로 한 것이므로, 이 페이지의 결함도 감점도 아닙니다."
)


@dataclass
class CheckInput:
    """판정 하나. 사이트에서는 coverage_ratio 가 '크롤한 페이지 중 결함 비율',
    페이지에서는 '그 페이지 안에서의 비율'(예: 이미지 alt 누락 비율)이다."""

    check_id: str
    status: str
    coverage_ratio: float = 1.0
    confidence: float = 1.0


@dataclass
class AttributedLoss:
    """손실 한 건 — 어느 검사가, 어느 범위(URL|SITE)에서, 몇 점을 가져갔나.

    kind 두 가지:
      CHECK                 검사의 실패·경고·측정불가가 만든 손실
      STAGE_NOT_APPLICABLE  단계 전체가 해당 없음이라 v2 산식이 그 단계 가중치를
                            통째로 잃는 경우. 구성 검사에 배점 비례로 귀속해
                            항등식을 지킨다 (실무에서는 드문 모서리다)
    """

    check_id: str
    stage: str
    scope: str
    status: str
    lost: float
    kind: str
    why: str


@dataclass
class GateEvent:
    """관문에서 곱해진 몫. **손실(뺄셈)이 아니다** — 화면에는 '차단으로 도달률
    X% 소실' 처럼 곱셈으로 그려야 한다. 뺄셈 목록에 섞으면 항등식이 깨진다."""

    check_id: str
    blocked_share: float


@dataclass
class SiteResult:
    """사이트 점수 + 분해. score 는 v2 와 동일한 수(같은 입력이면 같은 점수).

    항등식:  quality == 100 − Σ(losses[].lost)          (오차 1e-9)
    곱셈:    score  == round(reach × quality, 2)
    절단:    상한(cap)은 이 프로토타입 범위 밖 — 실코드에서는 이 뒤에 min() 으로
             걸리고, 분해에는 '절단' 으로만 표기한다(뺄셈 항 아님).
    """

    score: float
    reach: float
    quality: float
    losses: list[AttributedLoss] = field(default_factory=list)
    gate_events: list[GateEvent] = field(default_factory=list)
    gate_unverified: list[str] = field(default_factory=list)
    stage_scores: dict[str, tuple[float, float]] = field(default_factory=dict)
    unmeasured: list[str] = field(default_factory=list)

    @property
    def url_loss_total(self) -> float:
        return sum(x.lost for x in self.losses if x.scope == "URL")

    @property
    def site_loss_total(self) -> float:
        return sum(x.lost for x in self.losses if x.scope == "SITE")


def site_score(
    inputs: list[CheckInput],
    *,
    spec: Spec = SPEC_1_8_0,
    breadth_exponent: float = BREADTH_EXPONENT,
) -> SiteResult:
    """사이트 점수 — v2 산식 그대로 + 손실의 검사 단위 귀속.

    ## 산식은 v2 와 한 글자도 다르지 않다

        도달률 = Π (1 − 차단검사 실패비율)
        품질   = Σ 단계 (가중치 − Σ 손실)      단계 고정분모, N/A 는 단계 안 재분배
        점수   = 도달률 × 품질

    v3 이 더한 것은 **회계**다: 품질에서 빠진 모든 점이 검사 하나에 귀속되고,
    각 검사는 명세의 scope(URL|SITE)를 달고 있다. 그래서

        100 − Σ(URL손실) − Σ(SITE손실) == 품질

    이 항등식이 되고, "페이지는 다 좋은데 사이트가 낮다" 의 이유를 화면이 SITE
    손실 목록과 도달률로 정확히 말할 수 있다.

    ## NOT_SAMPLED 는 사이트 점수에 없다

    사이트 점수에서 성능은 상위 5장 표본으로 **실제로 잰다** — coverage 가 표본을
    반영하고, 문턱(min_measured_ratio) 미달이면 UNKNOWN 으로 배점을 잃는다
    (methodology §3.3). NOT_SAMPLED 는 페이지 점수 전용 상태이므로 여기 들어오면
    입력 오류다.
    """
    by_id: dict[str, CheckInput] = {}
    for item in inputs:
        if item.check_id not in spec.checks:
            raise ValueError(f"{item.check_id} 는 이 명세에 없는 검사다")
        if item.check_id in by_id:
            raise ValueError(f"{item.check_id} 판정이 두 번 들어왔다")
        if item.status == "NOT_SAMPLED":
            raise ValueError(
                f"{item.check_id}: NOT_SAMPLED 는 페이지 점수 전용이다. 사이트 "
                "점수에서 성능 표본은 coverage 와 UNKNOWN(문턱 미달)으로 반영된다."
            )
        by_id[item.check_id] = item

    losses: list[AttributedLoss] = []
    gate_events: list[GateEvent] = []
    gate_unverified: list[str] = []
    stage_scores: dict[str, tuple[float, float]] = {}
    unmeasured: list[str] = []
    reach = 1.0
    quality = 0.0

    for stage, meta in spec.stages.items():
        members = spec.stage_members(stage)
        live = [c for c in members if by_id.get(c) and by_id[c].status != "NOT_APPLICABLE"]

        if meta.is_gate:
            for check_id in live:
                item = by_id[check_id]
                if item.status == "UNKNOWN":
                    # 관측하지 않은 차단을 있다고 하면 없는 결함을 지어내는 것(0-A).
                    gate_unverified.append(check_id)
                    continue
                share = STATUS_MULTIPLIER.get(item.status, 1.0) * min(1.0, item.coverage_ratio)
                if share > 0:
                    reach *= 1.0 - share
                    gate_events.append(GateEvent(check_id, share))
            stage_scores[stage] = (round(reach * 100, 2), 100.0)
            continue

        budget = meta.points
        if not live:
            # 단계 전체가 해당 없음(또는 미제공). v2 산식은 이 단계의 가중치를
            # 재분배하지 않고 그냥 잃는다 — 항등식을 지키려면 이 손실도 귀속돼야
            # 하므로 구성 검사에 배점 비례로 나눈다. (실코드 평가기는 이 경우
            # 가중치를 재정규화한다 — 문서 §4 에 불일치로 기록해 뒀다.)
            raw_total = sum(spec.checks[c].points for c in members)
            for check_id in members:
                d = spec.checks[check_id]
                losses.append(
                    AttributedLoss(
                        check_id, stage, d.scope,
                        by_id[check_id].status if check_id in by_id else "NOT_PROVIDED",
                        budget * d.points / raw_total,
                        "STAGE_NOT_APPLICABLE",
                        "단계 전체 해당 없음 — v2 산식은 단계 가중치를 재분배하지 않는다",
                    )
                )
            stage_scores[stage] = (0.0, 0.0)
            continue

        declared = sum(spec.checks[c].points for c in live)
        scale = budget / declared

        stage_lost = 0.0
        for check_id in live:
            item = by_id[check_id]
            d = spec.checks[check_id]
            points = d.points * scale
            if item.status == "UNKNOWN":
                # 절대평가: 재지 못한 항목은 배점을 유지한 채 0점(ADR 0016).
                lost = points
                unmeasured.append(check_id)
                why = "측정 불가 — 배점은 분모에 남고 점수를 얻지 못한다"
            else:
                breadth = min(1.0, item.coverage_ratio) ** breadth_exponent
                lost = points * STATUS_MULTIPLIER.get(item.status, 1.0) * breadth * item.confidence
                why = d.why
            if lost > 0:
                losses.append(AttributedLoss(check_id, stage, d.scope, item.status, lost, "CHECK", why))
            stage_lost += lost

        stage_scores[stage] = (round(budget - stage_lost, 2), budget)
        quality += budget - stage_lost

    losses.sort(key=lambda x: -x.lost)
    return SiteResult(
        score=round(reach * quality, 2),
        reach=reach,
        quality=quality,
        losses=losses,
        gate_events=gate_events,
        gate_unverified=gate_unverified,
        stage_scores=stage_scores,
        unmeasured=unmeasured,
    )


# --------------------------------------------------------------------------- #
# 페이지 점수 — URL 범위 검사만, 같은 단계 구조를 페이지 분모로 재정규화
# --------------------------------------------------------------------------- #


@dataclass
class PageResult:
    """페이지 하나의 점수.

    항등식:  quality == 100 − Σ(losses[].lost)     (scoreable 단계가 있을 때)
    곱셈:    score  == round(reach × quality, 2)

    reach 는 **이 페이지의 관문**이다 — 이 페이지의 robots meta·HTTP 상태가
    실패하면 이 페이지는 검색에 존재하지 않으므로 점수가 ~0 이 된다.
    """

    score: float | None
    reach: float
    quality: float | None
    status: str  # SCORED | UNKNOWN | NOT_APPLICABLE
    stage_scores: dict[str, tuple[float, float]] = field(default_factory=dict)
    losses: list[AttributedLoss] = field(default_factory=list)
    gate_unverified: list[str] = field(default_factory=list)
    unmeasured: list[str] = field(default_factory=list)
    not_sampled: list[str] = field(default_factory=list)
    not_applicable: list[str] = field(default_factory=list)
    not_sampled_note_ko: str = NOT_SAMPLED_NOTE_KO


def page_score(
    inputs: list[CheckInput],
    *,
    spec: Spec = SPEC_1_8_0,
    breadth_exponent: float = BREADTH_EXPONENT,
) -> PageResult:
    """페이지 p 의 점수 — 그 페이지에서 판정된 URL 범위 검사만으로.

    ## 왜 SITE 검사를 거부하는가 (오류로)

    "본문 중복이 없다" 는 페이지 하나의 성질이 아니다. SITE 검사를 페이지에 붙이면
    분모가 다른 두 숫자가 같은 눈금처럼 보이고, 그것이 우리가 타사에서 잡아낸 바로
    그 결함이다(methodology §2.9 마지막 경고). 조용히 무시하지 않고 오류를 낸다 —
    조용한 무시는 호출자의 실수를 산식이 덮어 주는 것이다.

    ## 분모 — 단계별 URL 고정분모

    단계 s 의 페이지 분모 = 그 단계 URL 검사 배점 합 (명세 상수, url_stage_budget).
    N/A 와 NOT_SAMPLED 는 분모에서 빠지고 그 몫이 단계 안 형제에게 재분배된다.
    UNKNOWN 은 분모에 남아 0점이다. 사이트 점수와 같은 규칙, 같은 방향이다 —
    재려다 실패한 것만 아프고, 정책상 안 잰 것과 없는 것은 아프지 않다.

    ## 단계 가중치 재정규화

    페이지 종합 = 도달률 × Σ(단계점수 × 가중치) / Σ(채점 가능 단계의 가중치).

    사이트 점수(v2)와 달리 **채점 가능한 단계로 재정규화한다.** 페이지는 템플릿에
    따라 구조가 다르다 — 구조화 데이터가 원래 없는 안내 페이지에서 S5 가 통째로
    빠졌다고 그 페이지가 감점되면, 페이지 순위가 결함이 아니라 템플릿 종류로
    갈린다. 실코드 평가기(evaluator.py)도 영역 단위에서는 같은 재정규화를 한다.
    """
    by_id: dict[str, CheckInput] = {}
    for item in inputs:
        d = spec.checks.get(item.check_id)
        if d is None:
            raise ValueError(f"{item.check_id} 는 이 명세에 없는 검사다")
        if d.scope != "URL":
            raise ValueError(
                f"{item.check_id} 는 SITE 범위 검사다. 페이지 점수에 넣을 수 없다 — "
                "여러 장을 봐야 잴 수 있는 것을 한 장의 점수에 붙이면 분모가 다른 "
                "두 숫자가 같은 눈금처럼 보인다."
            )
        if item.status == "NOT_SAMPLED" and item.check_id not in NOT_SAMPLED_ALLOWED:
            raise ValueError(
                f"{item.check_id}: NOT_SAMPLED 는 명세가 표본 정책을 선언한 검사"
                "(성능)에만 허용된다. 아무 데나 붙이면 '안 재기로 했다' 가 절대평가를 "
                "비껴가는 뒷문이 된다."
            )
        if item.check_id in by_id:
            raise ValueError(f"{item.check_id} 판정이 두 번 들어왔다")
        by_id[item.check_id] = item

    reach = 1.0
    gate_unverified: list[str] = []
    unmeasured: list[str] = []
    not_sampled: list[str] = []
    not_applicable: list[str] = []
    stage_scores: dict[str, tuple[float, float]] = {}

    # (단계, 가중치, 손실목록) — 재정규화 전에 단계별로 모은다.
    scoreable: list[tuple[str, float, float, list[tuple[str, float, str, str]]]] = []

    for stage, meta in spec.stages.items():
        members = [c for c in spec.stage_members(stage) if spec.checks[c].scope == "URL"]

        if meta.is_gate:
            for check_id in members:
                item = by_id.get(check_id)
                if item is None or item.status == "NOT_APPLICABLE":
                    continue
                if item.status == "UNKNOWN":
                    gate_unverified.append(check_id)  # 0-A: 없는 차단을 지어내지 않는다
                    continue
                share = STATUS_MULTIPLIER.get(item.status, 1.0) * min(1.0, item.coverage_ratio)
                if share > 0:
                    reach *= 1.0 - share
            stage_scores[stage] = (round(reach * 100, 2), 100.0)
            continue

        live: list[str] = []
        for check_id in members:
            item = by_id.get(check_id)
            if item is None:
                continue
            if item.status == "NOT_APPLICABLE":
                not_applicable.append(check_id)
            elif item.status == "NOT_SAMPLED":
                not_sampled.append(check_id)
            else:
                live.append(check_id)

        if not live:
            stage_scores[stage] = (0.0, 0.0)
            continue

        budget = spec.url_stage_budget(stage)
        declared = sum(spec.checks[c].points for c in live)
        scale = budget / declared

        stage_lost = 0.0
        stage_loss_rows: list[tuple[str, float, str, str]] = []
        for check_id in live:
            item = by_id[check_id]
            d = spec.checks[check_id]
            points = d.points * scale
            if item.status == "UNKNOWN":
                lost = points
                unmeasured.append(check_id)
                why = "측정 불가 — 배점은 분모에 남고 점수를 얻지 못한다"
            else:
                breadth = min(1.0, item.coverage_ratio) ** breadth_exponent
                lost = points * STATUS_MULTIPLIER.get(item.status, 1.0) * breadth * item.confidence
                why = d.why
            if lost > 0:
                stage_loss_rows.append((check_id, lost, item.status, why))
            stage_lost += lost

        fraction_intact = (budget - stage_lost) / budget
        stage_scores[stage] = (round(100.0 * fraction_intact, 2), 100.0)
        scoreable.append((stage, meta.points, stage_lost / budget, stage_loss_rows))

    if not scoreable:
        provided = [i.status for i in inputs]
        status = (
            "NOT_APPLICABLE"
            if provided and all(s in {"NOT_APPLICABLE", "NOT_SAMPLED"} for s in provided)
            else "UNKNOWN"
        )
        return PageResult(
            None, reach, None, status,
            stage_scores=stage_scores, gate_unverified=gate_unverified,
            unmeasured=unmeasured, not_sampled=not_sampled, not_applicable=not_applicable,
        )

    weight_total = sum(w for _, w, _, _ in scoreable)
    losses: list[AttributedLoss] = []
    quality = 100.0
    for stage, w, fraction_lost, rows in scoreable:
        stage_share = w / weight_total * 100.0
        quality -= stage_share * fraction_lost
        budget = spec.url_stage_budget(stage)
        for check_id, lost, status_, why in rows:
            losses.append(
                AttributedLoss(
                    check_id, stage, "URL", status_,
                    stage_share * (lost / budget), "CHECK", why,
                )
            )

    losses.sort(key=lambda x: -x.lost)
    return PageResult(
        score=round(reach * quality, 2),
        reach=reach,
        quality=quality,
        status="SCORED",
        stage_scores=stage_scores,
        losses=losses,
        gate_unverified=gate_unverified,
        unmeasured=unmeasured,
        not_sampled=not_sampled,
        not_applicable=not_applicable,
    )


# --------------------------------------------------------------------------- #
# 성능 표본 — 누가 표본에 드는지는 명세가 정한다 (조작 유인 차단)
# --------------------------------------------------------------------------- #


def lab_sample_pages(pages: list[tuple[str, float]], *, max_urls: int = 5) -> list[str]:
    """실험실 성능을 실측할 페이지 — 중요도 상위 max_urls 장.

    선정 기준이 명세에 고정돼 있어(중요도는 url_importance 가 정한다) 재는 쪽이
    표본을 고를 수 없다. NOT_SAMPLED 가 감점이 아닐 수 있는 근거가 이것이다 —
    표본 밖에 두는 것으로 이득을 볼 수 있는 사람이 없다.

    동률은 입력 순서(크롤 발견 순)를 유지한다 — 같은 입력이면 같은 표본이다.
    """
    ranked = sorted(range(len(pages)), key=lambda i: (-pages[i][1], i))
    return [pages[i][0] for i in ranked[:max_urls]]


# --------------------------------------------------------------------------- #
# 부재 주장 — 표본으로 존재는 증명되지만 부재는 증명되지 않는다
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SampleScope:
    """collect/sample.py 의 SampleScope 와 같은 사실·같은 규칙 (프로토타입 자족).

    실구현에서는 저쪽이 단일 구현이고 여기는 참조일 뿐이다 — 규칙이 갈라지면
    저쪽이 맞다.
    """

    crawl_is_exhaustive: bool
    page_count: int
    declared_url_count: int

    @property
    def is_whole_site(self) -> bool:
        if not self.crawl_is_exhaustive:
            return False
        if self.page_count >= 2:
            return True
        return self.declared_url_count == 1


def absence_claim(
    scope: SampleScope, *, violations_found: int, subject_ko: str
) -> tuple[str, str]:
    """부재형 검사(no_duplicate_* · no_orphan · no_broken_links …)의 판정.

    ## 왜 이 함수가 따로 있는가

    존재 주장과 부재 주장은 증명 부담이 다르다. "중복이 있다" 는 두 장이면
    증명되지만, "중복이 없다" 는 **전체를 봐야만** 증명된다. 잘린 크롤(100장
    상한)에서 PASS 를 단정하는 것이 이 판이 고치는 결함이다 — sample.py 의
    is_whole_site 규칙은 옳았지만 수집기가 1장 크롤에서만 물었다.

    ## 판정표

        결함 발견            → FAIL     존재는 표본으로 증명된다
        미발견 + 전체 크롤   → PASS     부재가 실제로 증명됐다
        미발견 + 표본        → UNKNOWN  "본 N장 중에는 없었다. 나머지는 확인 못함"

    UNKNOWN 은 분모에 남아 0점이므로(ADR 0016) **덜 재서 점수가 오르지 않는다** —
    성질 시험이 이것을 고정한다.
    """
    if violations_found > 0:
        return "FAIL", f"{subject_ko}이(가) {violations_found}건 발견되었습니다."
    if scope.is_whole_site:
        return "PASS", f"사이트 전체를 확인했고 {subject_ko}이(가) 없습니다."
    return "UNKNOWN", (
        f"본 {scope.page_count}장 중에는 {subject_ko}이(가) 없었습니다. 다만 사이트 "
        "전체를 본 것이 아니므로 나머지 페이지는 확인하지 못했습니다. 사이트 전체 "
        "진단으로 다시 재면 판정됩니다."
    )


# --------------------------------------------------------------------------- #
# 변화 대응 — 페이지 하나만 다시 쟀을 때
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SiteAudit:
    """전체 진단 한 번의 기록. measured_on 이 SITE 값의 '기준 날짜' 가 된다."""

    measured_on: str  # 'YYYY-MM-DD'
    outcomes: dict[str, CheckInput]


@dataclass
class SiteContextValue:
    """페이지 화면에 곁들이는 SITE 검사 값 — 이 페이지에서 새로 잰 것이 아니다."""

    check_id: str
    status: str
    as_of: str
    note_ko: str


def page_panel(
    page_inputs: list[CheckInput],
    site_audit: SiteAudit,
    *,
    spec: Spec = SPEC_1_8_0,
) -> tuple[PageResult, list[SiteContextValue]]:
    """페이지 화면에 나가는 두 덩어리: 새로 계산한 페이지 점수 + 이전 전체 진단의
    SITE 값.

    ## 왜 SITE 값을 페이지 재크롤로 갱신하지 않는가

    "중복 없음" 은 페이지 하나를 다시 봐서 알 수 있는 사실이 아니다. 페이지 하나를
    고치고 다시 쟀을 때 URL 판정만 갱신하고, SITE 판정은 마지막 전체 진단 값에
    **날짜를 달아** 유지한다. 날짜가 없으면 사용자는 방금 잰 값으로 읽고, 고친
    것이 반영 안 됐다며 고장 신고를 하게 된다(0-J).
    """
    result = page_score(page_inputs, spec=spec)
    context = [
        SiteContextValue(
            check_id,
            site_audit.outcomes[check_id].status,
            site_audit.measured_on,
            f"이 값은 {site_audit.measured_on} 전체 진단 기준입니다. "
            "전체 재진단 시 갱신됩니다.",
        )
        for check_id, d in spec.checks.items()
        if d.scope == "SITE" and check_id in site_audit.outcomes
    ]
    return result, context


def page_budget_report(spec: Spec = SPEC_1_8_0) -> str:
    """단계별 페이지 고정분모(URL 배점 합)를 사람이 읽을 수 있게 편다."""
    lines = [f"{'단계':<12}{'URL배점':>8}{'SITE배점':>9}{'단계원배점':>10}"]
    for stage, meta in spec.stages.items():
        url = spec.url_stage_budget(stage)
        total = sum(d.points for d in spec.checks.values() if d.stage == stage)
        lines.append(f"{meta.name_ko:<12}{url:>8.2f}{total - url:>9.2f}{total:>10.2f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(page_budget_report())
