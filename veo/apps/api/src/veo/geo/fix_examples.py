"""GEO 검사별 조치 코드 예시 — 붙여넣을 수 있는 형태로.

SEO 쪽(:mod:`veo.seo.fix_examples`)과 **같은 규칙, 같은 자리표시자**를 쓴다. 두 화면이
나란히 놓이는데 한쪽만 코드가 나오면 읽는 사람은 GEO 쪽에 고칠 방법이 없다고 읽는다.

실측 2026-08-07 — 운영 GEO 리포트의 `fix_example` 은 37개 검사 중 **하나만** 채워져
있었다(`access.search_bots_allowed`). 나머지는 문장 설명만 나갔고, 읽는 사람이 그 문장을
직접 코드로 옮겨야 했다. SEO 는 같은 자리에 30개가 등록돼 있었다.

## 무엇을 싣고 무엇을 싣지 않는가

**정답 코드가 사실상 하나로 정해지는 항목만 싣는다.** 사이트 구조에 따라 달라지는 것
(중복 문단 통합·내부 링크·외부 프로필 확보 등)은 코드를 지어내면 **틀린 코드**가 되므로
싣지 않는다. 없는 항목은 지금처럼 문장 설명만 나간다 — 빈 것이 틀린 것보다 낫다.

GEO 는 SEO 와 성격이 하나 다르다. **코드가 아니라 글의 구조가 답인 항목이 있다**
(직접 답변 문단·제목 구조·표). 그런 항목은 HTML 뼈대와 함께 **글을 어떻게 쓰는지**를
같은 조각에 담는다 — 마케터가 그대로 복사해 문구만 갈아 끼우면 되도록.

## 자리표시자

`업체명` · `페이지주소` · `도메인` 처럼 대문자 한글로 둔다. 그대로 붙여넣으면 동작하지
않는다는 것이 눈에 보여야 한다. 상호 자리는 :data:`veo.seo.fix_examples.BRAND_PLACEHOLDER`
하나로 통일하고, 아는 업체명이 있으면 :func:`veo.seo.fix_examples.with_brand` 가 그
자리만 갈아 끼운다 — 모르면 자리표시자를 그대로 둔다. 도메인이나 제목에서 상호를
추측해 넣으면 **틀린 이름을 확신을 가지고 붙여넣게** 만든다.
"""

from __future__ import annotations

from typing import Final

from veo.seo.fix_examples import BRAND_PLACEHOLDER

__all__ = ["code_example_for"]

_B: Final = BRAND_PLACEHOLDER

