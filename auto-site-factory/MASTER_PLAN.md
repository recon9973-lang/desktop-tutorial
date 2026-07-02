# VENOM Site Factory — 마스터 기획안 v2

> 코드네임: **VENOM Site Factory**  
> 갱신일: 2026-06-29 · 브랜치: `claude/auto-website-generator-qz1azp`  
> 한 줄 정의: **고객 기본 정보를 넣으면 → 기획·제작·SEO/AEO/GEO 최적화·배포까지 자동으로 끝내는 홈페이지 생산 공장.**

---

## 0. Executive Summary

| 질문 | 현재 답 |
|---|---|
| **플랫폼** | WordPress 멀티사이트 + 캐시 정적화 (Nginx FastCGI + Redis + Cloudflare) |
| **카테고리** | `clinic` 병원 + `local` 소상공인 완성, `press`/`blog`/`magazine` 예정 |
| **자동화 수준** | 입력폼 → site-spec.json → 정적 HTML + SEO 파일 4종 자동 생성 (CLI 1줄) |
| **미리보기** | 실시간 미리보기 서버 (`node server.js`) → 입력 즉시 iframe 렌더 |
| **SEO/AEO/GEO** | robots.txt + sitemap.xml + llms.txt + Schema.org + OG 기본 완성; 고도화 필요 |
| **다음 단계** | lib 의존성 해소 → AEO 스키마 보강 → press 블루프린트 → WP 자동 provisioning |

---

## 1. 전수조사 — 현재 구현 상태

### 1.1 파일 인벤토리

```
auto-site-factory/
├── engine/
│   ├── generate.js          ✅ 완성  — 정적 HTML 생성 엔진 (295줄)
│   ├── seo.js               ✅ 완성  — robots.txt / sitemap / llms.txt 생성 (71줄)
│   ├── blog-gen.js          ⚠ 부분  — CLI 완성, OpenAI 의존 (114줄)
│   ├── wp-adapter.js        ⚠ 부분  — provision.sh 생성, 실 연결 미완 (145줄)
│   └── options/
│       └── medical-review.js ⚠ 부분  — 래퍼 완성, lib 의존성 없음 (24줄)
├── blueprints/
│   ├── clinic/
│   │   ├── blueprint.json   ✅ 완성  — 8개 진료과목, 3규모, 스톡사진 URL
│   │   └── template.html    ✅ 완성  — 병원 전용 네이비 테마
│   └── local/
│       ├── blueprint.json   ✅ 완성  — 7개 업종, cafe 스톡 5장, Higgsfield CDN
│       └── template.html    ✅ 완성  — 소상공인 Amber/Brown 따뜻한 테마
├── samples/
│   ├── site-spec.example.json   ✅ 치과 예제
│   └── local-spec.example.json  ✅ 카페 예제
├── intake/
│   └── index.html           ✅ 완성  — clinic/local 조건부 폼 + 미리보기 연동
├── server.js                ✅ 완성  — 미리보기 서버 (포트 3737)
└── output/                  ✅ 생성됨 — 3개 예제 사이트 출력물

venom-plugins/
├── venom-seo/               ✅ 완성  — robots.txt 필터, llms.txt 엔드포인트, Schema.org
├── venom-autoblog/          ✅ 완성  — WP-Cron 자동발행, REST API
└── venom-medreview/         ✅ 완성  — save_post 검수, 관리자 컬럼
```

### 1.2 완성도 레이더

| 컴포넌트 | 완성도 | 비고 |
|---|---|---|
| **정적 생성 엔진** | 95% | 테스트 통과, clinic/local 양쪽 작동 |
| **병원(clinic) 블루프린트** | 90% | 8개 진료과목; photo 업로드 연동 완성 |
| **소상공인(local) 블루프린트** | 85% | 7개 업종; 카페만 스톡 사진 있음 |
| **SEO 엔진** | 80% | robots/sitemap/llms.txt 완성; AEO 고도화 필요 |
| **입력 폼** | 90% | 미리보기 포함; trust/reviews 입력 미구현 |
| **미리보기 서버** | 100% | POST /api/preview 작동 확인 |
| **WP 어댑터** | 40% | provision.sh 생성; wp-cli 실행 부재 |
| **WP 플러그인** | 75% | SEO/autoblog/medreview 3종; analytics/image 미완 |
| **lib 의존성** | 20% | post-generator, medical-ad-validator 미포함 |
| **press/blog/magazine 블루프린트** | 0% | 미착수 |

