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
"""

from __future__ import annotations

from typing import Final

__all__ = ["code_example_for"]

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
        '<meta name="description" content="지역명 + 병원명. 핵심 진료·검사 안내. '
        '예약 및 진료시간 정보.">'
    ),
    "seo.onpage.single_title_element": (
        "<!-- <title> 은 문서에 하나만 -->\n"
        "<title>페이지 주제 — 병원명</title>"
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
}


def code_example_for(check_id: str) -> str | None:
    """이 검사의 조치 코드 예시. 정답 코드가 하나로 정해지지 않는 검사는 ``None``."""
    return _EXAMPLES.get(check_id)
