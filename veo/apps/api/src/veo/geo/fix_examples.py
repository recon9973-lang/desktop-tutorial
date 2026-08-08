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
        "<h2>[환자가 실제로 묻는 질문을 그대로]</h2>\n"
        "<p>[한 문장으로 결론부터]. [이어서 근거나 조건 한두 문장].\n"
        "[이럴 때는 예외다 — 예외가 있으면 여기서 밝힌다].</p>\n"
        "\n"
        "<!-- 첫 문단 안에 '무엇이 · 얼마나 · 언제까지 · 예외는' 이 들어가면 좋다.\n"
        "     **내용은 반드시 의료진이 씁니다.** VEO 는 자리와 순서만 알려줍니다 —\n"
        "     의학적 사실을 진단 도구가 채워 주면 그것이 그대로 환자에게 나갑니다. -->"
    ),
    "geo.extract.passage_self_contained": (
        "<!-- 나쁜 예 — '위에서 말한' 이 있으면 그 문단만 떼어냈을 때 뜻이 끊긴다 -->\n"
        "<p>위에서 말한 방법으로 관리하시면 됩니다.</p>\n"
        "\n"
        "<!-- 좋은 예 — 주어와 대상을 문단 안에서 다시 밝힌다 -->\n"
        f"<p>{_B}에서는 [무엇을] [언제] [어떻게 하라고] 안내합니다.\n"
        "[피해야 할 것]은 [이유] 때문에 피하십시오.</p>\n"
        "\n"
        "<!-- 요령은 **주어와 대상을 문단 안에서 다시 밝히는 것** 하나다.\n"
        "     내용은 의료진이 씁니다 — 진단 도구가 의학적 조언을 채워 주면\n"
        "     그것이 그대로 환자에게 나갑니다. -->"
    ),
    "geo.extract.heading_structure_semantic": (
        "<!-- 제목은 '질문 하나 = 제목 하나' 로 나눈다. 글자 크기 때문에 쓰지 않는다. -->\n"
        "<h1>[시술·진료명]</h1>\n"
        "  <h2>[환자가 묻는 질문 1]</h2>\n"
        "  <h2>[환자가 묻는 질문 2]</h2>\n"
        "    <h3>[그 질문의 하위 갈래]</h3>\n"
        "  <h2>[환자가 묻는 질문 3]</h2>\n"
        "\n"
        "<!-- h1 은 한 장에 하나. h2 를 건너뛰고 h3 로 가지 않는다. -->"
    ),
    "geo.extract.tables_lists_machine_readable": (
        "<!-- 비교·수치는 문장에 풀어 쓰지 말고 표로. AI 가 값을 그대로 읽어 간다. -->\n"
        "<table>\n"
        "  <caption>[무엇을 비교하는 표인지]</caption>\n"
        "  <thead>\n"
        "    <tr><th>[항목]</th><th>[값1]</th><th>[값2]</th></tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        "    <tr><td>[종류]</td><td>[값]</td><td>[값]</td></tr>\n"
        "    <tr><td>[종류]</td><td>[값]</td><td>[값]</td></tr>\n"
        "  </tbody>\n"
        "</table>\n"
        "\n"
        "<!-- 이미지로 만든 표는 읽히지 않는다. 반드시 글자로 된 표여야 한다.\n"
        "     **값은 병원이 채웁니다.** 특히 비급여 진료비는 의료법이 게시 방법을\n"
        "     정하고 있으므로, 진단 도구가 임의로 넣은 금액을 그대로 올리면 안 됩니다. -->"
    ),
    # ------------------------------------------------------------------ 근거·출처 투명성
    "geo.evidence.claims_have_sources": (
        "<!-- 검증이 필요한 주장 바로 옆에 출처를 붙인다. 글 맨 끝에 몰아 두지 않는다. -->\n"
        "<p>[검증이 필요한 주장을 한 문장으로]\n"
        '(<a href="https://출처주소" rel="nofollow">[발표한 곳], [연도]</a>).</p>\n'
        "\n"
        "<!-- 출처에는 '누가 · 언제' 가 들어가야 한다. '전문가에 따르면' 은 출처가 아니다.\n"
        "     **주장과 출처는 반드시 실제로 확인한 것이어야 합니다.** 여기에 예시 숫자와\n"
        "     학회 이름을 넣어 두면, 그것이 그대로 병원 홈페이지에 올라가 없는 연구를\n"
        "     실재하는 학회가 발표한 것처럼 만듭니다. 그래서 비워 둡니다. -->"
    ),
    "geo.evidence.author_identified": (
        "<!-- ① 화면에 보이게 -->\n"
        '<div class="byline">\n'
        "  <span>작성 · 감수</span>\n"
        '  <a href="/doctors/[식별자]">[이름] [직함] ([전문과목])</a>\n'
        "  <time datetime=\"[YYYY-MM-DD]\">[감수한 날]</time>\n"
        "</div>\n"
        "\n"
        "<!-- ② 구조화 데이터에도 같은 사람을 적는다 -->\n"
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "MedicalWebPage",\n'
        '  "author":  { "@type": "Person", "name": "[이름]", "jobTitle": "[전문과목]" },\n'
        '  "reviewedBy": { "@type": "Person", "name": "[감수자 이름]" }\n'
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
        '    "telephone": "[+82-지역번호-국번-번호]",\n'
        '    "address": {\n'
        '      "@type": "PostalAddress",\n'
        '      "streetAddress": "[도로명 주소 · 상세주소]",\n'
        '      "addressLocality": "[시·도 시·군·구]",\n'
        '      "addressCountry": "KR"\n'
        "    }\n"
        "  }\n"
        "}\n"
        "</script>"
    ),
    "geo.evidence.method_disclosed": (
        "<!-- 자체 수치를 냈으면 어떻게 셌는지 같은 페이지에 밝힌다. -->\n"
        "<h3>산출 방법</h3>\n"
        f"<p>[기간]에 {_B}에서 [무엇]을 받은 [대상] [N]명을 대상으로,\n"
        "[언제·어떻게] 확인한 값입니다. [제외한 대상]은 집계에서 제외했습니다.</p>\n"
        "\n"
        "<!-- '기간 · 대상 수 · 세는 방법 · 제외한 것' 넷이 있으면 충분하다.\n"
        "     **실제로 센 것만 적습니다.** 숫자를 예시로라도 넣어 두면 하지 않은 조사를\n"
        "     한 것처럼 발표하게 됩니다. -->"
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
        '  "telephone": "[+82-지역번호-국번-번호]",\n'
        '  "address": {\n'
        '    "@type": "PostalAddress",\n'
        '    "streetAddress": "[도로명 주소 · 상세주소]",\n'
        '    "addressLocality": "[시·도 시·군·구]",\n'
        '    "postalCode": "[우편번호]",\n'
        '    "addressCountry": "KR"\n'
        "  },\n"
        '  "openingHours": "[Mo-Fr 09:00-18:00 형식으로 실제 진료시간]"\n'
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
        '    <span itemprop="streetAddress">[도로명 주소 · 상세주소]</span>\n'
        '    <span itemprop="addressLocality">[시·도 시·군·구]</span>\n'
        "  </div>\n"
        '  <span itemprop="telephone">[대표번호]</span>\n'
        "</div>\n"
        "\n"
        "<!-- 전화번호 표기 방식(하이픈 유무)도 모든 채널에서 통일한다. -->"
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
        '  "name": "[시술명]", "bodyLocation": "[부위]",\n'
        '  "howPerformed": "[어떻게 하는 시술인지 — 의료진이 씁니다]" }\n'
        "</script>"
    ),
    "geo.meta.title_description_descriptive": (
        "<!-- 제목과 설명은 그 페이지에만 맞는 문장이어야 한다.\n"
        "     사이트 전체에 같은 문장을 돌려 쓰면 AI 가 페이지를 구분하지 못한다. -->\n"
        "<title>[이 페이지가 답하는 것] | " + _B + "</title>\n"
        '<meta name="description"\n'
        '      content="[이 페이지에서만 알 수 있는 내용을 한두 문장으로.\n'
        '               다른 페이지에 그대로 복사되지 않는 문장이어야 합니다]">\n'
        "\n"
        "<!-- 제목 25~35자, 설명 70~90자가 잘리지 않는다. -->"
    ),
    "geo.meta.opengraph_present": (
        "<!-- <head> 안. AI 답변과 메신저 공유가 같은 값을 읽는다. -->\n"
        '<meta property="og:type" content="article">\n'
        '<meta property="og:title" content="[이 페이지가 답하는 것]">\n'
        '<meta property="og:description" content="[한 문장 요약]">\n'
        '<meta property="og:url" content="페이지주소">\n'
        '<meta property="og:image" content="https://도메인/공유이미지.jpg">\n'
        f'<meta property="og:site_name" content="{_B}">'
    ),
    # ------------------------------------------------------------------ 최신성·변경 신호
    "geo.fresh.dates_present": (
        "<!-- ① 화면에 보이게 — 사람이 읽는 자리 -->\n"
        '<p class="dates">\n'
        '  발행 <time datetime="[YYYY-MM-DD]">[발행일]</time> ·\n'
        '  수정 <time datetime="[YYYY-MM-DD]">[마지막으로 실제 고친 날]</time>\n'
        "</p>\n"
        "\n"
        "<!-- ② 구조화 데이터에도 같은 날짜를 -->\n"
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "MedicalWebPage",\n'
        '  "datePublished": "[YYYY-MM-DD 발행일]",\n'
        '  "dateModified": "[YYYY-MM-DD 실제로 고친 날]"\n'
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
        "    <lastmod>[YYYY-MM-DD 실제로 고친 날]</lastmod>\n"
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