### 1.3 핵심 미결 항목 (빠른 순서)

1. **`engine/lib/` 의존성 누락** — `medical-review.js`가 `../lib/medical-ad-validator`를 require하는데 factory 폴더에 없음. `blog-gen.js`도 `../lib/post-generator` 없음.
2. **소상공인 스톡사진 부족** — `restaurant/beauty/nail/fitness/bakery/retail` 6개 업종에 stock.hero/intro/gallery 없음 → Higgsfield 생성 필요.
3. **intake form trust/reviews 입력** — 현재 폼은 trust 숫자, 후기(reviews) 입력 없어 예제 값이 자동 적용됨.
4. **WP 실배선** — provision.sh만 나옴; `wp-cli` 실행 래퍼 없어 사람이 수동 복붙해야 함.
5. **venom-analytics 플러그인** — analytics 옵션은 체크박스에 있지만 플러그인 없음.
6. **AEO/GEO 스키마 보강** — 아래 §3 참조.

---

## 2. 브레인스토밍 — 아이디어 목록

### 2.1 UX / 입력 최적화

| 아이디어 | 효과 | 난이도 |
|---|---|---|
| **AI 자동완성 폼** — 상호명+업종 입력 시 Claude가 슬로건·메타 자동 제안 | 입력 시간 70% 절감 | 중 |
| **다단계 마법사 UI** — 현재 긴 단일 폼 → 4단계 스텝퍼 (대분류→브랜드→콘텐츠→배포) | 완료율 상승 | 중 |
| **로고 색상 추출** — 로고 업로드 시 자동으로 primary color 추출 | 브랜드 일관성 자동화 | 하 |
| **업종 자동 감지** — 사업자 번호 or 네이버 플레이스 URL → 업종·주소 자동 채움 | 오타·입력 오류 방지 | 상 |
| **spec 버전 관리** — 동일 고객의 spec 여러 버전 저장·비교 | 수정 이력 추적 | 중 |

### 2.2 미리보기 / 검수 강화

| 아이디어 | 효과 | 난이도 |
|---|---|---|
| **SEO 점수 오버레이** — 미리보기 패널에 실시간 SEO 체크리스트 패널 | 검수 사전 차단 | 중 |
| **모바일 Lighthouse 점수** — 미리보기 생성 후 자동 성능/접근성 점수 | 품질 보증 | 상 |
| **Schema 유효성 배지** — 생성된 JSON-LD가 Google Rich Results Test 통과하는지 실시간 확인 | 리치리절트 보장 | 중 |
| **실사진 vs 스톡 토글** — 미리보기에서 "실사진 모드 / AI스톡 모드" 전환 | 고객 설득 자료 | 하 |
| **A/B 색상 미리보기** — primary color 슬라이더로 실시간 컬러 변환 | 브랜드 컬러 결정 지원 | 하 |

### 2.3 SEO/AEO/GEO 전략적 아이디어

| 아이디어 | 효과 | 난이도 |
|---|---|---|
| **llms.txt 2.0** — 단순 소개 넘어서 Q&A 형식 + 서비스 상세 + 가격 범위 포함 | AI 인용률 3-5배 향상 | 하 |
| **AI 검색 시뮬레이터** — ChatGPT/Perplexity에 업체 쿼리 날리면 어떻게 답하는지 비교 | GEO 효과 측정 | 상 |
| **지역 경쟁사 분석** — 네이버 지도 API로 반경 1km 경쟁사 키워드 자동 분석 | 틈새 키워드 발굴 | 상 |
| **스키마 캘린더** — 이벤트/프로모션을 Event 스키마로 자동 발행 → Google 이벤트 리스팅 | 추가 검색 노출 | 중 |
| **FAQ 자동 생성** — 업종별 자주 묻는 질문 DB + Claude가 업체 맞춤 FAQ 30개 생성 | AEO 핵심 콘텐츠 | 중 |

