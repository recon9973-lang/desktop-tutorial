# VENOM GrowthOps — 통합 검색 성장 시스템 기획서

> 코드네임: **VENOM GrowthOps** (작업 시 별칭 `growthops`)
> 작성일: 2026-06-30 · 작성: 시니어 개발 세션
> 대상 저장소: `recon9973-lang/desktop-tutorial` · 개발 브랜치: `claude/pbn-backlink-system-mf8r3o`

---

## 0. 이 문서의 출발점 — 방향 전환에 대한 기록

최초 요청은 "PBN(Private Blog Network) 자동 백링크 시스템"이었다. PBN은 **한 주체가 통제하는 다수 도메인을, 서로 독립적인 사이트가 자발적으로 추천하는 것처럼 위장**해 검색 랭킹을 조작하는 기법으로, Google Search Essentials의 **링크 스팸(link spam) 정책 정면 위반**이다. 적발 시 머니사이트까지 함께 수동 조치·색인 제외(de-index)되며, 자동화로 패턴이 균일할수록 SpamBrain 등 탐지가 쉬워진다. 따라서 PBN 자동화는 구축하지 않는다.

대신 **근본 목표(검색 유입·도메인 권위 성장)를 적법한 화이트햇 방식으로 달성·시스템화**한다. 이 방식은 패널티 리스크 없이 복리로 누적되고, 베놈이 이미 보유한 자산과 자연스럽게 결합된다.

---

## 1. 기존 자산 인벤토리 (재사용 대상)

베놈은 이미 상당한 자동화 파이프라인을 보유. 신규 모듈은 **이 자산 위에 얹는다**(중복 구현 금지).

### 1.1 콘텐츠 생성 파이프라인
| 모듈 | 역할 |
|---|---|
| `lib/post-generator.js` | GPT 기반 포스트 본문·메타·JSON-LD(Article) 생성 |
| `lib/image-generator.js` | DALL·E `b64_json` → `sharp` WebP 변환 → GitHub 저장 (**OG/이미지 변환 자산**) |
| `lib/infographics.js` | 인포그래픽 생성 |
| `lib/translate.js` | 발행 글 영문 번역 (en 채널) |
| `lib/content-validator.js` | 인코딩 깨짐·구분자 잔존·빈태그·환각 전화번호 정리 |
| `lib/medical-ad-validator.js` | 의료광고법 검증 |
| `lib/keyword-research.js` | 네이버/구글 자동완성·검색광고 연관키워드·검색량 |
| `lib/post-designer.js` | 포스트 디자인 |
| `lib/sitemap-builder.js` | 발행 시 `sitemap.xml` 자동 갱신 |
| `lib/github-store.js` | GitHub API로 JSON/포스트/이미지 저장 (`savePost`, `savePostEn`, `appendLog`, `getPosts`) |
| `lib/openai-client.js` | OpenAI 호출 래퍼 |

### 1.2 API / 자동화 (Vercel serverless)
| 엔드포인트 | 역할 |
|---|---|
| `api/cron-daily-posts.js` | 매일 자동발행 크론 (스케줄·카테고리·키워드·지역 기반) |
| `api/generate-post.js` / `api/publish-post.js` | 수동 생성·발행·삭제 |
| `api/posting-settings.js` | 발행 설정 |
| `api/analytics.js` | 자체 방문자 분석 — **Vercel KV(Upstash Redis)** 기반, 일별·채널별 집계 + SEO 점수 리더보드 |
| `api/insights.js` | 네이버 데이터랩 트렌드 / 검색 경쟁 / AEO(Perplexity) / 키워드도구 |
| `api/seo-proxy.js` | Google KG 엔티티 / PageSpeed Insights(PSI) / 페이지+robots 수집 / 네이버 키워드 (SSRF 방어 내장) |
| `api/health.js` | 헬스/진단 |
| `api/store.js` | 범용 저장 |

### 1.3 프론트
- `venom-wordpress/preview/` = Vercel 웹루트 (SPA `index.html`, 관리자 `admin.html`)
- 콘텐츠 데이터: `content/blog-posts.json`, `blog-posts-en.json`, `posting-log.json`, `posting-settings.json`, `settings.json`
- 디자인 토큰: `--p:#533afd` / `--bd:#1c1e54` / `--ink:#0d253d` / `--soft:#f6f9fc` / `--border:#e3e8ee` / `--r12 --r16`

### 1.4 인프라 제약 (중요)
- **Vercel Hobby = 서버리스 함수 12개 한도.** 현재 `api/`에 11개. → **신규 API는 기존 파일에 `?type=` 라우팅으로 합치거나, 1개 통합 함수로 묶는다.** (이미 `seo-proxy`, `insights`가 이 패턴)
- 영속 저장소 2종: **GitHub(콘텐츠·설정 JSON, git 이력)** + **Vercel KV/Upstash(카운터·시계열·세션성 데이터)**. 신규 데이터도 이 둘만 사용.
- KST(Asia/Seoul) 기준 날짜 경계 통일.

---

## 2. 브레인스토밍 — 무엇을, 왜

