---
name: seo-audit
description: >-
  홈페이지의 SEO를 Google SEO 시작 가이드 + 네이버 서치어드바이저 공식 기준으로 진단·채점·개선 처방한다.
  URL이나 HTML을 주고 "SEO 점검/진단/분석/점수", "검색 최적화 확인", "네이버/구글 SEO 검사",
  "왜 검색에 안 잡히나", "메타태그/robots/사이트맵/구조화데이터 점검", "SEO 리포트 만들어줘" 라고
  할 때 사용. 다수 홈페이지를 관리하는 콘솔에서 사이트별 SEO 상태를 표준 100점 체계로 평가할 때 적합.
---

# SEO 진단·최적화 스킬 (Google + 네이버 공식 기준)

이 스킬은 홈페이지 관리 프로그램에서 **각 사이트의 SEO 상태를 공식 가이드 기준으로 진단**하고,
점수·등급·개선 처방을 산출한다. 근거는 전부 1차 공식 문서다. 순위를 "보장"한다고 말하지 않는다.

## 언제 쓰나
- 특정 URL/도메인의 SEO 점수를 매길 때
- 검색 노출이 안 되는 원인을 진단할 때 (크롤링 차단·noindex·메타 누락 등)
- 사이트별 SEO를 표준화된 100점 체계로 비교·모니터링할 때
- SEO 개선 우선순위(무엇부터 고칠지)를 정할 때

## 근거 (1차 공식 자료만 인용)
- **Google** — SEO 시작 가이드, How Search Works, Helpful Content, AI 최적화 가이드, URL 구조, 링크 모범사례, Sitemap
- **네이버** — 서치어드바이저 SEO 가이드 (`https://searchadvisor.naver.com/guide`)
- **성능(속도)** — Google PageSpeed Insights(PSI) / Lighthouse 실측
- 프로젝트 내 상세 근거: `docs/seo-guidelines.md`
- 재사용 채점 엔진: `venom-wordpress/preview/assets/seo-engine.js` (의존성 0, 브라우저·Node 겸용)

---

## 채점 체계 (100점 만점)

기본 분석(원본 HTML 파싱, ~1–2초) = **90점**. 정밀 분석(PSI) 시 속도 10점 합산 = **100점**.
**종합 SEO 점수에서 속도(성능)는 분리**한다 — Google이 SEO와 성능을 별도 게이지로 나누기 때문.

| 카테고리 | 배점 | 측정 |
|---|---|---|
| 콘텐츠 & 메타 | 38 | HTML 파싱 |
| 기술·크롤링 | 30 | HTML + robots.txt |
| 검색 노출 강화 | 22 | HTML + robots.txt |
| 속도 최적화 | 10 | PSI(Lighthouse) 정밀 분석 |

### ① 콘텐츠 & 메타 (38)
| 항목 | 배점 | 출처 | 통과 규칙 |
|---|---|---|---|
| title 태그 | 8 | 공통 | 존재 + **단일** + 10~60자 |
| 메타 디스크립션 | 8 | 공통 | 존재 + **단일** + 50~160자 |
| H1 대표 제목 | 6 | 네이버 | **정확히 1개** |
| 이미지 ALT | 7 | 공통 | 속성 누락 ≤10% (`alt=""`·1×1 추적픽셀 제외) |
| 의미있는 링크 텍스트 | 5 | Google | "여기 클릭"·맨 URL·빈 텍스트 지양(≤20%), 이미지링크는 alt로 평가 |
| 서술형 URL | 4 | Google | 의미있는 단어, 세션ID·긴 임의ID·과다 파라미터 지양 |

### ② 기술·크롤링 (30)
| 항목 | 배점 | 출처 | 통과 규칙 |
|---|---|---|---|
| HTTPS | 6 | 공통 | SSL 적용 |
| 검색로봇 수집 허용 | 7 | 공통 | robots.txt가 Googlebot·**Yeti(네이버)**·`*` 루트 차단 안 함 (RFC 9309 그룹 파싱, Allow 우선) |
| 인덱싱 허용 | 6 | 공통 | meta robots `noindex` 미설정 |
| Canonical | 6 | 공통 | 대표 URL 지정 |
| Viewport | 4 | 공통 | 모바일 우선 인덱싱 |
| HTML lang | 4 | Google | 페이지 언어 명시 |