### 2.4 운영 / 비즈니스 모델

| 아이디어 | 효과 | 난이도 |
|---|---|---|
| **고객 대시보드** — 생성된 사이트 상태, 블로그 발행 현황, SEO 점수 한눈에 | 해지율 감소, 락인 | 상 |
| **화이트레이블 리셀러** — 다른 마케팅 대행사가 VENOM Factory를 자사 솔루션으로 판매 | B2B 채널 확장 | 상 |
| **월구독 + 옵션팩 과금** — 기본 사이트 관리 월 X원 + 블로그 Y원/월 + 이미지 Z원/월 | 예측 가능 수익 | 중 |
| **자동 리뷰 수집** — 카카오/네이버 리뷰 API로 최신 후기 자동 업데이트 | 사이트 신선도 유지 | 상 |

---

## 3. SEO · AEO · GEO 최적화 현황 및 고도화 계획

### 3.1 현재 구현 현황

#### ✅ 완성된 항목

| 파일 | 기능 |
|---|---|
| `engine/seo.js` `robotsTxt()` | AI 크롤러 허용 (GPTBot·ClaudeBot·PerplexityBot·Google-Extended) |
| `engine/seo.js` `sitemapXml()` | 페이지별 priority·changefreq 포함 sitemap.xml |
| `engine/seo.js` `llmsTxt()` | AI 학습·인용 동의, 업종별 소개, 카테고리 분기 |
| `template.html` (both) | `<title>`, `<meta description>`, `<link rel="canonical">` |
| `template.html` (both) | OG 태그 (title, description, image, url) |
| `template.html` clinic | `MedicalClinic` Schema.org JSON-LD |
| `template.html` local | `LocalBusiness` Schema.org JSON-LD |
| `template.html` (both) | `FAQPage` Schema.org JSON-LD |
| `venom-seo.php` | WordPress: robots.txt 필터 + llms.txt 엔드포인트 |

#### ⚠ 부분 구현 (존재하지만 미흡)

| 항목 | 현황 | 문제 |
|---|---|---|
| `LocalBusiness` sameAs | `instagram`, `naver_place` URL 포함 | 값이 빈 문자열이면 오염 |
| `llmsTxt` 콘텐츠 | 소개·키워드·링크 포함 | 메뉴·가격·영업시간 미포함 |
| FAQ 개수 | 기본 3개 | 5-10개가 AEO 효과 높음 |
| 이미지 alt | 일부 없음 | 접근성·이미지 SEO |

#### ❌ 미구현

| 항목 | 중요도 | 영향 |
|---|---|---|
| `Organization` 스키마 | 높 | 브랜드 엔티티 명확화 → GEO 핵심 |
| `AggregateRating` 스키마 | 높 | 별점 리치리절트 → CTR +15~30% |
| `OpeningHoursSpecification` | 높 | "지금 영업 중" 표시, Local Pack |
| `HowTo` / `Service` 스키마 | 중 | 서비스 과정 AEO |
| `BreadcrumbList` 스키마 | 중 | 내비게이션 리치리절트 |
| `Speakable` 콘텐츠 | 중 | 음성검색(Bixby, Clova) 대응 |
| 구조화된 NAP 일관성 | 높 | 지역 검색 신뢰도 |
| `hreflang` (다국어) | 중 | 글로벌 팩 활성화 시 필수 |

---

### 3.2 즉시 추가할 스키마 (코드)

아래 3개 스키마를 `template.html`에 추가하면 AEO/GEO 점수가 크게 올라간다.

