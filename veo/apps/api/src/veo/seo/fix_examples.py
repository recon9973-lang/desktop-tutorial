"""검사별 조치 코드 예시 — 붙여넣을 수 있는 형태로.

백로그 항목 "조치를 붙여넣을 수 있는 코드로" 의 구현이다. 문장 설명(remediation_ko)은
이미 있지만, 화면의 "더보기" 가 보여줄 **코드 한 조각**이 없어서 읽는 사람이 문장을
코드로 번역해야 했다.

여기 있는 것은 배점이 아니라 조치 문구다 — 명세가 아니라 코드에 사는 것이 맞다
(수집기의 remediation_ko 문장들과 같은 지위). 검사마다 정답 코드가 사실상 하나로
정해지는 항목만 싣는다. 사이트 구조에 따라 달라지는 항목(내부 링크·중복 통합 등)은
코드를 지어내면 틀린 코드가 되므로 싣지 않는다 — 없는 항목은 문장 설명만 나간다.

플레이스홀더는 대문자 한글로 표시한다(예: 페이지주소) — 그대로 붙여넣으면 동작하지
않는다는 것이 눈에 보여야 한다.

상호 자리는 :data:`BRAND_PLACEHOLDER` 하나로 통일한다. 예전에는 가상의 병원 이름
("온담의원")이 박혀 있었는데, 복사해 쓰라고 내놓은 코드에 **남의 상호**가 들어 있으니
읽는 사람은 그것이 자기 사이트에서 측정된 값인 줄 알았다. 아는 업체명이 있으면
:func:`with_brand` 가 이 자리에만 갈아 끼운다 — 모르면 자리표시자 그대로 두고, 없는
이름을 지어내지 않는다.
"""

from __future__ import annotations

from typing import Final

__all__ = ["BRAND_PLACEHOLDER", "code_example_for", "with_brand"]

#: 예시 코드 안의 상호 자리. 다른 자리표시자(페이지주소·도메인)와 같은 관례다.
BRAND_PLACEHOLDER: Final = "업체명"