_EXAMPLES: Final[dict[str, str]] = {
    # ------------------------------------------------------------------ 접근·검색 적격성
    "geo.access.indexable": (
        "<!-- <head> 안. 이 줄이 있으면 AI 답변 엔진도 이 페이지를 쓰지 않는다 -->\n"
        '<meta name="robots" content="index,follow">\n'
        "\n"
        "<!-- 반대로 아래가 있으면 지운다 -->\n"
        '<!-- <meta name="robots" content="noindex"> -->'
    ),
    "geo.access.search_bots_allowed": (
        "# robots.txt — 검색 목적 AI 크롤러를 허용한다.\n"
        "# 이들이 막히면 AI 답변에 인용될 길 자체가 없다.\n"
        "User-agent: OAI-SearchBot\n"
        "Allow: /\n"
        "\n"
        "User-agent: PerplexityBot\n"
        "Allow: /\n"
        "\n"
        "User-agent: Google-Extended\n"
        "Allow: /\n"
        "\n"
        "User-agent: Bingbot\n"
        "Allow: /"
    ),
    "geo.access.training_bot_policy_declared": (
        "# robots.txt — 학습용 크롤러 방침을 **의도적으로** 적는다.\n"
        "# 허용이든 거부든, 적혀 있으면 판단한 것이고 없으면 판단하지 않은 것이다.\n"
        "# 아래는 '학습은 거부, 검색 인용은 허용' 의 예다.\n"
        "User-agent: GPTBot\n"
        "Disallow: /\n"
        "\n"
        "User-agent: CCBot\n"
        "Disallow: /\n"
        "\n"
        "# 검색용은 위에서 따로 허용한다 (OAI-SearchBot 등)"
    ),
    # ------------------------------------------------------------------ 답변 추출성
    "geo.extract.direct_answer_present": (
        "<!-- 질문을 제목으로 두고, **바로 다음 문단**에 답을 완결해서 쓴다.\n"
        "     AI 는 이 한 문단만 떼어 인용한다 — 앞뒤를 읽어야 뜻이 통하면 못 쓴다. -->\n"
        "<h2>임플란트 수술 후 붓기는 며칠 가나요?</h2>\n"
        "<p>임플란트 수술 후 붓기는 보통 2~3일째 가장 심하고 5~7일 안에 대부분\n"
        "가라앉습니다. 일주일이 지나도 붓기와 통증이 함께 심해지면 감염 가능성이\n"
        "있으므로 내원해 확인해야 합니다.</p>\n"
        "\n"
        "<!-- 첫 문단 안에 '무엇이 · 얼마나 · 언제까지 · 예외는' 이 들어가면 좋다 -->"
    ),
    "geo.extract.passage_self_contained": (
        "<!-- 나쁜 예 — '위에서 말한' 이 있으면 그 문단만 떼어냈을 때 뜻이 끊긴다 -->\n"
        "<p>위에서 말한 방법으로 관리하시면 됩니다.</p>\n"
        "\n"
        "<!-- 좋은 예 — 주어와 대상을 문단 안에서 다시 밝힌다 -->\n"
        f"<p>{_B}에서는 임플란트 수술 후 첫 일주일 동안 찬 찜질과 처방된 항생제\n"
        "복용을 권합니다. 흡연과 빨대 사용은 잇몸 회복을 늦추므로 피하십시오.</p>"
    ),
    "geo.extract.heading_structure_semantic": (
        "<!-- 제목은 '질문 하나 = 제목 하나' 로 나눈다. 글자 크기 때문에 쓰지 않는다. -->\n"
        "<h1>임플란트</h1>\n"
        "  <h2>임플란트 수술은 얼마나 아픈가요?</h2>\n"
        "  <h2>임플란트 비용은 얼마인가요?</h2>\n"
        "    <h3>보험이 적용되는 경우</h3>\n"
        "  <h2>임플란트 수명은 몇 년인가요?</h2>\n"
        "\n"
        "<!-- h1 은 한 장에 하나. h2 를 건너뛰고 h3 로 가지 않는다. -->"
    ),
    "geo.extract.tables_lists_machine_readable": (
        "<!-- 비교·수치는 문장에 풀어 쓰지 말고 표로. AI 가 값을 그대로 읽어 간다. -->\n"
        "<table>\n"
        "  <caption>임플란트 종류별 비용과 기간</caption>\n"
        "  <thead>\n"
        "    <tr><th>종류</th><th>비용(1개)</th><th>치료 기간</th></tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        "    <tr><td>국산 임플란트</td><td>100만원~</td><td>3~4개월</td></tr>\n"
        "    <tr><td>수입 임플란트</td><td>150만원~</td><td>3~4개월</td></tr>\n"
        "  </tbody>\n"
        "</table>\n"
        "\n"
        "<!-- 이미지로 만든 표는 읽히지 않는다. 반드시 글자로 된 표여야 한다. -->"
    ),
    # ------------------------------------------------------------------ 근거·출처 투명성
    "geo.evidence.claims_have_sources": (
        "<!-- 검증이 필요한 주장 바로 옆에 출처를 붙인다. 글 맨 끝에 몰아 두지 않는다. -->\n"
        "<p>임플란트 10년 생존율은 약 95%로 보고됩니다\n"
        '(<a href="https://출처주소" rel="nofollow">대한구강악안면임플란트학회, 2024</a>).</p>\n'
        "\n"
        "<!-- 출처에는 '누가 · 언제' 가 들어가야 한다. '전문가에 따르면' 은 출처가 아니다. -->"
    ),
    "geo.evidence.author_identified": (
        "<!-- ① 화면에 보이게 -->\n"
        '<div class="byline">\n'
        "  <span>작성 · 감수</span>\n"
        '  <a href="/doctors/hong">홍길동 원장 (치과보철과 전문의)</a>\n'
        "  <time datetime=\"2026-08-07\">2026년 8월 7일</time>\n"
        "</div>\n"
        "\n"
        "<!-- ② 구조화 데이터에도 같은 사람을 적는다 -->\n"
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "MedicalWebPage",\n'
        '  "author":  { "@type": "Person", "name": "홍길동", "jobTitle": "치과보철과 전문의" },\n'
        '  "reviewedBy": { "@type": "Person", "name": "홍길동" }\n'
        "}\n"
        "</script>"
    ),
    "geo.evidence.publisher_identified": (
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "Article",\n'
        '  "publisher": {\n'
        '    "@type": "Organization",\n'
        f'    "name": "{_B}",\n'
        '    "url": "https://도메인/",\n'
        '    "logo": { "@type": "ImageObject", "url": "https://도메인/logo.png" },\n'
        '    "telephone": "+82-53-000-0000",\n'
        '    "address": {\n'
        '      "@type": "PostalAddress",\n'
        '      "streetAddress": "들안로 209, 2층",\n'
        '      "addressLocality": "대구광역시 수성구",\n'
        '      "addressCountry": "KR"\n'
        "    }\n"
        "  }\n"
        "}\n"
        "</script>"
    ),
    "geo.evidence.method_disclosed": (
        "<!-- 자체 수치를 냈으면 어떻게 셌는지 같은 페이지에 밝힌다. -->\n"
        "<h3>산출 방법</h3>\n"
        f"<p>2025년 1월~12월 {_B}에서 임플란트 식립을 받은 환자 412명을 대상으로,\n"
        "식립 12개월 후 정기 검진에서 확인한 값입니다. 검진에 오지 않은 37명은\n"
        "집계에서 제외했습니다.</p>\n"
        "\n"
        "<!-- '기간 · 대상 수 · 세는 방법 · 제외한 것' 넷이 있으면 충분하다. -->"
    ),
    # ------------------------------------------------------------------ 엔터티 명확성
    "geo.entity.organization_identified": (
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "MedicalClinic",\n'
        '  "@id": "https://도메인/#organization",\n'
        f'  "name": "{_B}",\n'
        '  "url": "https://도메인/",\n'
        '  "telephone": "+82-53-000-0000",\n'
        '  "address": {\n'
        '    "@type": "PostalAddress",\n'
        '    "streetAddress": "들안로 209, 2층",\n'
        '    "addressLocality": "대구광역시 수성구",\n'
        '    "postalCode": "42111",\n'
        '    "addressCountry": "KR"\n'
        "  },\n"
        '  "openingHours": "Mo-Fr 09:00-18:00"\n'
        "}\n"
        "</script>\n"
        "\n"
        "<!-- 일반 업종이면 @type 을 Organization / LocalBusiness / Store 로 바꾼다. -->"
    ),
    "geo.entity.stable_id_graph": (
        "<!-- 조직·페이지·글이 서로를 @id 로 가리키게 한다.\n"
        "     연결이 없으면 AI 는 같은 회사의 페이지들을 서로 다른 대상으로 본다. -->\n"
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@graph": [\n'
        "    {\n"
        '      "@type": "MedicalClinic",\n'
        '      "@id": "https://도메인/#organization",\n'
        f'      "name": "{_B}"\n'
        "    },\n"
        "    {\n"
        '      "@type": "WebPage",\n'
        '      "@id": "페이지주소#webpage",\n'
        '      "url": "페이지주소",\n'
        '      "isPartOf": { "@id": "https://도메인/#website" },\n'
        '      "about":    { "@id": "https://도메인/#organization" }\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "</script>"
    ),
    "geo.entity.sameas_profiles_present": (
        "<!-- 공식으로 운영하는 곳만 적는다. 남의 페이지나 폐쇄된 계정을 넣으면\n"
        "     AI 가 엉뚱한 정보를 우리 것으로 읽는다. -->\n"
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "MedicalClinic",\n'
        '  "@id": "https://도메인/#organization",\n'
        f'  "name": "{_B}",\n'
        '  "sameAs": [\n'
        '    "https://map.naver.com/p/entry/place/0000000000",\n'
        '    "https://www.instagram.com/계정",\n'
        '    "https://blog.naver.com/계정",\n'
        '    "https://www.youtube.com/@채널"\n'
        "  ]\n"
        "}\n"
        "</script>"
    ),
    "geo.entity.nap_consistent": (
        "<!-- 상호·주소·전화는 **한 글자도 다르지 않게** 모든 곳에서 같아야 한다.\n"
        "     홈페이지 · 네이버플레이스 · 구글 비즈니스 · 사업자등록 표기가 서로 다르면\n"
        "     AI 는 같은 업체인지 확신하지 못한다. -->\n"
        '<div itemscope itemtype="https://schema.org/MedicalClinic">\n'
        f'  <span itemprop="name">{_B}</span>\n'
        '  <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">\n'
        '    <span itemprop="streetAddress">들안로 209, 2층</span>\n'
        '    <span itemprop="addressLocality">대구광역시 수성구</span>\n'
        "  </div>\n"
        '  <span itemprop="telephone">053-000-0000</span>\n'
        "</div>\n"
        "\n"
        "<!-- 전화번호 표기(053-000-0000 / 0530000000)도 통일한다. -->"
    ),
    # ------------------------------------------------------------------ 구조화 데이터·메타
    "geo.sd.valid_syntax": (
        "<!-- JSON-LD 는 문법이 하나만 틀려도 통째로 무시된다.\n"
        "     흔한 실수: 마지막 쉼표, 홑따옴표, 주석(//), 줄바꿈이 든 문자열 -->\n"
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "MedicalClinic",\n'
        f'  "name": "{_B}",\n'
        '  "url": "https://도메인/"\n'
        "}\n"
        "</script>\n"
        "\n"
        "<!-- 붙여넣기 전에 search.google.com/test/rich-results 에서 확인한다. -->"
    ),
    "geo.sd.page_type_appropriate": (
        "<!-- 페이지가 하는 일에 맞는 타입을 쓴다. 전부 WebPage 로 두면 구분이 안 된다. -->\n"
        "\n"
        "<!-- 병원 소개    --> MedicalClinic · Dentist · Physician\n"
        "<!-- 진료·시술    --> MedicalProcedure\n"
        "<!-- 증상 설명    --> MedicalCondition\n"
        "<!-- 블로그 글    --> Article · MedicalWebPage\n"
        "<!-- 자주 묻는 질문 --> FAQPage\n"
        "<!-- 절차 안내    --> HowTo\n"
        "\n"
        '<script type="application/ld+json">\n'
        '{ "@context": "https://schema.org", "@type": "MedicalProcedure",\n'
        '  "name": "임플란트", "bodyLocation": "구강",\n'
        '  "howPerformed": "치조골에 인공 치근을 식립한 뒤 보철물을 연결합니다." }\n'
        "</script>"
    ),
    "geo.meta.title_description_descriptive": (
        "<!-- 제목과 설명은 그 페이지에만 맞는 문장이어야 한다.\n"
        "     사이트 전체에 같은 문장을 돌려 쓰면 AI 가 페이지를 구분하지 못한다. -->\n"
        "<title>임플란트 비용과 치료 기간 안내 | " + _B + "</title>\n"
        '<meta name="description"\n'
        '      content="임플란트 1개 100만원부터, 치료 기간 3~4개월. 보험 적용 조건과\n'
        '               수술 후 관리 방법을 정리했습니다.">\n'
        "\n"
        "<!-- 제목 25~35자, 설명 70~90자가 잘리지 않는다. -->"
    ),
    "geo.meta.opengraph_present": (
        "<!-- <head> 안. AI 답변과 메신저 공유가 같은 값을 읽는다. -->\n"
        '<meta property="og:type" content="article">\n'
        '<meta property="og:title" content="임플란트 비용과 치료 기간 안내">\n'
        '<meta property="og:description" content="임플란트 1개 100만원부터, 치료 기간 3~4개월.">\n'
        '<meta property="og:url" content="페이지주소">\n'
        '<meta property="og:image" content="https://도메인/공유이미지.jpg">\n'
        f'<meta property="og:site_name" content="{_B}">'
    ),
    # ------------------------------------------------------------------ 최신성·변경 신호
    "geo.fresh.dates_present": (
        "<!-- ① 화면에 보이게 — 사람이 읽는 자리 -->\n"
        '<p class="dates">\n'
        '  발행 <time datetime="2026-03-02">2026년 3월 2일</time> ·\n'
        '  수정 <time datetime="2026-08-07">2026년 8월 7일</time>\n'
        "</p>\n"
        "\n"
        "<!-- ② 구조화 데이터에도 같은 날짜를 -->\n"
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "MedicalWebPage",\n'
        '  "datePublished": "2026-03-02",\n'
        '  "dateModified": "2026-08-07"\n'
        "}\n"
        "</script>\n"
        "\n"
        "<!-- 두 날짜가 다르면 AI 는 어느 쪽도 믿지 않는다. -->"
    ),
    "geo.fresh.sitemap_lastmod_reliable": (
        "<!-- sitemap.xml — lastmod 는 **본문이 실제로 바뀐 날**만 적는다.\n"
        "     매일 오늘 날짜로 자동 갱신하면 신호가 무의미해지고, 크롤러가 무시한다. -->\n"
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        "    <loc>페이지주소</loc>\n"
        "    <lastmod>2026-08-07</lastmod>\n"
        "  </url>\n"
        "</urlset>\n"
        "\n"
        "<!-- 페이지의 dateModified 와 같은 날짜여야 한다. -->"
    ),
}


def code_example_for(check_id: str) -> str | None:
    """이 검사의 조치 코드 예시. 정답 코드가 하나로 정해지지 않는 검사는 ``None``.

    없는 것이 잘못된 것보다 낫다 — 사이트마다 답이 다른 항목에 코드를 지어내면,
    담당자는 **틀린 코드를 확신을 가지고** 붙여넣는다.
    """
    return _EXAMPLES.get(check_id)