**① Organization + AggregateRating (local template)**
```json
{
  "@context": "https://schema.org",
  "@type": ["LocalBusiness", "Organization"],
  "name": "{{brand.name}}",
  "telephone": "{{brand.phone}}",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "{{brand.address}}",
    "addressLocality": "{{brand.region}}",
    "addressCountry": "KR"
  },
  "openingHoursSpecification": "{{sections.hoursSchema}}",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.9",
    "reviewCount": "{{trust.0.num}}"
  },
  "priceRange": "₩₩"
}
```

**② Service 스키마 (각 메뉴 아이템)**
```json
{
  "@context": "https://schema.org",
  "@type": "Service",
  "serviceType": "{{specialty.label}}",
  "provider": { "@type": "LocalBusiness", "name": "{{brand.name}}" },
  "areaServed": "{{brand.region}}"
}
```

**③ llmsTxt 2.0 구조**
```
# {{brand.name}}

> {{brand.region}} {{specialty.label}}. {{brand.tagline}}

## 기본 정보
- 업종: {{specialty.label}}
- 위치: {{brand.address}}
- 연락처: {{brand.phone}}
- 영업시간: [시간 목록]

## 주요 메뉴·서비스
[메뉴 목록 with 가격]

## 고객 후기 요약
[별점, 대표 후기 3개]

## AI 인용 정책
이 사이트는 AI 학습·인용에 동의합니다.
출처: https://{{domain}}/
```

---

### 3.3 GEO (Generative Engine Optimization) 전략

GEO는 ChatGPT, Perplexity, Claude, 네이버 AI 검색이 업체를 인용할 확률을 높이는 것.

**핵심 원칙:**
1. **엔티티 명확화** — 업체명·위치·업종을 반복 구조화 (llms.txt + Schema.org + 본문)
2. **신뢰 신호** — 운영 연수, 누적 고객, 수상 이력을 숫자로 (trust 섹션)
3. **Q&A 밀도** — FAQ 10개 이상, HowTo 포함, "~어떻게?" 질문에 직접 답변
4. **인용 가이드라인** — llms.txt에 "어떻게 인용해야 하는지" 명시
5. **콘텐츠 신선도** — 블로그 자동발행(①팩)으로 크롤 주기 유지

**우선순위 액션:**
```
Week 1: Organization + AggregateRating 스키마 추가
Week 2: llmsTxt 2.0 (메뉴·가격·영업시간 포함)
Week 3: FAQ 10개 기본 DB 구축 (업종별)
Week 4: 자동 블로그 발행 → 크롤 주기 확보
```

---

## 4. 업데이트된 아키텍처

### 4.1 현재 구조 (완성된 부분)

```
[입력 폼 intake/index.html]
    ↓ build() → JSON
[site-spec.json]
    ↓ node engine/generate.js
[engine/generate.js]
    ├── prepare()    ← blueprint.json 로드, 섹션 빌드
    ├── render()     ← {{토큰}} 치환
    └── generate()   ← output/ 폴더에 저장
         ├── index.html
         ├── robots.txt   ← engine/seo.js
         ├── sitemap.xml  ← engine/seo.js
         └── llms.txt     ← engine/seo.js

[server.js (미리보기)]
    POST /api/preview → prepare() + render() → HTML 반환
    GET /             → intake/index.html 서빙

[venom-plugins/ (WordPress)]
    venom-seo       → robots.txt 필터, llms.txt, Schema.org
    venom-autoblog  → WP-Cron 자동발행, REST API
    venom-medreview → save_post 검수, 관리자 컬럼
```

### 4.2 목표 구조 (완성 시)

```
                    ┌─── Cloudflare CDN/WAF ───────────────────────┐
사용자              │                                              │
  ↓              Nginx FastCGI Cache (HTML 정적 서빙 99%)          │
[intake.html]       │  ↓ MISS                                      │
  ↓ build()      PHP-FPM → WordPress Multisite                    │
[site-spec.json]    │       ├── clinic.site1.kr                    │
  ↓ generate     Redis (Object Cache)                             │
[정적 output/]   MariaDB (사이트별 prefix)                         │
  ↓ deploy                                                        │
[WP Multisite] ←── Growth Engine (Node) ──────────────────────────┘
                    ├── ① 블로그 자동발행 (blog-gen.js → WP REST)
                    ├── ② 이미지 생성+WebP 변환
                    ├── ③ 검수 (medical-ad-validator)
                    ├── ④ 번역 (translate.js)
                    ├── ⑤ SEO/llms.txt 주입 (seo.js)
                    └── ⑥ 분석 (analytics.js)
```