_EXAMPLES: Final[dict[str, str]] = {
    "seo.ux.mobile_viewport": (
        '<!-- <head> 안에 한 줄 -->\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    ),
    "seo.html.charset_declared": (
        '<!-- <head> 맨 앞에 -->\n'
        '<meta charset="utf-8">'
    ),
    "seo.html.doctype_standards_mode": (
        "<!-- 문서 첫 줄에 -->\n"
        "<!DOCTYPE html>"
    ),
    "seo.canonical.declared_and_consistent": (
        "<!-- 페이지 자신의 대표 주소를 선언 -->\n"
        '<link rel="canonical" href="https://도메인/이_페이지_주소/">'
    ),
    "seo.onpage.meta_description_quality": (
        "<!-- 80~120자, 페이지 내용 요약 -->\n"
        '<meta name="description" content="지역명 + 업체명. 핵심 진료·검사 안내. '
        '예약 및 진료시간 정보.">'
    ),
    "seo.onpage.single_title_element": (
        "<!-- <title> 은 문서에 하나만 -->\n"
        "<title>페이지 주제 — 업체명</title>"
    ),
    "seo.onpage.single_meaningful_h1": (
        "<!-- 페이지 주제 하나만 h1, 나머지는 h2 로 -->\n"
        "<h1>페이지 주제</h1>\n"
        "<h2>하위 소제목</h2>"
    ),
    "seo.onpage.html_lang_declared": (
        '<html lang="ko">'
    ),
    "seo.onpage.image_alt_coverage": (
        "<!-- 내용 이미지는 무엇인지, 장식 이미지는 빈 값으로 -->\n"
        '<img src="doctor.jpg" alt="홍길동 원장 — 내과 전문의">\n'
        '<img src="divider.png" alt="">'
    ),
    "seo.sd.naver_supported_type": (
        "<!-- 카카오톡·네이버 공유 미리보기 -->\n"
        '<meta property="og:title" content="페이지 제목">\n'
        '<meta property="og:description" content="한 줄 소개">\n'
        '<meta property="og:image" content="https://도메인/공유이미지.jpg">\n'
        '<meta property="og:url" content="https://도메인/이_페이지_주소/">'
    ),
    "seo.robots.meta_indexable": (
        "<!-- 색인을 막고 있다면 이 줄을 제거 -->\n"
        '<meta name="robots" content="noindex">  <!-- ← 삭제 -->'
    ),
    "seo.crawl.crawlable_anchors": (
        "<!-- 크롤러가 따라갈 수 있게 href 를 준다 -->\n"
        '<a onclick="go(\'/진료안내\')">진료안내</a>          <!-- ✕ -->\n'
        '<a href="/진료안내/" onclick="go(this.href)">진료안내</a>  <!-- ✓ -->'
    ),
    "seo.perf.text_compression": (
        "# 웹서버 설정 (Apache 예)\n"
        "AddOutputFilterByType DEFLATE text/html text/css application/javascript"
    ),
    "seo.security.no_mixed_content": (
        "<!-- http → https 로 -->\n"
        '<img src="http://도메인/img.jpg">   <!-- ✕ -->\n'
        '<img src="https://도메인/img.jpg">  <!-- ✓ -->'
    ),
    "seo.onpage.title_present_and_unique": (
        "<!-- 페이지마다 다른 제목 — [페이지 주제] + 업체명 -->\n"
        "<title>불면증 클리닉 — 업체명</title>\n"
        "<title>오시는 길 — 업체명</title>"
    ),
    "seo.onpage.heading_hierarchy": (
        "<!-- 계층을 건너뛰지 않는다: h2 다음은 h3 -->\n"
        "<h2>진료 안내</h2>\n"
        "  <h3>내과</h3>   <!-- ✓ h2→h3 -->\n"
        "  <h5>내과</h5>   <!-- ✕ h2→h5 건너뜀 -->"
    ),
    "seo.canonical.not_cross_domain": (
        "<!-- canonical 은 자기 도메인의 주소여야 한다 -->\n"
        '<link rel="canonical" href="https://남의도메인.com/…">   <!-- ✕ -->\n'
        '<link rel="canonical" href="https://내도메인/이_페이지/"> <!-- ✓ -->'
    ),
    "seo.content.lazy_loading_safe": (
        '<!-- 첫 화면에 보이는 큰 이미지에는 lazy 를 걸지 않는다 -->\n'
        '<img src="hero.jpg" loading="lazy">   <!-- ✕ 첫 화면 이미지 -->\n'
        '<img src="hero.jpg" fetchpriority="high">  <!-- ✓ -->\n'
        '<img src="footer-map.jpg" loading="lazy">  <!-- ✓ 화면 아래 이미지 -->'
    ),
    "seo.sd.declared": (
        '<!-- 병원 기본 정보 구조화 데이터 — <head> 안에 -->\n'
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "MedicalClinic",\n'
        '  "name": "업체명",\n'
        '  "address": {"@type": "PostalAddress",\n'
        '              "addressLocality": "지역", "streetAddress": "주소"},\n'
        '  "telephone": "+82-00-000-0000",\n'
        '  "openingHours": "Mo-Fr 09:00-18:00"\n'
        '}\n'
        "</script>"
    ),
    "seo.sitemap.discoverable": (
        "# robots.txt 마지막 줄에 사이트맵 위치를 선언\n"
        "Sitemap: https://도메인/sitemap.xml"
    ),
    "seo.http.redirect_chain_sane": (
        "# 리다이렉트는 한 번에 최종 주소로\n"
        "http://a → https://a → https://www.a → 페이지   # ✕ 3단계\n"
        "http://a → https://www.a/페이지                  # ✓ 1단계"
    ),
    "seo.onpage.descriptive_anchor_text": (
        '<!-- 링크 문구에 목적지의 주제를 담는다 -->\n'
        '<a href="/불면증/">자세히 보기</a>        <!-- ✕ -->\n'
        '<a href="/불면증/">불면증 치료 안내 보기</a>  <!-- ✓ -->'
    ),
    "seo.content.breadcrumb_present": (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "BreadcrumbList",\n'
        '  "itemListElement": [\n'
        '    {"@type": "ListItem", "position": 1, "name": "홈", "item": "https://도메인/"},\n'
        '    {"@type": "ListItem", "position": 2, "name": "진료안내", "item": "https://도메인/진료안내/"}\n'
        '  ]\n'
        '}\n'
        "</script>"
    ),
    # ---- GEO — AI 답변 엔진이 인용할 수 있는 구조 ----
    "geo.extract.direct_answer_present": (
        "<!-- 첫 문단이 곧 답이 되게 — AI 는 이 문장을 그대로 인용한다 -->\n"
        "<p>업체명은 △△역 도보 3분 거리의 불면증·수면장애 전문 한의원으로,\n"
        "비약물 치료 프로그램을 운영합니다.</p>"
    ),
    "geo.evidence.author_identified": (
        '<!-- 의료 콘텐츠는 누가 썼는지가 인용 신뢰의 핵심 -->\n'
        '<p class="author">글쓴이: 홍길동 원장 (한방신경정신과 전문의)</p>\n'
        '<script type="application/ld+json">\n'
        '{"@context": "https://schema.org", "@type": "Person",\n'
        ' "name": "홍길동", "jobTitle": "한의사",\n'
        ' "worksFor": {"@type": "MedicalClinic", "name": "업체명"}}\n'
        "</script>"
    ),
    "geo.fresh.dates_present": (
        '<!-- 작성·수정 날짜를 기계가 읽을 수 있게 -->\n'
        '<time datetime="2026-08-02">2026년 8월 2일 작성</time>\n'
        '<meta property="article:modified_time" content="2026-08-02T09:00:00+09:00">'
    ),
    "geo.access.training_bot_policy_declared": (
        "# robots.txt — 학습용 크롤러 방침을 명시 (허용·차단은 사업 판단)\n"
        "User-agent: GPTBot\n"
        "Allow: /\n"
        "\n"
        "User-agent: Google-Extended\n"
        "Allow: /"
    ),
    "geo.extract.heading_structure_semantic": (
        "<!-- 본문 주제를 담은 h1 하나 — 로고는 h1이 아니라 이미지·링크로 -->\n"
        "<h1>불면증 치료 안내</h1>\n"
        "<h2>치료 방법</h2>"
    ),
    "geo.sd.matches_visible_content": (
        '<!-- 구조화 데이터 값은 화면에 보이는 것과 같아야 한다 -->\n'
        "<h1>업체명</h1>\n"
        '<script type="application/ld+json">\n'
        '{"@context": "https://schema.org", "@type": "MedicalClinic",\n'
        ' "name": "업체명"}  <!-- ✓ 화면의 이름 그대로 -->\n'
        "</script>"
    ),
    "geo.meta.opengraph_present": (
        '<meta property="og:title" content="페이지 제목">\n'
        '<meta property="og:description" content="한 줄 소개">\n'
        '<meta property="og:image" content="https://도메인/공유이미지.jpg">'
    ),
}


def code_example_for(check_id: str) -> str | None:
    """이 검사의 조치 코드 예시. 정답 코드가 하나로 정해지지 않는 검사는 ``None``."""
    return _EXAMPLES.get(check_id)


def with_brand(example: str | None, brand: str | None) -> str | None:
    """예시 코드의 상호 자리를 **실제 업체명**으로 바꾼다.

    담당자는 이 코드를 그대로 복사해 붙여넣는다. 그 자리에 자리표시자가 남아 있으면
    한 번 더 손봐야 하고, 손보는 것을 잊으면 자리표시자가 그대로 사이트에 올라간다.

    다만 **아는 이름만** 넣는다. 등록된 브랜드가 없으면 자리표시자를 그대로 둔다 —
    도메인이나 제목에서 상호를 추측해 넣으면, 틀린 이름을 확신을 가지고 붙여넣게 만든다.
    그것은 자리표시자보다 나쁘다.
    """
    if example is None or brand is None:
        return example
    name = brand.strip()
    if not name:
        return example
    return example.replace(BRAND_PLACEHOLDER, name)
