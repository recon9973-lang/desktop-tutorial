# 베놈 병원마케팅 플랫폼 아키텍처 (v1)

> 전수 발굴(3개 저장소 + 연결된 8개 MCP 툴) 종합. **어떤 기능을 · 어디에 붙여서 · 어떻게 분리하는가**를 정의한다.
> 이 문서는 사이트별 활용 검토의 설계 기준이다. 상태 배지: `추출`=이미 존재하나 사이트에 갇힘 / `부분` / `신규`.

## 핵심 통찰 3가지

1. **원장님 앱 ≈ 55% 이미 존재.** 진단엔진·키워드리서치·Perplexity AI실측·Search Console이 베놈 사이트 안에 이미 구축돼 있다. 신규 구축이 아니라 **추출·재포장** 문제다.
2. **재사용 엔진이 사이트마다 중복.** SEO엔진·키워드·콘텐츠파이프라인·인증·저장이 각자 구현돼 있다. **공유 플랫폼(L0)으로 추출**하면 4개 앱이 공유한다.
3. **자동화 글루가 비어 있음.** 사이트↔ERP↔원장님앱↔카카오를 잇는 오케스트레이션이 없다. **Airtable + Make**가 빠진 열쇠다.

## 5계층 구조 (위 → 아래 = 소비자 → 기반)

### L1 · 공개 사이트 (B2C / 리드) — 고객 접점
- 🏥 **베놈 사이트** `[운영]` — 마케팅·리드젠. 17페이지·3단 택소노미·무료진단v2·GrowthOps·자동발행. `desktop-tutorial`
- 💊 **당신의 영양제** `[76%]` — 소비자 추천 앱(웹+Expo). `your-supplement`

### L2 · 운영자 앱 (B2B / 사내) — 워크플로우·인텔리전스
- 🏢 **베놈 ERP** `[82%]` — 사내 워크플로우: 거래처·업무·연차·정산·보고서·원고스튜디오. 25 Prisma 모델. `marketing-agency-erp`
  - 이미지 스튜디오 ← Higgsfield / 사내채팅 ← Kakao
- 🩺 **원장님 앱** `[≈55% 재포장]` — 고객사(병원) 대상 마케팅 인텔리전스. L0의 진단·키워드·AI노출을 병원 관점으로 재포장.

### L0 · 공유 플랫폼 서비스 — 추출 대상, 모든 앱의 엔진
사이트에 흩어진 재사용 엔진을 공통 API/패키지(`venom-platform`)로 추출 → 4개 앱이 참조.

| 서비스 | 출처(추출 대상) | 동력 툴 |
|--------|----------------|---------|
| SEO 진단 엔진 (60여항목 정적채점+PSI, 재사용형 UMD) | `venom-wordpress/preview/assets/seo-engine.js` | Google PSI |
| 키워드·트렌드 인텔리전스 (검색량·연관어·자동완성) | `lib/keyword-research.js` | Naver 검색광고·데이터랩·PlayMCP |
| AI 노출 실측 (Perplexity 실측+GSC 순위+멀티AI매트릭스) | `api/insights.js`, `lib/search-console.js` | Perplexity·Search Console |
| 콘텐츠 파이프라인 (GPT생성·DALL-E·번역·의료광고검증·검수·디자인) | `lib/post-generator.js` 외 `lib/*` | OpenAI·Higgsfield |
| GrowthOps (토픽클러스터·내부링크·아웃리치CRM·SEO모니터, 테스트34) | `lib/*`, `api/growthops.js` | — |
| 인증·저장·감사 (AES암호화·이메일인증·감사로그·github-store·KV분석) | ERP + 사이트 | GitHub API·Vercel KV |

### L4 · 통합 글루 — 오케스트레이션 (빠진 열쇠)
- **Airtable** `[신규]` — 통합진단 신청 DB·CRM·마스터데이터·대시보드(인터페이스 자동생성)
- **Make** `[신규]` — 시나리오: 진단신청 → Airtable → 카카오알림 → ERP 업무 자동생성
- **메시징** `[부분]` — 카카오 알림톡·채널·사내채팅. WordPress 발행 대안채널.