베놈의 사업은 병원/의료 로컬 마케팅이다. 검색 성장의 병목은 보통 **(a) 충분한 양질 콘텐츠 (b) 사이트 내부 권위 흐름 (c) 성과 가시성 (d) 외부 인용/언급 확보**다. 4개 모듈이 각각을 담당한다.

```
        ┌─────────────────────────────────────────────────────────┐
        │                 VENOM GrowthOps                          │
        │                                                          │
  (a)   │  M1. 콘텐츠 자동화 강화   ─┐                              │
        │      (기존 파이프라인 +    │                              │
        │       토픽 클러스터 설계)  │                              │
        │                            ▼                             │
  (b)   │  M2. 내부링크 최적화 ──► 발행 글 그래프 ──► 권위 흐름     │
        │                            │                             │
  (c)   │  M3. SEO 모니터링 대시보드 ◄ 순위·인덱싱·CWV·백링크헬스   │
        │                            │                             │
  (d)   │  M4. 아웃리치 CRM ─► 게스트포스팅·디지털PR·제휴(적법)     │
        └─────────────────────────────────────────────────────────┘
                         관리자(admin.html)에서 통합 운영
```

### 핵심 설계 원칙
1. **신뢰(E-E-A-T) 우선** — 모든 자동화는 "사람이 검수 가능한 초안"을 만들고, 발행 결정은 운영자가. 대량 무검수 발행 금지.
2. **기존 자산 재사용** — 새 LLM 호출/이미지 변환은 기존 `lib/*` 함수 호출로.
3. **함수 한도 절약** — 신규 엔드포인트는 통합 라우팅.
4. **점진적 가치** — 모듈별로 독립 배포 가능. 한 모듈만 켜도 의미 있음.
5. **측정 가능** — 모든 액션은 대시보드에서 효과를 본다.

---

## 3. 모듈별 상세 기획

### M1. 콘텐츠 자동화 강화 (기존 파이프라인 + 토픽 클러스터)
**문제**: 현재 자동발행은 키워드 나열식. 검색 권위는 **필러(Pillar)–클러스터(Cluster)** 구조에서 복리로 쌓인다.
**할 일**:
- `lib/topic-cluster.js` (신규): 진료과목·지역을 입력하면 1개 필러 주제 + N개 클러스터 하위주제를 `keyword-research.js`의 실데이터로 설계.
- `cron-daily-posts.js`에 "클러스터 모드" 추가 — 무작위 키워드 대신 미완성 클러스터의 빈칸을 우선 채움.
- 산출물 저장: `content/clusters.json` (필러↔클러스터↔발행글 매핑).
**재사용**: `keyword-research`, `post-generator`, `image-generator`, `medical-ad-validator`, `github-store`.

### M2. 내부링크 최적화 엔진 ⭐ (1차 개발 대상)
**문제**: 발행 글이 늘수록 서로 연결 안 된 "고아 글"이 생김. 내부링크는 **합법적·고효과** SEO 지렛대.
**할 일**:
- `lib/internal-linker.js` (신규):
  - 입력: `blog-posts.json` 전체 + `clusters.json`
  - 각 글의 제목·키워드·카테고리로 **관련도 점수** 산출(키워드 교집합 + 카테고리 + 클러스터 동일성 가중).
  - 각 글마다 상위 N개 "추천 내부링크" + 자연스러운 앵커텍스트 제안.
  - **고아 글 탐지**(인바운드 내부링크 0건) 리포트.
  - 옵션: 본문 HTML에 "관련 글" 블록 자동 삽입(운영자 승인형).
- 발행 직후(`cron`/`publish-post`)와 온디맨드(관리자 버튼) 둘 다에서 호출.
**제약**: 앵커텍스트 과최적화 금지(동일 정확매치 앵커 반복 X) — 다양화 규칙 내장.

### M3. SEO 모니터링 대시보드 ⭐ (2차 개발 대상)
**문제**: 성과가 안 보이면 개선 루프가 안 돈다. 현재 `analytics`(방문자)·`insights`(트렌드)는 있으나 **순위/인덱싱/페이지속도/내부링크 헬스 통합 뷰**가 없음.
**할 일**:
- `api/seo-monitor.js` (신규 통합 함수, `?type=` 라우팅):
  - `type=indexing` — 발행 URL의 sitemap 등록·인덱싱 추정 상태
  - `type=cwv` — 핵심 페이지 PageSpeed Insights(기존 `seo-proxy` PSI 재사용) 점수 시계열(KV 저장)
  - `type=linkhealth` — `internal-linker` 결과 요약(고아 글 수, 평균 내부링크 수)
  - `type=visibility` — `insights`의 AEO/검색 노출 신호 집계
- 데이터는 KV에 일/주 단위 스냅샷 저장 → 추세 그래프.
- 관리자 대시보드에 **"SEO 모니터" 탭** 신설(카드 + 라인차트, 의존성 없는 경량 SVG 차트).
**원칙**: 외부 유료 SEO API 없이, 보유 중인 Google PSI/네이버/자체 데이터로 구성. (필요 시 Search Console API는 후속 옵션)

