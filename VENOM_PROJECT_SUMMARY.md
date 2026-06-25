# 병원마케팅 베놈 — 프로젝트 인수인계 문서

> 새 대화에서 이 파일을 먼저 읽고 작업을 이어가세요.  
> 마지막 업데이트: 2026-06-25

---

## 1. 프로젝트 개요

- **서비스명**: 병원마케팅 베놈
- **법인명**: 주식회사 베놈
- **대표**: 김보형
- **사업자등록번호**: 291-86-02777
- **연락처**: 1661-4142
- **주소**: 대구광역시 수성구 용학로25길54, 4층
- **카카오채널**: https://pf.kakao.com/_jxjxdcxj
- **배포 URL**: https://desktop-tutorial-chi-peach.vercel.app/
- **Git 저장소**: recon9973-lang/desktop-tutorial
- **개발 브랜치**: `claude/nice-cray-94p4hx`

---

## 2. 파일 구조

```
desktop-tutorial/
├── venom-wordpress/preview/
│   ├── index.html          ← 메인 SPA (6000+ 줄)
│   └── admin.html          ← 관리자 대시보드
├── api/
│   └── kw-proxy.js         ← 네이버 키워드 검색량 API 프록시
├── robots.txt              ← AI 크롤러 허용 (GPTBot, ClaudeBot, PerplexityBot)
├── sitemap.xml             ← 검색엔진 제출용
├── vercel.json             ← Vercel 라우팅·헤더 설정
└── VENOM_PROJECT_SUMMARY.md ← 이 파일
```

---

## 3. 기술 스택

- **프론트엔드**: Vanilla HTML/CSS/JS (SPA, 단일 파일)
- **배포**: Vercel (serverless functions)
- **외부 API**: 네이버 검색광고 API (키워드 검색량)
- **CSS 변수**:
  - `--p: #533afd` (primary purple)
  - `--bd: #1c1e54` (dark blue)
  - `--ink: #0d253d` (text)
  - `--soft: #f6f9fc` (light bg)
  - `--border: #e3e8ee`

---

## 4. SPA 라우팅 구조

### 핵심 함수

```javascript
sp(id)   // 최상위 페이지 전환 → pg-{id} div를 보여줌
ld(cat)  // 병원마케팅 카테고리 로드 → pages 객체에서 HTML 가져와 pg-detail에 삽입
loadBlogPost(id)  // 블로그 포스트 렌더링
switchTool(tab)   // 도구탭 전환 (seo/geo/kw)
```

### 페이지 목록 (pg-{id})

| ID | 설명 |
|---|---|
| `home` | 메인 랜딩 |
| `hospital` | 병원 홈페이지 제작 |
| `ai` | AI마케팅 허브 |
| `geo` | GEO 생성AI 최적화 전용 페이지 |
| `aeo` | AEO 답변엔진 최적화 전용 페이지 |
| `seo` | SEO 검색엔진 최적화 전용 페이지 |
| `services` | 온라인마케팅 서비스 |
| `blog` | 블로그 목록 |
| `blog-post` | 블로그 상세 (동적) |
| `tools` | SEO 점수 체크/GEO 점수 체크/키워드 검색량 체크 |
| `contact` | 상담 신청 |
| `about` | 회사 소개 |
| `seo-dict` | SEO 용어 사전 |
| `detail` | 병원마케팅 카테고리 상세 (동적) |
| `hosp_mkt` | 병원마케팅 카테고리 overview |

---

## 5. 콘텐츠 데이터 객체

### `pages` 객체 — 병원마케팅 카테고리

```javascript
// ld(cat) 함수로 로드 → pg-detail에 삽입
dental        치과 마케팅 (필수 조건 5가지, FAQ, 3단계 모델, 사례 3개, 레퍼런스)
implant       임플란트 마케팅 ← NEW (필수 조건 5가지, 위험표현표, FAQ, 3단계 모델, 사례)
ortho_dental  교정 마케팅 ← NEW (필수 조건 5가지, 환자유형별 콘텐츠, FAQ, 3단계 모델)
skin          피부과 마케팅 (필수 조건 5가지, AI통계, 3단계 모델, 사례 3개)
ortho         정형외과 마케팅
oriental      한의원 마케팅 (필수 조건 5가지, 3단계 모델, 사례 3개)
plastic       성형외과 마케팅
geo           GEO 최적화 (AI마케팅)
aeo           AEO 최적화 (AI마케팅)
seo           SEO 최적화 (AI마케팅)
naegwa        내과 마케팅
angwa         안과 마케팅
shimui        의료광고심의
medical_device 의료기기 마케팅
```

### CSS 클래스 (dc- prefix)