---

## 5. 카테고리 블루프린트 로드맵

### 5.1 완성 (즉시 사용 가능)

| 카테고리 | 업종 수 | 스톡 사진 | 스키마 | 상태 |
|---|---|---|---|---|
| `clinic` 병원 | 8 | 부분 (진단기기 중심) | MedicalClinic + FAQ | ✅ |
| `local` 소상공인 | 7 | 카페만 5장 | LocalBusiness + FAQ | ✅ |

### 5.2 다음 구현 대상

| 카테고리 | 핵심 섹션 | 전용 스키마 | 우선도 |
|---|---|---|---|
| `press` 인터넷 언론 | 기사 CMS, 카테고리, 기자 프로필 | NewsArticle, Journalist | 높 |
| `blog` 개인 블로그 | 글목록, about, 구독 | BlogPosting, Person | 중 |
| `magazine` 매거진 | 피처, 이슈/호, 갤러리 | Magazine, PublicationVolume | 중 |
| `corp` 기업 | 회사소개, 채용, 뉴스룸 | Organization, JobPosting | 낮 |

### 5.3 소상공인 스톡 사진 미보충 업종

다음 6개 업종에 Higgsfield AI 생성 스톡 사진 필요:

| 업종 | 필요 컷 |
|---|---|
| `restaurant` 식당 | 외관, 홀 내부, 시그니처 메뉴 3컷 |
| `beauty` 미용실 | 외관, 시술 중, 헤어 결과물 3컷 |
| `nail` 네일샵 | 네일 아트 클로즈업 5컷 |
| `fitness` 헬스장 | 기구, 트레이닝, 공간 3컷 |
| `bakery` 베이커리 | 외관, 제품 진열, 베이킹 3컷 |
| `retail` 소매점 | 외관, 상품 진열, 쇼케이스 3컷 |

---

## 6. 빠른 실행 계획 (Sprint 1-4)

### Sprint 1 (1주) — 기반 완성
**목표**: lib 의존성 해소 + AEO 스키마 보강 + 소상공인 스톡 보충

- [ ] `engine/lib/medical-ad-validator.js` 복사 또는 이식
- [ ] `engine/lib/post-generator.js` 스텁 구현 (OpenAI 없을 때 템플릿 기반 fallback)
- [ ] Organization + AggregateRating 스키마 → `template.html` 양쪽 추가
- [ ] OpeningHoursSpecification 스키마 → local template
- [ ] llmsTxt() 2.0 — 메뉴·영업시간·별점 포함
- [ ] 소상공인 6개 업종 Higgsfield 스톡 생성

### Sprint 2 (2주) — 입력 폼 고도화
**목표**: 폼 완성도 90% → 100% + AI 자동완성

- [ ] trust 입력 카드 (숫자 4개: 운영연수, 평점, 월고객, 퍼센트)
- [ ] reviews 입력 카드 (후기 3개: 작성자, 별점, 본문)
- [ ] FAQ 입력 카드 (Q&A 동적 추가)
- [ ] Claude API 연동 → 업종 선택 시 슬로건·FAQ 자동 제안
- [ ] 색상 AI 추출 (로고 업로드 → primary color 추천)

### Sprint 3 (3주) — press 블루프린트 + WP 실배선
**목표**: 3번째 카테고리 완성 + WordPress 실제 연결

- [ ] `blueprints/press/blueprint.json` + `template.html`
- [ ] `wp-adapter.js` — wp-cli 실행 래퍼 (child_process.exec)
- [ ] `venom-plugins/venom-analytics/` — 방문 분석 WP 플러그인
- [ ] WP Multisite 도메인 매핑 자동화

