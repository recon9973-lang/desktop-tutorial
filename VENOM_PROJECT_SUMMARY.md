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
│   ├── index.html          ← 메인 SPA (5000+ 줄)
│   └── admin.html          ← 관리자 대시보드
├── api/
│   └── kw-proxy.js         ← 네이버 키워드 검색량 API 프록시
├── vercel.json             ← Vercel 라우팅 설정
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
| `tools` | SEO/GEO/키워드 도구 |
| `contact` | 상담 신청 |
| `about` | 회사 소개 |
| `seo-dict` | SEO 용어 사전 |
| `detail` | 병원마케팅 카테고리 상세 (동적) |

---

## 5. 콘텐츠 데이터 객체

### `pages` 객체 — 병원마케팅 카테고리

```javascript
// ld(cat) 함수로 로드
dental        치과 마케팅
skin          피부과 마케팅
ortho         정형외과 마케팅
oriental      한의원 마케팅
plastic       성형외과 마케팅
geo           GEO 최적화 (AI마케팅)
aeo           AEO 최적화 (AI마케팅)
seo           SEO 최적화 (AI마케팅)
naegwa        내과 마케팅
angwa         안과 마케팅
shimui        의료광고심의
medical_device 의료기기 마케팅
```

### `blogPosts` 객체 — 블로그 포스트

```javascript
geo1          GEO 기초 가이드
dental1       치과 마케팅 사례
seo1          SEO 전략
skin1         피부과 마케팅
geo2          GEO 고급 전략
strategy1     병원 마케팅 전략
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

## 7. 관리자 페이지 (admin.html)

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

## 8. SEO 설정 현황

### 완료된 항목

- [x] `<title>` 태그 최적화
- [x] meta description, keywords
- [x] OG tags (og:title, og:description, og:image)
- [x] Twitter Card
- [x] Canonical URL
- [x] robots.txt (Vercel 서빙)
- [x] FAQPage Schema JSON-LD — pg-geo, pg-aeo, pg-seo 각각
- [x] LocalBusiness Schema JSON-LD
- [x] BreadcrumbList Schema
- [x] E-E-A-T 콘텐츠 구성

### 미완료 항목

- [ ] OG 이미지 실제 파일 (`/og-image.jpg` 없음)
- [ ] 이미지 alt 태그 전수 점검
- [ ] sitemap.xml 생성
- [ ] robots.txt 파일

---

## 9. 네비게이션 구조

```
상단 GNB
├── 병원마케팅 (드롭다운)
│   ├── 치과 → ld('dental')
│   ├── 피부과 → ld('skin')
│   ├── 정형외과 → ld('ortho')
│   ├── 한의원 → ld('oriental')
│   ├── 성형외과 → ld('plastic')
│   ├── 내과 → ld('naegwa')
│   ├── 안과 → ld('angwa')
│   ├── 의료광고심의 → ld('shimui')
│   └── 의료기기마케팅 → ld('medical_device')
├── AI마케팅 (드롭다운)
│   ├── GEO → sp('geo')
│   ├── AEO → sp('aeo')
│   └── SEO → sp('seo')
├── 온라인마케팅 → sp('services')
├── 병원홈페이지 → sp('hospital')
├── 블로그 → sp('blog')
└── 무료상담 → sp('contact')

푸터
├── 회사 소개 → sp('about')
├── 연혁 & 팀 → sp('about')
├── SEO 용어 사전 → sp('seo-dict')
├── 마케팅 블로그 → sp('blog')
├── 무료 상담 → sp('contact')
└── 관리자 → admin.html (새 탭)
```

---

## 10. CTA 버튼 현황

- **상담신청** 버튼: `onclick="sp('contact')"` 또는 `onclick="sp('contact');return false"`
- **카카오상담** 버튼: `href="https://pf.kakao.com/_jxjxdcxj"` target="_blank"

---

## 11. 남은 작업 (미완성)

### 높은 우선순위

1. **온라인마케팅 서브페이지 상세화** — 검색광고(파워링크/파워컨텐츠/브랜드검색/플레이스), 언론, 브랜드마케팅 콘텐츠 추가 (사이트맵 기준)
2. **OG 이미지** — `/og-image.jpg` 실제 파일 필요 (1200×630px)
3. **sitemap.xml** — 검색엔진 제출용
4. **관리자 블로그 localStorage 연동** — 새로고침 시 작성 글 유지

### 낮은 우선순위

5. **데일리 카드뉴스 실제 API** — Make.com 또는 n8n 자동화 연동
6. **이미지 alt 태그** — 전수 점검
7. **네이버 API 403 재현 확인** — 실제 키 유효한지 테스트

---

## 12. 참고 사이트 (레퍼런스)

- https://venomad.com — 베놈 광고대행사
- https://next-t.co.kr — 넥스트티 마케팅
- https://ezloan.io/wiki — SEO 사례

---

## 13. 배포 방법

```bash
# 로컬에서 작업 후
git add .
git commit -m "feat: ..."
git push -u origin claude/nice-cray-94p4hx

# Vercel은 main 브랜치 자동 배포
# PR 머지 후 main에서 자동 배포됨
```

---

## 14. 주요 Git 커밋 이력 (이번 세션)

| 커밋 | 내용 |
|---|---|
| `a098850` | feat: add company page, SEO dictionary, fix footer company info |
| `3a0bc6a` | (이전 세션 최종 커밋) |

---

## 15. 새 대화에서 이어받기

새 Claude 세션에서 이 파일을 읽은 후:

1. `git checkout claude/nice-cray-94p4hx` 확인
2. `/home/user/desktop-tutorial/venom-wordpress/preview/index.html` 관련 섹션 읽기
3. 위 "남은 작업" 목록부터 진행

> 파일이 크므로 (5000+ 줄) 전체를 읽지 말고 `Grep`으로 필요한 섹션만 찾아서 수정할 것.