### L3 · 도구 · 스킬 · 유틸 (횡단 지원)
seo-generator · seo-writing 스킬 · seo-medical-expert 스킬 · 전수검사 스킬 · 디자인 리소스 · webp(→이미지스튜디오로 흡수)

## 기능 → 사이트 → 툴 바인딩

| 기능 | 붙일 곳 | 동력(툴/엔진) | 상태 |
|------|---------|--------------|------|
| NAVER 노출점검(플레이스·블로그·카페·지식iN·뉴스·이미지·웹) | 🩺 원장님 앱 | PlayMCP search_local/blog/cafearticle/kin/news/image/webkr | 신규(툴준비완료) |
| 개원 입지분석 | 🩺 원장님 앱 | PlayMCP search_local + datalab_search | 신규 |
| 키워드 검색량·연관어 | 🩺 원장님 앱 · 사이트 진단 | Naver 검색광고 + 데이터랩 ← lib/keyword-research.js | 추출 |
| AI 내업체 노출(ChatGPT·Gemini·Claude·Perplexity) | 🩺 원장님 앱 · 🏥 사이트 진단 | Perplexity 실측 + OpenAI ← api/insights.js (Gemini·Claude 키 대기) | 부분추출 |
| 통합진단 신청 관리 | 🏥 사이트 → L4 → 🩺/🏢 | Airtable(DB) + Make(자동화) + Kakao(알림) | 신규 |
| 이미지 스튜디오 | 🏢 ERP | Higgsfield generate_image + Canva + webp(변환) | 신규(조립) |
| 원고 스튜디오 콘텐츠 | 🏢 ERP | L0 콘텐츠파이프라인(GPT·의료광고검증) + seo-writing 스킬 | 연결 |
| 사내채팅 | 🏢 ERP | Kakao + Make | 신규 |
| 법률검토·개인정보처리방침 | 🩺 원장님 앱 · 🏥 사이트 | seo-medical-expert 스킬 | 스킬존재 |
| 최저가·복용알람 | 💊 영양제 | PlayMCP Naver쇼핑 + Kakao 알림톡 | 키대기 |

## 사이트 분리 전략

- **4개 독립 배포** — 베놈사이트 · 영양제 · ERP · 원장님앱. 각자 도메인·저장소. 대상 사용자가 다름(방문자/소비자/직원/고객사).
- **L0 = 공유 플랫폼 추출** — 사이트에 박힌 엔진을 공통 API(`venom-platform`)로 분리 → 4개 앱이 참조. 중복 제거·일관성.
- **원장님앱 ≠ ERP** — ERP는 사내(직원), 원장님앱은 고객사(외부 병원). 분리하되 통합진단 신청이 L4로 양쪽에 흐른다.
- **L4가 허브** — Airtable+Make가 4개 앱·카카오를 잇는 중앙 신경계.

## 구축 로드맵 (ROI 순)

1. **P1 · L0 공유 서비스 추출 + L4 글루 세팅** `[기반]` — 진단·키워드·AI노출 엔진을 공통 API로 분리. Airtable 통합진단 베이스 + Make 시나리오 뼈대.
2. **P2 · 원장님 앱 = L0 재포장 + PlayMCP 네이버** `[최대 ROI]` — 이미 55% 존재 → 병원 관점 대시보드로 재포장. NAVER 노출/입지/키워드는 PlayMCP로 즉시.
3. **P3 · ERP 스튜디오·미배선 정리** — 이미지스튜디오(Higgsfield/Canva) 조립, 원고스튜디오 L0연결, `WorkStatusButtons` 등 미배선 배선.
4. **P4 · 영양제 프로덕션화** — 프로덕션 DB·앱 하드코딩 제거·review/price_offer 영속·쿠팡파트너스.
5. **P5 · 키 주입 → 전체 실동작** `[스위치 온]` — Vercel env + Naver/Kakao/OpenAI/Gemini/Claude 키 → 배포 초록불 + 4엔진 AI매트릭스 + 실발송.

---
*아키텍처 v1 · 2026-07-04 · 시각 아티팩트와 병행 관리. 사이트별 활용 검토가 진행되면 갱신한다.*
