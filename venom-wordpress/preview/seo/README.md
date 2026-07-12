# VENOM SEO 진단기 — 완전체 (한 곳)

> 내부 SEO/GEO 진단의 **단일 소스**. 엔진·규칙·지식근거가 여기 다 모여 있습니다.
> "지식 근거가 어디 있지?" 할 필요 없이 **이 폴더 하나**를 보면 됩니다.

## 📁 구성 (이 폴더가 전부)
| 파일 | 역할 |
|---|---|
| `seo-engine.js` | **진단 엔진**(의존성 0). HTML+robots 파싱 → 100점·5등급·카테고리별 채점. 브라우저/Node 공용. |
| `seo-rules.json` | **규칙+지식 근거**. 규칙 23개, 각 규칙이 Google 공식문서 번호(`grounds`)로 인용됨 + 처방(`prescription`). |
| `README.md` | 이 문서 — 전체 지도. |

## 🧠 지식 근거 (203문서)
규칙의 근거는 **`/google_seo_guide/`**(Google 공식 SEO 문서 203종) + **마스터 인덱스** `google_seo_guide/00_지식맵_MASTER_INDEX.md`.
`seo-rules.json`의 각 규칙 `grounds:[번호]`가 그 문서를 가리킵니다. (예: `[171]`=유용·신뢰 콘텐츠, `[145]`=기사 스키마, `[121]`=LocalBusiness)

## 📊 채점 카테고리 (v1.6)
| 카테고리 | 배점 | 내용 | 근거 |
|---|---|---|---|
| 📝 콘텐츠 & 메타 | 42 | title·description·H1·ALT·링크텍스트·URL | Google SEO 기본 |
| ⚙️ 기술·크롤링 | 42 | HTTPS·robots·인덱싱·canonical·viewport·lang | 기술 요구사항 |
| 🔍 검색 노출 강화 | 16 | 구조화데이터·OG·sitemap·파비콘·robots.txt | 리치결과·수집 |
| 🩺 **신뢰·전문성(E-E-A-T)** | 16 | **저자·의료진 · 조직/병원정보 · 발행수정일 · 연락처 · 엔티티(sameAs)** | **[171][185][121][145]** |
| ✍️ **콘텐츠 최적화** | 15 | **포커스 키워드 배치(제목·본문·메타) · 소제목 구조 · 문단 가독성 · 스캔(목록·표)** | **[89][39][143]** |
| ⚡ 속도(CWV) | 별도 | LCP·CLS·INP — PSI 실측 시 | [4][63] |

> **포커스 키워드**: `analyze({ ..., keyword: '임플란트' })` 로 대상 키워드를 주면 제목·본문·메타 **배치(위치)**를 평가.
> 키워드를 안 주면 키워드 항목은 자동 제외되고 구조·가독성만 채점. (Google 금지사항인 **키워드 밀도/스터핑은 채점 안 함**)

> 점수는 `total/max` 백분율로 정규화(카테고리 추가/제외에 자동 대응). 속도는 종합점수에서 분리(Google 방식).

## ✅ E-E-A-T 보완 (2026 최신 문서 반영)
의료(YMYL) 사이트라 신뢰 신호를 이식했습니다. **틀린 통설은 배제**:
- ❌ FAQ 리치결과 스키마 → **2026년 지원 중단**([189/190])이라 채점 안 함
- ❌ "콘텐츠 단어 수" → **순위요인 아님**([89][171])
- ❌ llms.txt·청킹·AI 전용 재작성 → **불필요**([39])
- ✅ 대신 저자·조직·최신성·연락처·sameAs = 실제 Google이 중시하는 신뢰/엔티티 신호

## ⚖️ Rank Math(WP 진단기) 대비 — 이번에 닫은 공백 / 로드맵
| 항목 | 우리 엔진 | 상태 |
|---|---|---|
| 포커스 키워드·가독성·본문 최적화 | ✍️ **콘텐츠 최적화 카테고리로 이식 완료(v1.7)** | ✅ 닫음 |
| 신뢰(E-E-A-T)·GEO 신호 | 🩺 신뢰 카테고리(v1.6) — 오히려 우위(의료 특화) | ✅ 우위 |
| 결정성·근거·이식성 | 무료·의존성0·203문서 인용·어디든 임베드 | ✅ 우위 |
| sitemap/schema/canonical | **점검만** (Rank Math는 자동 생성·관리) | ⏳ 로드맵(생성은 사이트/CMS 쪽 작업) |
| CWV 실측 | PSI 붙이면 정확 | ✅(PSI 연동 시) |
| GSC/색인 연동 | 없음 | ⏳ 로드맵(GSC API 연동 필요) |
| 렌더링 HTML 확보 | 봇차단·SPA 시 pending 처리 | ⚠️ 수집단(seo-proxy)에서 렌더링 강화 필요 |
| 실제 자동수정 | 진단·처방까지(수정은 별도) | ⏳ 로드맵(ERP/CMS 쓰기권한 필요) |

> 정직 원칙: **정적 분석기로 할 수 있는 것(진단·처방·키워드·구조)은 다 했고**, 쓰기권한·외부 API가 필요한 것(자동 sitemap/schema 생성, GSC 연동, 인에디터 코칭)은 로드맵으로 명시.

## 🔌 사용법
```js
// 브라우저
const r = SEOEngine.analyze({ url, html, robots, isHttps });
el.innerHTML = SEOEngine.renderInfographic(r);
const merged = SEOEngine.mergePSI(r, psiJson);   // 정밀(속도) 후

// Node (+jsdom)
const doc = new (require('jsdom').JSDOM)(html).window.document;
SEOEngine.analyze({ url, html, robots, isHttps, doc });
```
로드 경로(사이트): `<script src="/seo/seo-engine.js?v=1.6.0">` — 절대경로(중첩 라우트 안전).

## 🔗 관련(진단 생태계)
- 룰 기반(무료·결정적): **이 엔진** — 기술·콘텐츠·신뢰
- AI 실측(유료·토큰): `api/insights.js`(AEO 매트릭스: Perplexity·Claude·Gemini·GPT), `api/seo-proxy.js`(PSI·지식그래프·네이버키워드=무료)
- 자동 모니터: `api/cron-seo-monitor.js`(이 엔진 사용)