### ③ 검색 노출 강화 (22, 보너스성 — 감점 완화)
| 항목 | 배점 | 출처 | 통과 규칙 |
|---|---|---|---|
| 구조화 데이터 | 3 | Google | Schema.org JSON-LD (리치결과 자격, 필수 아님) |
| Open Graph | 3 | 네이버 | og:title + og:description |
| sitemap.xml 선언 | 4 | 공통 | robots.txt의 `Sitemap:` 선언 |
| 파비콘 | 2 | Google | 검색결과 아이콘 |
| robots.txt 존재 | 3 | 공통 | 수집 규칙 파일 제공 |

### ④ 속도 최적화 (10, PSI 정밀 분석)
성능 점수·텍스트 압축·이미지 최적화(WebP·지연로딩)·렌더링 차단 최소화 — Lighthouse 실측 + CrUX 현장 데이터.

---

## 진단 절차

1. **입력 수집** — 대상 URL의 HTML, `robots.txt`, HTTPS 여부. (JS 렌더링 SPA면 원본 HTML이 비어 있을 수 있음)
2. **정적 분석** — 위 ①~③ 항목을 HTML/robots에서 파싱해 채점 (90점 기준).
3. **JS 렌더링/봇 차단 감지** — 본문이 비어 있고 script가 많으면 `renderSuspect`로 판정,
   해당 항목을 "실패"가 아닌 **"정밀필요(pending)"**로 표시(거짓 실패 방지).
4. **정밀 분석(PSI, 선택)** — Google PageSpeed Insights API로 렌더링 후 재채점 + 속도 10점 합산 → 100점.
   PSI의 렌더 결과(score===1 통과)로 정적 수집이 놓친 항목을 상향 보정.
5. **등급 산정** — 90%+ 플래티넘 / 80%+ 골드 / 70%+ 실버 / 60%+ 브론즈 / 그 미만 개선필요.
6. **개선 처방** — 미통과 항목을 **배점 높은 순**으로 정렬해 "무엇을·왜·어떻게" 제시.

프로젝트에 엔진이 있으면 직접 호출:
```js
const SEOEngine = require('./venom-wordpress/preview/assets/seo-engine.js');
const result = SEOEngine.analyze({ url, html, robots, isHttps });   // Node면 { doc } 도 전달(jsdom)
// PSI JSON이 있으면:  const merged = SEOEngine.mergePSI(result, psiJson);
// result.total / result.max / result.grade / result.categories[].items
```

## 의도적으로 감점하지 않는 것 (Google이 "중요치 않다"고 명시)
- 헤딩 순서·개수 (접근성 목적일 뿐, 순위 무관)
- 콘텐츠 단어 수 ("마법의 글자 수 없음")
- 키워드 밀도 / meta keywords (키워드 스터핑은 스팸 정책 위반)
- 구조화 데이터 필수화 (리치결과용 권장일 뿐)
- llms.txt / AI 전용 마크업 (Google 미사용)
- 도메인 키워드·TLD·서브도메인 vs 서브디렉터리 (영향 미미)

## 정직성 원칙 (Google 서드파티 도구 가이드)
- 이 진단은 **공식 가이드 기반 참고용 휴리스틱**이며 검색 순위를 **보장하지 않는다.**
- 1차 데이터는 [Google Search Console](https://search.google.com/search-console) · [네이버 서치어드바이저](https://searchadvisor.naver.com)에서 확인 권장.

---

## 출력 형식 (기본)
```
🔎 SEO 진단: {도메인}
종합 {total}/{max}점 · {등급}

[카테고리별]  콘텐츠&메타 xx/38 · 기술·크롤링 xx/30 · 검색노출 xx/22 (· 속도 xx/10)

⚠️ 개선 우선순위 (배점 높은 순)
1. [항목] (+N점) — 현재 상태 → 조치 방법
2. ...

✅ 통과 항목: N개 / ⚠️ 미흡: N개 / 통과율 NN%
※ 참고용 진단 · 순위 보장 아님 · 1차 데이터는 Search Console 확인
```

---

## 개선 시 추가로 챙기면 좋은 것 (권장 확장)
- **AEO/GEO(생성형 AI 검색) 신호**: FAQPage·Article·MedicalClinic 등 Schema.org JSON-LD, 즉답형 리드,
  인용 가능한 권위 콘텐츠 — 이 부분은 `ai-content-writer` 스킬과 짝으로 쓰면 강력하다.
- **Core Web Vitals**: LCP/CLS/INP를 CrUX 현장 데이터로 모니터링.
- **다중 사이트 트렌드**: 관리 콘솔에서 도메인별 점수를 일자별로 저장해 추세 그래프화
  (프로젝트의 `api/cron-seo-monitor.js` 패턴 참고).
- **국가별 대응**: 네이버(Yeti) + 구글(Googlebot)을 항상 함께 점검. 한국 사이트는 네이버 노출이 핵심.