```css
.dc-case        카드형 사례 박스
.dc-case-label  사례 레이블 (과목·지역)
.dc-result      성과 배지 묶음
.dc-refs        레퍼런스 링크 박스
.dc-refs-list   레퍼런스 링크 목록
.dc-table       데이터 테이블
.dc-table-wrap  테이블 수평 스크롤 래퍼
.dc-cta-box     하단 상담 신청 박스
```

### `blogPosts` 객체 — 블로그 포스트

```javascript
geo1          GEO 기초 가이드
dental1       치과 마케팅 사례
seo1          SEO 전략
skin1         피부과 마케팅
geo2          GEO 고급 전략 (Perplexity)
strategy1     병원 마케팅 예산 전략
dental2       치과 신환 유치
aeo1          AEO 가이드
local_incheon 인천 지역마케팅
local_busan   부산 지역마케팅
local_daegu   대구 지역마케팅
local_daejeon 대전 지역마케팅
local_gwangju 광주 지역마케팅
local_ulsan   울산 지역마케팅
```

---

## 6. 네이버 키워드 API 설정

### api/kw-proxy.js

- 환경변수 (Vercel 대시보드에서 설정):
  - `NAVER_CUSTOMER_ID` — 고객 ID
  - `NAVER_ACCESS_LICENSE` — API 키
  - `NAVER_SECRET_KEY` — 시크릿 키 (base64 디코딩 없이 직접 사용)
- HMAC-SHA256 서명: `timestamp + '.' + accessLicense`
- 403 오류 시: Vercel 환경변수에서 `NAVER_SECRET_KEY` 재입력 필요

---

## 7. 도구 탭 (pg-tools 또는 홈 내장)

| 탭 | 설명 |
|---|---|
| SEO 점수 체크 | URL 입력 → 100점 기준 SEO 진단 |
| GEO 점수 체크 | 키워드 입력 → 5개 AI 플랫폼 노출 체크 + 체크리스트 |
| 키워드 검색량 체크 | 키워드 → PC/모바일 분리 검색량 + 연관 키워드 테이블 |

---

## 8. 관리자 페이지 (admin.html)

- 경로: `/venom-wordpress/preview/admin.html`
- 기능:
  - 방문자 실시간 로그 (시뮬레이션)
  - 블로그 포스트 작성/발행 (AI 초안 생성 버튼 포함)
  - 키워드 분석
  - 유입 출처 분석
  - SEO 점수 대시보드
  - 데일리 카드뉴스 업로드 UI
  - 사이트 설정

> **주의**: 관리자 블로그 작성 시 `addBlogPostFromAdmin(data)` 함수 호출 → index.html의 blogPosts에 추가됨 (새로고침 시 초기화 — localStorage 연동 미완성)

---

## 9. SEO 설정 현황

### 완료된 항목

- [x] `<title>` 태그 최적화
- [x] meta description, keywords
- [x] OG tags (og:title, og:description, og:image)
- [x] Twitter Card
- [x] Canonical URL
- [x] robots.txt (AI 크롤러 허용 포함)
- [x] sitemap.xml
- [x] FAQPage Schema JSON-LD — pg-geo, pg-aeo, pg-seo 각각
- [x] LocalBusiness Schema JSON-LD (주소 대구로 수정 완료)
- [x] BreadcrumbList Schema
- [x] E-E-A-T 콘텐츠 구성
- [x] 내부 링크 구조 (치과↔의료광고심의, 치과↔GEO/AEO/SEO, 피부과↔AEO 등)

### 미완료 항목

- [ ] OG 이미지 실제 파일 (`/og-image.jpg` 없음, 1200×630px 필요)
- [ ] 이미지 alt 태그 전수 점검
- [ ] YouTube Shorts 실제 영상 ID 교체 (현재 `dQw4w9WgXcQ` 더미값)

---

## 10. AI마케팅 구조 추천 (SEO 관점)

**결론: GEO/AEO/SEO로 분리하는 현재 구조가 옳습니다.**

- "병원 GEO 최적화", "병원 AEO 최적화", "의료 SEO"는 각각 독립적인 검색 수요가 있음
- 하나로 합치면 키워드 경쟁력 희석
- AI 검색(ChatGPT, Gemini)에서도 각 개념을 별도 질문으로 물어보는 경향
- 현재처럼 GEO·AEO·SEO 각각 독립 페이지 + JSON-LD FAQPage가 최적

---

## 11. 네비게이션 구조