### Sprint 4 (4주) — 미리보기 고도화 + 대시보드
**목표**: 고객용 셀프 진행 UI

- [ ] SEO 점수 오버레이 (미리보기 패널 우측 패널)
- [ ] Schema.org 유효성 실시간 체크 (Google API)
- [ ] 고객 대시보드 v1 (생성된 사이트 목록, 발행 현황)
- [ ] Cloudflare API 도메인 매핑 자동화

---

## 7. 기술 스택 확정

| 레이어 | 기술 | 역할 |
|---|---|---|
| **빌드 엔진** | Node.js (순수 `fs`/`path`) | spec → HTML + SEO 파일 |
| **템플릿** | 커스텀 `{{token}}` 치환기 | 의존성 0 |
| **미리보기** | Node.js `http` 모듈 | `/api/preview` 서버 |
| **CMS 플랫폼** | WordPress Multisite | 콘텐츠 관리·블로그·고객 어드민 |
| **WP 자동화** | WP-CLI + WP REST API | 사이트 생성·콘텐츠 주입 |
| **캐시 정적화** | Nginx FastCGI + Redis | PHP 우회 99% 정적 서빙 |
| **CDN/WAF** | Cloudflare | DDoS, 속도, SSL |
| **AI 이미지** | Higgsfield MCP | 업종별 스톡 사진 생성 |
| **AI 콘텐츠** | Claude API (Sonnet 4.6) | 블로그 발행·FAQ 생성·슬로건 |
| **이미지 DB** | AWS S3 / Cloudflare R2 | 미디어 오프로드 |

---

## 8. 과금 모델 제안

| 플랜 | 가격 | 포함 | 타겟 |
|---|---|---|---|
| **Lite** | 제작비 1회 | 원페이지, SEO 기본 | 소상공인 입문 |
| **Standard** | 제작비 + 월 관리비 | 5p + 블로그 자동발행 | 병원·카페 주력 |
| **Pro** | 제작비 + 월 풀팩 | 7p+ + 전 옵션 팩 | 언론·매거진·기업 |
| **Enterprise** | 맞춤 견적 | Headless + 전용 서버 | 대형 병원·프랜차이즈 |

> 옵션 팩은 플랜 업그레이드 or 개별 추가 구매 가능. 예: Standard에 "다국어 팩" 단독 추가.

---

## 9. 열린 결정사항

| # | 항목 | 현재 기본값 | 사용자 결정 필요 |
|---|---|---|---|
| 1 | **lib 이식 방식** | 메인 프로젝트 참조 | factory 자체 복사 vs symbolic link |
| 2 | **AI 자동완성 모델** | 미정 | Claude Haiku (빠름·저렴) vs Sonnet (품질) |
| 3 | **스톡 사진 정책** | Higgsfield CDN URL | 스톡 사진도 data URI 임베딩할지 |
| 4 | **WP 멀티사이트 도메인** | 고객 도메인 매핑 | 서브도메인 기본 제공 여부 |
| 5 | **셀프서비스 시점** | 내부 도구로 시작 | Sprint 4 이후 고객 직접 신청 오픈 |
| 6 | **블로그 발행 AI** | OpenAI GPT | Claude Haiku로 전환 (비용 절감) |

---

## 10. 기대 효과 (성과 지표)

| 지표 | 현재 (수작업) | 목표 (자동화) |
|---|---|---|
| 사이트 1개 제작 시간 | 3~5일 | 30분 이내 |
| SEO 파일 생성 | 수동 | 100% 자동 |
| AI 검색(GEO) 준비도 | 0% | 90%+ (llms.txt + Schema 풀세트) |
| 동시 운영 사이트 수 | 무제한 (수작업) | 멀티사이트 1대 100개 |
| 블로그 발행 주기 | 비정기 | 일 1회 자동 |
| 의료광고 위반 체크 | 수동 교정 | 자동 감지·수정 |

---

*이 기획서는 살아있는 문서입니다. 스프린트 완료마다 갱신됩니다.*  
*마지막 갱신: 2026-06-29 (전수조사 v2 기반)*