### M4. 적법 아웃리치 CRM (3차 개발 대상)
**문제**: 외부 권위(백링크·언급)는 PBN이 아니라 **실제 매체·파트너·게스트포스팅·디지털 PR**로 얻는다. 이 활동을 관리할 도구가 없음.
**할 일**:
- 데이터: `content/outreach.json` (GitHub 저장) — 연락처(매체/블로그/협회), 상태(리드→컨택→응답→게재→유지), 제안 유형(게스트포스팅/PR/제휴/인터뷰), 메모, 다음 액션일.
- `api/outreach.js` (신규 통합 함수): CRUD + 상태 전이 + 리마인더 목록.
- 관리자 대시보드 **"아웃리치" 탭**: 칸반/리스트, 상태별 필터, "오늘 할 일".
- 템플릿: 정중한 제안 메일 초안 생성(기존 OpenAI 래퍼 재사용). **대량 스팸 발송 기능은 넣지 않음** — 1:1 관계 관리 도구.
**경계**: 링크 구매/교환 자동화 X. "관계·제안·게재 추적"만.

---

## 4. 데이터 모델 (신규)

```
content/clusters.json      # M1: { clusters: [{ id, pillar, category, region, subtopics:[{kw, postId|null, status}] }] }
content/outreach.json      # M4: { contacts: [{ id, name, site, type, status, owner, nextAt, notes, history:[] }] }
KV: seo:cwv:{url}:{ymd}     # M3: PSI 점수 스냅샷
KV: seo:snap:{ymd}         # M3: 일별 통합 스냅샷(고아글 수, 발행 수, 인덱싱 추정 등)
```
기존 `blog-posts.json` / `posting-log.json` 스키마는 변경하지 않고, 내부링크/클러스터는 별도 파일로 매핑(비파괴적).

## 5. API 설계 (함수 한도 준수)

신규 서버리스 함수는 **최대 2개**만 추가(현재 11/12):
- `api/seo-monitor.js` — M3 (`?type=indexing|cwv|linkhealth|visibility`)
- `api/outreach.js` — M4 (`?action=list|get|upsert|delete|remind`)
- M1·M2 로직은 **함수 추가 없이** 기존 `cron-daily-posts.js`·`generate-post.js`·`publish-post.js` 흐름과 `lib/*`에 통합. 관리자 온디맨드 트리거는 기존 `store.js`/`generate-post.js`에 액션 추가로 흡수.

> 12개 한도가 빠듯하면: `analytics`+`usage-stats` 통합, 또는 `contact`를 `store`로 흡수해 슬롯 확보.

## 6. 보안·컴플라이언스 가드레일
- 의료광고법 검증(`medical-ad-validator`)은 **모든 발행 경로에서 필수 통과**.
- 내부링크 앵커 다양화·과최적화 방지 규칙.
- 아웃리치는 동의/수신거부 존중, 대량 발송 미구현.
- SSRF 방어(`seo-proxy` 패턴) 신규 URL 입력에도 적용.
- 시크릿은 전부 Vercel 환경변수(코드·커밋에 노출 금지).

## 7. 개발 로드맵 (점진 배포)

| 단계 | 모듈 | 산출물 | 상태 |
|---|---|---|---|
| 1 | M2 내부링크 엔진 | `lib/internal-linker.js` + 테스트8 + `scripts/internal-links-report.js` | ✅ 완료 |
| 2 | M3 모니터링 | `api/growthops.js?module=linkhealth\|snapshot` + 콘솔 "SEO 모니터" 탭 | ✅ 완료 |
| 3 | M4 아웃리치 CRM | `api/growthops.js?module=outreach` + `lib/outreach.js` + 테스트15 + "아웃리치" 탭 | ✅ 완료 |
| 4 | M1 토픽 클러스터 | `lib/topic-cluster.js` + cron 클러스터 모드 | ⏳ 후속 |
| 5 | 통합·QA | 발행 플로우 관련글 자동주입, PSI 연결, admin 내비 링크 | ⏳ 후속 |

> M3·M4는 함수 한도(12/12)를 지키기 위해 단일 `api/growthops.js`로 통합했다(기획 당시 분리 계획에서 변경). 콘솔은 `admin.html` 수정 위험을 피해 독립 페이지 `/growthops.html`로 제공한다.

각 단계는 독립 커밋·배포. M2를 먼저 하는 이유: 외부 의존성 0, 기존 데이터만으로 즉시 효과, 다른 모듈(M3 linkhealth)의 입력이 됨.

## 8. 성공 지표 (KPI)
- 고아 글 비율 ↓ (목표 0%), 글당 평균 내부링크 수 ↑
- 핵심 페이지 PSI(모바일) 점수 추세 ↑
- 클러스터 완성도(빈칸/전체) ↑
- 아웃리치 게재 건수·획득 인용 수 (수동 기록)
- 자연 검색 유입(자체 analytics 채널=naver/google) 추세 ↑

---

### 부록 A. 네이밍
최초 음성 입력의 "오토 Anthropication…"은 받아쓰기 오류로 보임(추정: *오토 옵티마이제이션 / Auto Optimization*). 본 시스템은 **VENOM GrowthOps**로 명명하되, 원하시면 변경 가능.