```
상단 GNB
├── 병원마케팅 (클릭: sp('hosp_mkt'), 드롭다운)
│   ├── 치과 → ld('dental')
│   ├── 피부과 → ld('skin')
│   ├── 정형외과 → ld('ortho')
│   ├── 한의원 → ld('oriental')
│   ├── 성형외과 → ld('plastic')
│   ├── 내과 → ld('naegwa')
│   ├── 안과 → ld('angwa')
│   ├── 의료광고심의 → ld('shimui')
│   └── 의료기기마케팅 → ld('medical_device')
├── AI마케팅 (클릭: sp('ai'), 드롭다운)
│   ├── GEO → sp('geo')
│   ├── AEO → sp('aeo')
│   └── SEO → sp('seo')
├── 온라인마케팅 → sp('services')
├── 블로그 → sp('blog')
├── 홈페이지 제작 → sp('hospital')
└── 상담신청 → 카카오 채널

푸터
├── 회사 소개 → sp('about')
├── SEO 용어 사전 → sp('seo-dict')
├── 마케팅 블로그 → sp('blog')
├── 상담신청 → sp('contact')
└── 관리자 → admin.html (새 탭)
```

---

## 12. CTA 버튼 현황 (정리 완료)

- **상담신청** 버튼: `onclick="sp('contact')"` 또는 폼으로 이동
- **카카오상담** 버튼: `href="https://pf.kakao.com/_jxjxdcxj"` target="_blank"
- ~~"무료 진단", "무료상담신청", "카카오무료진단"~~ → 전부 "카카오상담" 또는 "상담신청"으로 변경 완료

---

## 13. 온라인마케팅 서비스 (pg-services) — 완성된 항목

- 네이버 마케팅 (플레이스/블로그/키워드광고/카페지식인)
- 인스타그램·SNS
- 유튜브 마케팅
- **파워링크** — 네이버 검색 최상단 텍스트 광고
- **파워컨텐츠** — 블로그·카페 상단 정보성 광고
- **브랜드검색** — 병원명 전용 영역
- **플레이스 광고** — 지도 상단 노출
- **언론보도·PR** — E-E-A-T 백링크
- **브랜드마케팅** — 닥터 브랜딩
- 채널 선택 가이드 테이블 (예산별)
- 진료과목별 광고 조합 추천 표 (★★★)

---

## 14. 남은 작업

### 높은 우선순위

1. **YouTube Shorts 실제 영상 ID** — 현재 `dQw4w9WgXcQ` 더미. 베놈 실제 유튜브 채널 영상 ID로 교체 필요
2. **블로그 포스트 풀텍스트** — 현재 일부 포스트만 상세 내용 있음. 관리자 페이지에서 추가 작성 권장
3. **OG 이미지** — `/og-image.jpg` 1200×630px 실제 파일 필요
4. ~~**관리자 블로그 localStorage**~~ — **완료**: localStorage 연동 완성. 작성/초안저장/수정/삭제 모두 새로고침 후에도 유지됨.
5. ~~**임플란트/교정 마케팅**~~ — **완료**: `implant`, `ortho_dental` 독립 페이지 생성. 드롭다운·사이드바 링크 추가.

### 낮은 우선순위

6. **데일리 카드뉴스 실제 API** — Make.com 또는 n8n 자동화 연동
7. **이미지 alt 태그** — 전수 점검
8. **네이버 API 403** — 실제 키 유효한지 테스트

---

## 15. 참고 사이트 (레퍼런스)

- https://venomad.com — 베놈 광고대행사
- https://next-t.co.kr — 넥스트티 마케팅
- https://ezloan.io/wiki — SEO 사례

---

## 16. 배포 방법

```bash
git add .
git commit -m "feat: ..."
git push -u origin claude/nice-cray-94p4hx

# Vercel은 main 브랜치 자동 배포
# PR 머지 후 main에서 자동 배포됨
```

---

## 17. 주요 Git 커밋 이력

| 커밋 | 내용 |
|---|---|
| `29f6ef4` | feat: add localStorage persistence for blog posts in admin page |
| `fab360a` | feat: add implant and orthodontics marketing pages with full content |
| `bc83f23` | feat: add rich content guides, fix CTAs, search ad details, SEO |
| `8859a18` | feat: enhance GEO checker and keyword tool |
| `b5f27f4` | feat: add detailed case studies and reference links |
| `782b534` | feat: add SEO dictionary nav link, fix admin path |
| `a098850` | feat: add company page, SEO dictionary, fix footer company info |

---

## 18. 새 대화에서 이어받기

새 Claude 세션에서 이 파일을 읽은 후:

1. `git checkout claude/nice-cray-94p4hx` 확인
2. 위 "남은 작업" 목록부터 진행
3. 파일이 크므로 (6000+ 줄) 전체를 읽지 말고 `Grep`으로 필요한 섹션만 찾아서 수정

> **핵심 패턴**: 새 섹션 추가 시 `dc-cta-box` 마커 기준으로 before/after 삽입
