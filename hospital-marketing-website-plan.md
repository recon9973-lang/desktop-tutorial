# 병원마케팅 홈페이지 제작 상세 기획서

> 버전: v1.0 | 작성일: 2026-06-23 | 대상: 풀스택 개발팀 / 디자인팀 / SEO팀

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [사이트맵 (IA)](#2-사이트맵-ia)
3. [페이지별 상세 기획](#3-페이지별-상세-기획)
4. [디자인 시스템](#4-디자인-시스템)
5. [기술 아키텍처](#5-기술-아키텍처)
6. [SEO 전략](#6-seo-전략)
7. [컴포넌트 구조](#7-컴포넌트-구조)
8. [개발 로드맵](#8-개발-로드맵)
9. [품질 기준 및 체크리스트](#9-품질-기준-및-체크리스트)

---

## 1. 프로젝트 개요

### 1-1. 프로젝트 목표

| 항목 | 내용 |
|------|------|
| 사이트 성격 | 병원마케팅 전문 대행사 기업 홈페이지 |
| 핵심 목적 | 서비스 소개 + 리드 획득(문의/상담 신청) + SEO/GEO/AEO 최적화 |
| 참고 레퍼런스 | https://www.next-t.co.kr/ (디자인 톤앤매너, 레이아웃 구조 참고) |
| 타겟 고객 | 병원장, 의원 원장, 병원 마케팅 담당자 |
| 핵심 KPI | 월간 오가닉 트래픽, 상담 신청 전환율, 페이지 체류 시간 |

### 1-2. 핵심 차별화 포인트

- **AI 마케팅 선도**: GEO(Generative Engine Optimization), AEO(Answer Engine Optimization) 서비스를 전면 부각
- **병과별 전문성**: 치과·피부과·정형외과 등 과별 맞춤 마케팅 케이스 제시
- **지역 SEO 특화**: 인천·대전·대구·울산·부산·광주 지역별 랜딩 페이지 운영
- **홈페이지 제작 + 마케팅 통합 패키지**: 원스톱 솔루션 강조

---

## 2. 사이트맵 (IA)

### 2-1. 전체 사이트맵

```
홈 (/)
│
├── 병원마케팅 (/hospital-marketing)                        [H2 GNB]
│   ├── 치과마케팅 (/hospital-marketing/dental)
│   ├── 피부과마케팅 (/hospital-marketing/dermatology)
│   ├── 정형외과마케팅 (/hospital-marketing/orthopedics)
│   ├── 한의원마케팅 (/hospital-marketing/oriental)
│   ├── 성형외과마케팅 (/hospital-marketing/plastic-surgery)
│   ├── 내과마케팅 (/hospital-marketing/internal-medicine)
│   ├── 안과마케팅 (/hospital-marketing/ophthalmology)
│   └── 의료기기마케팅 (/hospital-marketing/medical-device)
│
├── 온라인마케팅 (/online-marketing)                        [H2 GNB]
│   ├── 파워링크 (/online-marketing/power-link)
│   ├── 파워컨텐츠 (/online-marketing/power-content)
│   ├── 브랜드검색광고 (/online-marketing/brand-search)
│   ├── 플레이스검색광고 (/online-marketing/place-search)
│   ├── 인스타그램 (/online-marketing/instagram)
│   ├── 페이스북 (/online-marketing/facebook)
│   ├── 당근마켓 (/online-marketing/daangn)
│   ├── 리타게팅 (/online-marketing/retargeting)
│   ├── 언론홍보 (/online-marketing/press)
│   └── 브랜드마케팅 (/online-marketing/brand)
│       ├── 브랜드기획 (/online-marketing/brand/planning)
│       ├── 콘텐츠마케팅 (/online-marketing/brand/content)
│       ├── 브랜드블로그 (/online-marketing/brand/blog)
│       └── 영상콘텐츠 (/online-marketing/brand/video)
│
├── 병원홈페이지 제작 (/website)                            [H2 GNB]
│   ├── 기본형 (/website/basic)
│   ├── 중급형 (/website/standard)
│   ├── 고급형 (/website/premium)
│   ├── 기본형+SEO (/website/basic-seo)
│   ├── 중급형+SEO (/website/standard-seo)
│   ├── 고급형+SEO (/website/premium-seo)
│   ├── 패키지A: 기본+SEO+AEO+GEO(키워드1) (/website/pkg-a)
│   ├── 패키지B: 중급+SEO+AEO+GEO(키워드2) (/website/pkg-b)
│   ├── 패키지C: 고급+SEO+AEO+GEO(키워드3) (/website/pkg-c)
│   ├── 패키지D: 기본+SEO+AEO+GEO(키워드4)+컨텐츠4 (/website/pkg-d)
│   ├── 패키지E: 중급+SEO+AEO+GEO(키워드4)+컨텐츠8 (/website/pkg-e)
│   ├── 패키지F: 고급+SEO+AEO+GEO(키워드4)+컨텐츠16 (/website/pkg-f)
│   ├── 반응형 안내 (/website/responsive)
│   └── 적응형 안내 (/website/adaptive)
│
├── 블로그 (/blog)                                          [H2 GNB]
│   ├── 병원마케팅 카테고리 (/blog?cat=hospital-marketing)
│   ├── 병원홈페이지 카테고리 (/blog?cat=hospital-website)
│   ├── 지역마케팅 (/blog?cat=local)
│   │   ├── 인천병원마케팅 (/blog/local/incheon)
│   │   ├── 대전병원마케팅 (/blog/local/daejeon)
│   │   ├── 대구병원마케팅 (/blog/local/daegu)
│   │   ├── 울산병원마케팅 (/blog/local/ulsan)
│   │   ├── 부산병원마케팅 (/blog/local/busan)
│   │   └── 광주병원마케팅 (/blog/local/gwangju)
│   ├── 마케팅팁 (/blog?cat=tips)
│   ├── 마케팅소식 (/blog?cat=news)
│   ├── SEO (/blog?cat=seo)
│   ├── GEO (/blog?cat=geo)
│   └── AEO (/blog?cat=aeo)
│
├── AI마케팅 (/ai-marketing)                                [H2 GNB]
│   ├── GEO 서비스 (/ai-marketing/geo)
│   │   ├── GEO란? (/ai-marketing/geo/intro)
│   │   ├── GEO 프로세스 (/ai-marketing/geo/process)
│   │   └── GEO 효과 (/ai-marketing/geo/effect)
│   ├── AEO 서비스 (/ai-marketing/aeo)
│   │   ├── AEO란? (/ai-marketing/aeo/intro)
│   │   ├── AEO 프로세스 (/ai-marketing/aeo/process)
│   │   └── AEO 효과 (/ai-marketing/aeo/effect)
│   └── SEO 서비스 (/ai-marketing/seo)
│       ├── SEO 소개 (/ai-marketing/seo/intro)
│       ├── SEO란? (/ai-marketing/seo/about)
│       ├── SEO 프로세스 (/ai-marketing/seo/process)
│       ├── SEO 효과 (/ai-marketing/seo/effect)
│       ├── SEO 영역
│       │   ├── 콘텐츠 SEO (/ai-marketing/seo/content)
│       │   ├── 테크니컬 SEO (/ai-marketing/seo/technical)
│       │   └── 링크빌딩 SEO (/ai-marketing/seo/link-building)
│       └── SEO 용어 (/ai-marketing/seo/glossary)
│
├── 성공사례 (/case-study)                                  [보조 메뉴]
│   ├── 대행사 사례 (/case-study/agency)
│   ├── 회사별 (/case-study/company)
│   └── 과별 샘플 페이지 (/case-study/sample)
│
├── 회사소개 (/about)                                       [푸터]
│   ├── 연혁 (/about/history)
│   └── 조직 (/about/team)
│
├── 문의하기 (/contact)                                     [CTA 공통]
│
└── 자료실 (/resources)                                     [푸터]
    └── 질병관리청 국가건강정보포털 링크 연동
```

### 2-2. URL 네이밍 원칙

| 원칙 | 적용 예시 |
|------|-----------|
| 소문자 + 하이픈(kebab-case) | `/hospital-marketing/dental` |
| 한국어 URL 금지 (SEO) | ❌ `/병원마케팅` → ✅ `/hospital-marketing` |
| 계층은 최대 3depth | `/ai-marketing/seo/technical` |
| 블로그는 쿼리스트링 카테고리 | `/blog?cat=seo` |
| 지역 랜딩은 별도 경로 | `/blog/local/busan` |

---

## 3. 페이지별 상세 기획

### 3-1. 메인 페이지 (/)

#### 섹션 구성 (위 → 아래)

| # | 섹션명 | 목적 | 핵심 요소 |
|---|--------|------|-----------|
| 1 | Hero | 첫인상, 핵심 메시지 전달 | 풀스크린 배경, 메인 카피, CTA 버튼 2개(무료상담 / 서비스 보기) |
| 2 | 숫자로 보는 성과 | 신뢰 구축 | 누적 파트너 병원 수, 평균 트래픽 상승률, 운영 연수 (카운팅 애니메이션) |
| 3 | 서비스 소개 | 4대 서비스 일람 | 병원마케팅 / 온라인마케팅 / 홈페이지 제작 / AI마케팅 카드형 |
| 4 | AI마케팅 특화 | GEO·AEO 차별화 강조 | 풀블리드 배경, 아이콘+설명, "경쟁사보다 먼저" 메시지 |
| 5 | 병과별 마케팅 | 타겟 세분화 | 8개 병과 탭 or 그리드 (치과/피부과/정형 등) |
| 6 | 성공사례 | 사회적 증거 | 슬라이더: 병원명(익명), 성과 지표, Before/After |
| 7 | 홈페이지 제작 패키지 | 가격 정책 노출 | 3단 가격표 (기본/중급/고급) + 패키지 업셀 |
| 8 | 블로그 최신글 | 콘텐츠 신뢰도 | 최신 3~4개 포스트 카드 |
| 9 | 무료 상담 CTA | 전환 유도 | 폼 (이름, 연락처, 병원명, 관심서비스), 개인정보 동의 |
| 10 | Footer | 정보 제공 | 회사정보, 메뉴, 자료 링크, SNS |

#### Hero 섹션 카피 방향

```
[H1] 병원 매출을 올리는 가장 확실한 방법
[H2] AI 시대의 병원마케팅, GEO·AEO·SEO 통합 전략
[CTA-1] 무료 상담 신청하기 (Primary Button)
[CTA-2] 서비스 소개 보기 (Secondary Button)
```

---

### 3-2. 병원마케팅 과별 페이지 (공통 템플릿)

> `/hospital-marketing/[specialty]` — 8개 페이지 동일 템플릿 사용

| 섹션 | 내용 |
|------|------|
| Hero | 과명 + "전문 마케팅 파트너" 카피, 배경 이미지(병과별 상이) |
| 과별 특성 | 해당 병과 환자 검색 패턴, 주요 키워드 분석 |
| 서비스 전략 | 파워링크 / 블로그 / SNS / GEO 등 채널별 전략 설명 |
| 성공 사례 | 해당 과 실제 성과 (수치 포함) |
| 관련 지역 마케팅 | 인천·부산 등 지역별 링크 노출 |
| 무료 상담 CTA | 공통 폼 컴포넌트 삽입 |

---

### 3-3. 병원홈페이지 제작 페이지

#### 상품 체계 정리

| 등급 | 기본형 | 중급형 | 고급형 |
|------|--------|--------|--------|
| 홈페이지만 | basic | standard | premium |
| +SEO | basic-seo | standard-seo | premium-seo |
| +SEO+AEO+GEO | pkg-a (키워드1) | pkg-b (키워드2) | pkg-c (키워드3) |
| +SEO+AEO+GEO+콘텐츠 | pkg-d (콘텐츠4) | pkg-e (콘텐츠8) | pkg-f (콘텐츠16) |

#### 페이지 섹션

| 섹션 | 내용 |
|------|------|
| Hero | "병원홈페이지, 이제 마케팅까지 함께" |
| 반응형 vs 적응형 비교 | 인포그래픽 형태 비교 표 |
| 상품 비교표 | 체크박스형 기능 포함 여부 매트릭스 |
| 제작 프로세스 | 6단계 타임라인 (기획→디자인→개발→SEO→런칭→관리) |
| 병원 특화 기능 | 예약 시스템, 네이버 연동, 진료일정, 과별 소개 등 |
| 포트폴리오 | 제작 사례 갤러리 (필터: 병과별) |
| 무료 상담 CTA | |

---

### 3-4. AI마케팅 — GEO/AEO/SEO 상세 페이지

#### GEO (Generative Engine Optimization) 페이지

| 섹션 | 내용 |
|------|------|
| 개념 정의 | "ChatGPT·Perplexity·Gemini에 노출되는 새로운 SEO" |
| GEO란? | AI 검색엔진 작동 원리 도식화 |
| GEO 프로세스 | 5단계 프로세스 인포그래픽 |
| GEO 효과 | Before/After 노출 비교, 수치 데이터 |
| 병원 GEO 적용 사례 | 실제 AI 검색 결과 스크린샷 |

#### SEO 영역 세부 페이지

| 페이지 | 핵심 내용 |
|--------|-----------|
| 콘텐츠 SEO | 의료 키워드 리서치, E-E-A-T 전략, 블로그 운영법 |
| 테크니컬 SEO | Core Web Vitals, Schema Markup(의료), 사이트구조 |
| 링크빌딩 SEO | 의료 업계 링크 획득 전략, 언론 보도 활용 |
| SEO 용어집 | 검색엔진 최적화 관련 용어 사전 (FAQ 구조) |

---

### 3-5. 블로그 (/blog)

#### 구조

| 요소 | 상세 |
|------|------|
| 목록 페이지 | 카테고리 필터 탭 + 카드형 리스트 (썸네일, 제목, 날짜, 카테고리) |
| 상세 페이지 | 본문 + 목차(TOC) + 관련글 + 저자 프로필 + 공유 버튼 |
| 지역 랜딩 | `/blog/local/[city]` — 해당 지역 검색 특화 콘텐츠 |
| 카테고리 | 병원마케팅 / 병원홈페이지 / 지역마케팅 / 마케팅팁 / 마케팅소식 / SEO / GEO / AEO |

#### 블로그 SEO 특이사항

- 지역 랜딩 페이지는 `LocalBusiness` Schema 삽입 필수
- 각 포스트: `Article` Schema + `BreadcrumbList` Schema
- 질병관리청 국가건강정보포털 외부 링크는 `rel="noopener noreferrer"` + 신뢰도 표시

---

### 3-6. 공통 UI 컴포넌트 — 문의 폼

#### 필드 구성

| 필드명 | 타입 | 필수 여부 | 검증 규칙 |
|--------|------|-----------|-----------|
| 병원명 | text | 필수 | 2자 이상 |
| 원장/담당자명 | text | 필수 | 2자 이상 |
| 연락처 | tel | 필수 | 010-XXXX-XXXX 형식 |
| 이메일 | email | 선택 | 이메일 형식 |
| 관심 서비스 | checkbox (복수) | 필수 | 1개 이상 선택 |
| 문의 내용 | textarea | 선택 | 500자 이내 |
| 개인정보 동의 | checkbox | 필수 | 미동의시 제출 불가 |

#### 관심 서비스 선택지

- 병원마케팅 (광고)
- 홈페이지 제작
- SEO/GEO/AEO
- 블로그 운영
- SNS 관리
- 기타

---

## 4. 디자인 시스템

### 4-1. 컬러 팔레트

| 역할 | 색상명 | HEX | 용도 |
|------|--------|-----|------|
| Primary | Deep Navy | `#0A1628` | 헤더 배경, 주요 텍스트, 강조 버튼 |
| Primary Light | Navy Blue | `#1A3A6B` | 호버 상태, 섹션 배경 |
| Secondary | Vivid Blue | `#2563EB` | CTA 버튼, 링크, 아이콘 포인트 |
| Secondary Light | Sky Blue | `#EFF6FF` | 카드 배경, 섹션 구분 |
| Accent | Electric Cyan | `#06B6D4` | AI마케팅 강조, 배지, 태그 |
| Success | Emerald | `#10B981` | 성과 수치, 긍정 지표 |
| Warning | Amber | `#F59E0B` | 주의 알림, 강조 텍스트 |
| Neutral 900 | Dark Gray | `#111827` | 본문 텍스트 |
| Neutral 600 | Medium Gray | `#4B5563` | 서브 텍스트, 캡션 |
| Neutral 100 | Light Gray | `#F3F4F6` | 섹션 배경 교체용 |
| White | Pure White | `#FFFFFF` | 기본 배경 |

#### 그라디언트 정의

```css
/* Hero 섹션 */
--gradient-hero: linear-gradient(135deg, #0A1628 0%, #1A3A6B 50%, #2563EB 100%);

/* AI 마케팅 섹션 강조 */
--gradient-ai: linear-gradient(135deg, #06B6D4 0%, #2563EB 100%);

/* 버튼 Primary */
--gradient-cta: linear-gradient(90deg, #2563EB 0%, #1D4ED8 100%);
```

---

### 4-2. 타이포그래피

| 요소 | 폰트 | 크기 (Desktop) | 크기 (Mobile) | 굵기 | 줄간격 |
|------|------|---------------|---------------|------|--------|
| H1 | Pretendard | 56px | 32px | 800 | 1.2 |
| H2 | Pretendard | 40px | 26px | 700 | 1.25 |
| H3 | Pretendard | 28px | 22px | 600 | 1.3 |
| H4 | Pretendard | 20px | 18px | 600 | 1.4 |
| Body Large | Pretendard | 18px | 16px | 400 | 1.7 |
| Body | Pretendard | 16px | 15px | 400 | 1.7 |
| Caption | Pretendard | 13px | 12px | 400 | 1.5 |
| Button | Pretendard | 15px | 14px | 600 | 1.0 |

> **폰트 선택 이유**: Pretendard는 한글 가독성 최상, 시스템 폰트 대체 가능, 무료 라이선스

---

### 4-3. 스페이싱 시스템

```
spacing-1:  4px   (tight 요소 내부)
spacing-2:  8px   (아이콘 ↔ 텍스트)
spacing-3:  12px  (태그, 배지)
spacing-4:  16px  (카드 패딩)
spacing-6:  24px  (섹션 내부 간격)
spacing-8:  32px  (컴포넌트 간격)
spacing-12: 48px  (섹션 패딩 (mobile))
spacing-16: 64px  (섹션 패딩 (tablet))
spacing-24: 96px  (섹션 패딩 (desktop))
spacing-32: 128px (Hero 상하 패딩)
```

---

### 4-4. 브레이크포인트 (반응형)

| 이름 | 최소 너비 | 대상 기기 |
|------|-----------|-----------|
| `sm` | 640px | 대형 스마트폰 |
| `md` | 768px | 태블릿 세로 |
| `lg` | 1024px | 태블릿 가로 / 소형 노트북 |
| `xl` | 1280px | 데스크탑 |
| `2xl` | 1536px | 와이드 스크린 |

> **기본값**: Mobile-First 설계. 기준 너비 없으면 모바일 스타일 적용.

---

### 4-5. 컴포넌트 스타일 가이드

#### 버튼

| 종류 | 배경 | 텍스트 | 테두리 | 용도 |
|------|------|--------|--------|------|
| Primary | `#2563EB` | White | 없음 | 주 CTA (상담 신청) |
| Secondary | Transparent | `#2563EB` | `#2563EB` 1px | 보조 CTA (자세히 보기) |
| Ghost | Transparent | White | White 1px | 다크 배경 위 버튼 |
| Danger | `#EF4444` | White | 없음 | 삭제, 경고 |

- 모든 버튼: `border-radius: 8px`, `padding: 12px 24px`
- 호버: `opacity: 0.9` + `translateY(-1px)` 트랜지션
- 클릭: `scale(0.98)` 트랜지션

#### 카드

```
배경: #FFFFFF
테두리: 1px solid #E5E7EB
radius: 12px
shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)
hover shadow: 0 10px 25px rgba(0,0,0,0.12)
hover 트랜지션: translateY(-4px), 0.2s ease
```

---

### 4-6. 애니메이션 가이드

| 요소 | 애니메이션 | 트리거 | 시간 |
|------|-----------|--------|------|
| 섹션 진입 | Fade Up (opacity 0→1, y 20→0) | Intersection Observer | 0.5s |
| 카운터 숫자 | Count Up | 섹션 진입 시 | 1.5s |
| CTA 버튼 | Pulse (subtle) | 3초 주기 반복 | 0.8s |
| 메뉴 드롭다운 | Fade + Scale | hover | 0.15s |
| 카드 그리드 | Stagger (0.1s 간격) | 섹션 진입 시 | 0.4s each |
| Hero 텍스트 | Word by Word Reveal | 페이지 로드 | 0.8s total |

> **원칙**: `prefers-reduced-motion` 미디어 쿼리 필수 적용. 과한 애니메이션 금지.

---

## 5. 기술 아키텍처

### 5-1. 기술 스택 선정

| 레이어 | 기술 | 선정 이유 |
|--------|------|-----------|
| Framework | **Next.js 14 (App Router)** | SSG/SSR 혼합, SEO 최적화, RSC 지원 |
| Language | **TypeScript** | 타입 안전성, 유지보수성 |
| Styling | **Tailwind CSS v3** | 빠른 개발, 번들 최적화, 반응형 |
| UI Components | **shadcn/ui** | 접근성 준수, 커스터마이징 자유도 |
| Animation | **Framer Motion** | React 친화적, 선언형 애니메이션 |
| State | **Zustand** | 경량, 단순, Context 대비 성능 우수 |
| Form | **React Hook Form + Zod** | 성능, 유효성 검증 통합 |
| CMS | **Notion API** 또는 **Contentful** | 비개발자 콘텐츠 관리 (블로그) |
| Analytics | **Google Analytics 4 + Google Tag Manager** | 전환 추적 |
| Deployment | **Vercel** | Next.js 최적 배포 환경, Edge Network |
| 이미지 CDN | **Next.js Image (with Vercel)** | WebP 자동 변환, lazy loading |

---

### 5-2. 프로젝트 디렉토리 구조

```
/
├── app/                              # Next.js App Router
│   ├── (root)/
│   │   ├── page.tsx                  # 메인 홈
│   │   └── layout.tsx                # Root Layout
│   ├── hospital-marketing/
│   │   ├── page.tsx                  # 병원마케팅 목록
│   │   └── [specialty]/
│   │       └── page.tsx              # 과별 동적 페이지
│   ├── online-marketing/
│   │   └── [service]/page.tsx
│   ├── website/
│   │   └── [package]/page.tsx
│   ├── blog/
│   │   ├── page.tsx                  # 블로그 목록
│   │   ├── [slug]/page.tsx           # 포스트 상세
│   │   └── local/[city]/page.tsx     # 지역 랜딩
│   ├── ai-marketing/
│   │   └── [service]/
│   │       └── [sub]/page.tsx
│   ├── contact/page.tsx
│   ├── about/
│   │   ├── page.tsx
│   │   ├── history/page.tsx
│   │   └── team/page.tsx
│   └── api/
│       ├── contact/route.ts          # 문의 폼 API
│       └── blog/route.ts             # 블로그 API
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Navigation.tsx
│   │   ├── MobileMenu.tsx
│   │   └── Footer.tsx
│   ├── sections/                     # 페이지 섹션 단위
│   │   ├── HeroSection.tsx
│   │   ├── StatsSection.tsx
│   │   ├── ServicesSection.tsx
│   │   ├── AiMarketingSection.tsx
│   │   ├── SpecialtySection.tsx
│   │   ├── CaseStudySection.tsx
│   │   ├── PricingSection.tsx
│   │   ├── BlogPreviewSection.tsx
│   │   └── ContactFormSection.tsx
│   ├── ui/                           # Atomic 컴포넌트
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Tabs.tsx
│   │   ├── Accordion.tsx
│   │   └── CountUp.tsx
│   └── common/
│       ├── ContactForm.tsx           # 재사용 문의 폼
│       ├── SectionHeader.tsx
│       ├── Breadcrumb.tsx
│       └── SchemaOrg.tsx            # JSON-LD 스키마
│
├── lib/
│   ├── constants/
│   │   ├── menu.ts                   # GNB 메뉴 데이터
│   │   ├── services.ts               # 서비스 목록 데이터
│   │   └── specialties.ts            # 병과 데이터
│   ├── hooks/
│   │   ├── useIntersectionObserver.ts
│   │   └── useMediaQuery.ts
│   └── utils/
│       ├── seo.ts                    # metadata 생성 헬퍼
│       └── schema.ts                 # Schema.org 생성 헬퍼
│
├── content/                          # MDX 또는 JSON 정적 콘텐츠
│   ├── blog/
│   └── services/
│
├── public/
│   ├── images/
│   ├── icons/
│   └── fonts/
│
├── styles/
│   └── globals.css
│
├── tailwind.config.ts
├── next.config.ts
└── tsconfig.json
```

---

### 5-3. 렌더링 전략

| 페이지 유형 | 렌더링 방식 | 이유 |
|-------------|-------------|------|
| 메인 홈 | **SSG** (Static) | 변경 빈도 낮음, 최고 성능 |
| 서비스 소개 페이지 | **SSG** | 정적 콘텐츠 |
| 과별/지역 랜딩 페이지 | **SSG + ISR** (1시간) | SEO 중요, 가끔 업데이트 |
| 블로그 목록 | **SSR** 또는 **ISR** (10분) | 최신성 필요 |
| 블로그 상세 | **SSG + ISR** (1시간) | SEO 최우선 |
| 문의 폼 | **CSR** (클라이언트) | 인터랙션 |
| 관리자 대시보드 | **CSR** | 인증 필요 |

---

## 6. SEO 전략

### 6-1. 기술적 SEO (Technical SEO)

#### 필수 구현 항목

| 항목 | 상세 내용 | 우선순위 |
|------|-----------|----------|
| `robots.txt` | 크롤링 허용/차단 경로 명시 | P0 |
| `sitemap.xml` | 동적 생성, 우선순위(priority) 설정 | P0 |
| Canonical URL | 중복 페이지 방지 (`rel="canonical"`) | P0 |
| Open Graph | 소셜 공유 미리보기 (og:image 1200×630) | P0 |
| Twitter Card | 트위터 공유 최적화 | P1 |
| 구조화된 데이터 (JSON-LD) | 아래 스키마 항목 참조 | P0 |
| Core Web Vitals | LCP < 2.5s, FID < 100ms, CLS < 0.1 | P0 |
| 페이지 속도 | Lighthouse 성능 점수 90+ | P0 |
| HTTPS | SSL 인증서 강제 적용 | P0 |
| 모바일 최적화 | Google Mobile-Friendly Test 통과 | P0 |
| hreflang | 추후 다국어 확장 고려 시 적용 | P2 |

#### 구조화된 데이터 (Schema.org) 스키마 목록

| 페이지 | 적용 스키마 |
|--------|-------------|
| 메인 홈 | `Organization`, `WebSite`, `SearchAction` |
| 서비스 페이지 | `Service`, `BreadcrumbList` |
| 과별 마케팅 | `MedicalBusiness`, `LocalBusiness`, `BreadcrumbList` |
| 지역 랜딩 | `LocalBusiness` (지역명 포함), `BreadcrumbList` |
| 블로그 포스트 | `Article`, `Author`, `BreadcrumbList`, `FAQPage` (해당 시) |
| 가격 페이지 | `Product`, `Offer`, `AggregateRating` (리뷰 연동 시) |
| 문의 페이지 | `ContactPage` |
| 회사소개 | `Organization`, `AboutPage` |

---

### 6-2. 콘텐츠 SEO 전략

#### 타겟 키워드 체계

| 키워드 유형 | 예시 | 경쟁도 | 전환율 |
|-------------|------|--------|--------|
| 브랜드 (Brand) | [회사명] 병원마케팅 | 낮음 | 최고 |
| 서비스 (Service) | 치과마케팅 업체, 피부과 광고 대행사 | 중간 | 높음 |
| 지역 (Local) | 부산 병원마케팅, 인천 의원 SEO | 낮음 | 높음 |
| 정보성 (Informational) | 병원 블로그 운영 방법, GEO란 무엇인가 | 높음 | 낮음 |
| 비교 (Comparison) | 병원 홈페이지 제작 업체 비교 | 중간 | 중간 |

#### E-E-A-T 전략 (경험·전문성·권위성·신뢰성)

- **Experience**: 실제 성공 사례 수치 공개 (익명 처리)
- **Expertise**: 저자 프로필 페이지 (경력, 자격, 링크드인)
- **Authoritativeness**: 언론 보도 배지, 수상 실적
- **Trustworthiness**: 개인정보처리방침, 사업자 정보, 리뷰

---

### 6-3. GEO (Generative Engine Optimization) 전략

> AI 검색엔진(ChatGPT, Perplexity, Gemini, Copilot)에 최적화

| 전략 | 실행 방법 |
|------|-----------|
| FAQ 구조화 | 각 페이지 하단 FAQ 섹션 + `FAQPage` Schema |
| 질문형 H2 태그 | "병원마케팅이란?", "GEO와 SEO의 차이는?" |
| 정의형 콘텐츠 | 용어 정의를 명확한 문장으로 시작 |
| 인용 가능한 통계 | 병원 마케팅 트렌드 데이터 자체 조사 발행 |
| 구조화 데이터 완비 | AI 크롤러가 신뢰하는 Schema 풀세트 적용 |
| 공식 출처 인용 | 질병관리청, 건강보험심사평가원 데이터 인용 |

---

### 6-4. AEO (Answer Engine Optimization) 전략

> 음성 검색, 스니펫, 지식 패널 최적화

| 전략 | 실행 방법 |
|------|-----------|
| Featured Snippet 목표 | 정의형 단락을 40~60자 내외로 작성 |
| 음성 검색 키워드 | 구어체 롱테일 키워드 포함 |
| People Also Ask | PAA 패턴 분석 후 콘텐츠 반영 |
| How-to Schema | 프로세스 설명 페이지에 `HowTo` Schema 적용 |

---

### 6-5. 지역 SEO 전략

| 도시 | 타겟 키워드 예시 | 전용 랜딩 URL |
|------|-----------------|---------------|
| 인천 | 인천 치과 마케팅, 인천 병원 SEO | `/blog/local/incheon` |
| 대전 | 대전 피부과 광고, 대전 한의원 마케팅 | `/blog/local/daejeon` |
| 대구 | 대구 정형외과 마케팅, 대구 성형외과 광고 | `/blog/local/daegu` |
| 울산 | 울산 내과 마케팅, 울산 병원 홈페이지 | `/blog/local/ulsan` |
| 부산 | 부산 병원마케팅 대행사, 부산 안과 SEO | `/blog/local/busan` |
| 광주 | 광주 병원 블로그, 광주 의원 광고 | `/blog/local/gwangju` |

각 지역 랜딩 페이지 구성:
1. 지역명 포함 H1 태그
2. 해당 지역 의료 시장 특성 분석
3. 지역 특화 성공 사례
4. `LocalBusiness` Schema (지역 주소 포함)
5. 지역 병원 특화 문의 폼

---

### 6-6. 페이지별 메타데이터 가이드

| 페이지 | Title 패턴 | Description 패턴 |
|--------|-----------|-----------------|
| 홈 | `[회사명] - 병원마케팅 전문 대행사` | 병원 매출 상승을 위한 SEO·GEO·AEO 통합 마케팅. 치과·피부과 등 병과별 전문 전략. |
| 과별 | `[병과]마케팅 전문 - [회사명]` | [병과] 특화 디지털 마케팅으로 환자 유입을 극대화하세요. |
| 지역 | `[도시] 병원마케팅 - [회사명]` | [도시] 지역 병원 마케팅 전문가. 지역 SEO·광고·블로그 통합 운영. |
| 블로그 포스트 | `[포스트 제목] - [회사명] 블로그` | [포스트 첫 문장 발췌 120자 이내] |

---

## 7. 컴포넌트 구조

### 7-1. 글로벌 네비게이션 (GNB)

#### PC 레이아웃

```
[로고]  [병원마케팅▾]  [온라인마케팅▾]  [병원홈페이지 제작▾]  [블로그▾]  [AI마케팅▾]   [무료상담 CTA 버튼]
         └─ 드롭다운 메가메뉴 (2열 구성)
```

#### 메가메뉴 구조

```
병원마케팅
├── [아이콘] 치과마케팅
├── [아이콘] 피부과마케팅
├── [아이콘] 정형외과마케팅
├── [아이콘] 한의원마케팅
├── [아이콘] 성형외과마케팅
├── [아이콘] 내과마케팅
├── [아이콘] 안과마케팅
└── [아이콘] 의료기기마케팅
```

#### 모바일 레이아웃

- 햄버거 메뉴 → 풀스크린 슬라이드 오버레이
- 아코디언 형태 서브메뉴
- 하단 고정 CTA 버튼 (무료상담)

---

### 7-2. Footer 구조

```
[로고 + 회사 소개 한줄]                     [SNS 아이콘 그룹]

병원마케팅        온라인마케팅      홈페이지 제작     회사
치과마케팅        파워링크          기본형            회사소개
피부과마케팅      파워컨텐츠        중급형            연혁
정형외과마케팅    브랜드검색광고    고급형            조직
...               ...               ...               문의하기

─────────────────────────────────────────────────────────
[사업자 정보: 회사명 | 대표자 | 사업자번호 | 주소 | 전화]
[개인정보처리방침] [이용약관] [자료실]
© 2024 [회사명]. All rights reserved.

자료 출처: 질병관리청 국가건강정보포털 (health.kdca.go.kr)
```

---

## 8. 개발 로드맵

### 8-1. Phase별 개발 계획

#### Phase 1 — 기초 구축 (1~2주)

| 작업 | 담당 | 산출물 |
|------|------|--------|
| Next.js 프로젝트 셋업 | 개발 | 프로젝트 보일러플레이트 |
| Tailwind 커스텀 설정 | 개발 | `tailwind.config.ts` |
| 글로벌 레이아웃 (Header/Footer) | 개발+디자인 | Layout 컴포넌트 |
| 디자인 시스템 문서화 | 디자인 | Figma 컴포넌트 라이브러리 |
| SEO 기본 설정 (robots, sitemap) | 개발 | `robots.txt`, `sitemap.xml` |

#### Phase 2 — 핵심 페이지 (3~4주)

| 작업 | 담당 | 산출물 |
|------|------|--------|
| 메인 홈페이지 | 개발+디자인 | `/` 페이지 |
| 병원마케팅 섹션 | 개발 | 8개 과별 페이지 |
| 병원홈페이지 제작 | 개발 | 패키지 페이지 |
| 문의 폼 + API | 개발 | `/contact` + `/api/contact` |
| 기본 SEO 메타데이터 | 개발 | 전 페이지 metadata |

#### Phase 3 — 콘텐츠 및 AI마케팅 (5~6주)

| 작업 | 담당 | 산출물 |
|------|------|--------|
| 온라인마케팅 서비스 페이지 | 개발 | 10개 페이지 |
| AI마케팅 (GEO/AEO/SEO) | 개발+콘텐츠 | GEO·AEO·SEO 페이지 |
| 블로그 CMS 연동 | 개발 | 블로그 목록+상세 |
| 지역 랜딩 페이지 6개 | 개발+콘텐츠 | 지역별 페이지 |
| Schema.org 전체 적용 | 개발 | JSON-LD 삽입 |

#### Phase 4 — 최적화 및 런칭 (7~8주)

| 작업 | 담당 | 산출물 |
|------|------|--------|
| Lighthouse 성능 최적화 | 개발 | 점수 90+ 달성 |
| 크로스브라우저 테스트 | QA | 테스트 리포트 |
| Google Analytics 4 설정 | 마케팅 | 전환 추적 설정 |
| Search Console 등록 | 마케팅 | 색인 요청 완료 |
| 최종 콘텐츠 입력 | 콘텐츠 | 전 페이지 실제 내용 |
| Vercel 배포 | 개발 | 프로덕션 URL |

---

### 8-2. 우선순위 매트릭스

| 우선순위 | 페이지/기능 | 이유 |
|----------|-------------|------|
| **P0** (런칭 필수) | 메인 홈, 문의 폼, 모바일 반응형, 기본 SEO | 사업 운영 핵심 |
| **P1** (2주 내) | 과별 마케팅 8개, 홈페이지 제작 패키지, AI마케팅 | 전환 유도 핵심 |
| **P2** (1달 내) | 블로그, 지역 랜딩, 성공 사례 | 트래픽 성장 |
| **P3** (분기 내) | SEO 용어집, 자료실, 과별 샘플 | 콘텐츠 확장 |

---

## 9. 품질 기준 및 체크리스트

### 9-1. 성능 기준

| 지표 | 목표값 | 측정 도구 |
|------|--------|-----------|
| Lighthouse Performance | 90+ | Chrome DevTools |
| Lighthouse SEO | 100 | Chrome DevTools |
| Lighthouse Accessibility | 95+ | Chrome DevTools |
| LCP (Largest Contentful Paint) | < 2.5s | CrUX |
| CLS (Cumulative Layout Shift) | < 0.1 | CrUX |
| FID (First Input Delay) | < 100ms | CrUX |
| 첫 로드 번들 크기 | < 150KB (gzip) | Bundle Analyzer |

### 9-2. SEO 체크리스트

- [ ] 모든 페이지 고유 `<title>` (60자 이내)
- [ ] 모든 페이지 고유 `<meta description>` (160자 이내)
- [ ] 모든 이미지 `alt` 속성 포함
- [ ] 페이지당 H1 단 1개
- [ ] 내부 링크 구조 논리적 연결
- [ ] `robots.txt` 올바른 설정
- [ ] `sitemap.xml` 자동 생성 및 Search Console 제출
- [ ] Canonical URL 모든 페이지 적용
- [ ] Open Graph 이미지 전 페이지 (1200×630)
- [ ] JSON-LD Schema 주요 페이지 전체 적용
- [ ] 404 페이지 커스텀 (CTA 포함)
- [ ] 301 리다이렉트 구조 정의

### 9-3. 접근성 체크리스트

- [ ] 키보드 네비게이션 전체 지원
- [ ] `aria-label` 아이콘 버튼 전체 적용
- [ ] 색상 대비율 WCAG AA 기준 (4.5:1) 충족
- [ ] `focus-visible` 스타일 모든 인터랙티브 요소
- [ ] `prefers-reduced-motion` 적용
- [ ] Skip Navigation 링크 포함

### 9-4. 보안 체크리스트

- [ ] 문의 폼 서버사이드 유효성 검증
- [ ] CSRF 토큰 적용 (폼)
- [ ] Rate Limiting (문의 API)
- [ ] 환경변수 `.env.local` 분리 (API 키 노출 금지)
- [ ] `Content-Security-Policy` 헤더 설정
- [ ] 개인정보처리방침 페이지 필수 (PIPA 준수)
- [ ] HTTPS 강제 리다이렉트

---

## 부록: 외부 연동 정보

| 서비스 | 목적 | 연동 방법 |
|--------|------|-----------|
| 질병관리청 국가건강정보포털 | 의료 자료 출처 인용 | 외부 링크 (`rel="noopener"`) |
| 네이버 키워드 분석 | 키워드 리서치 데이터 | 수동 데이터 반영 (API 미공개) |
| Google Analytics 4 | 트래픽·전환 분석 | GTM 태그 삽입 |
| Google Search Console | 색인·순위 모니터링 | DNS 인증 또는 메타태그 |
| 카카오맵/네이버맵 | 위치 정보 (선택) | 임베드 스크립트 |
| 채널톡 또는 채널IO | 실시간 상담 위젯 | JavaScript 삽입 |

---

*본 기획서는 개발 착수 전 팀 내 공유 및 고객사 확인 후 최종 확정합니다.*
*기획 변경 시 버전 관리(v1.x)를 통해 이력을 추적합니다.*
