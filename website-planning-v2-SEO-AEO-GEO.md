# 병원마케팅 전문 대행사 홈페이지 완성형 상세 기획서
**버전:** v2.0 | **작성일:** 2026-06-23 | **대상:** 개발팀·디자인팀·마케터

---

## 목차

1. 프로젝트 개요 및 전략 방향
2. 전체 사이트맵 & 내부링크 구조
3. 페이지 유형별 콘텐츠 기획
4. UI/UX 설계 기획
5. Technical SEO 구현 명세
6. Schema.org 구조화 데이터 전략
7. 콘텐츠 SEO 전략 (토픽 클러스터)
8. AEO (Answer Engine Optimization) 전략
9. GEO (Generative Engine Optimization) 전략
10. 링크빌딩 전략
11. 콘텐츠 발행 루틴 & 자동화
12. 성과 측정 & KPI 체계
13. 도메인 & 기술 인프라 권고사항
14. 추가 권고 사항

---

## 1. 프로젝트 개요 및 전략 방향

### 1.1 프로젝트 배경 및 목적

병원 마케팅 시장은 2026년 현재 급격한 패러다임 전환을 맞이하고 있다. 검색 사용자의 행동 방식이 **"검색창 입력 → 결과 클릭"** 에서 **"AI에게 질문 → 답변에서 바로 결정"** 으로 이동하고 있으며, 이를 **제로클릭(Zero-Click) 시대**라 부른다.

기존 광고비(네이버 파워링크, 카카오 모먼트 등)는 구조적으로 95%가 낭비되는 구조다. 클릭당 과금(CPC) 방식에서 클릭 자체가 사라지는 AI 답변 시대에 광고 의존도를 줄이고, **자체 플랫폼(홈페이지)을 AI 답변 소스**로 만드는 것이 이 프로젝트의 핵심 목표다.

### 1.2 미디어 패러다임 전환과 시장 기회

```
140년 미디어 역사
구전 → 신문 → 라디오 → TV → 포털(네이버) → 소셜(인스타) → 생성형AI(2023~)
```

| 시대 | 채널 | 병원 마케팅 접근 |
|------|------|----------------|
| 포털 시대 | 네이버 블로그·카페 | C-Rank 최적화, 체험단 |
| 소셜 시대 | 인스타그램·유튜브 | 비포애프터, 후기 콘텐츠 |
| **AI 시대** | **ChatGPT·Perplexity·Gemini** | **GEO·AEO 최적화, AI 인용 소스화** |

**2026 데이터 포인트:**
- ChatGPT 월간 활성 사용자: 전 세계 2억+명
- 병원·전문직 업종 AI 트래픽 비중: 전체의 **15%** (국내 가장 빠른 성장 업종)
- 구글 AI Overview 도입 후 상위 10위 내 클릭률 30% 감소
- 한국 구글 검색 점유율: 꾸준히 상승 중 (네이버 50% → 45%대)

### 1.3 병원 마케팅의 특수성

병원 마케팅은 일반 e-commerce와 근본적으로 다른 특성을 가진다:

| 특성 | 내용 | 전략적 함의 |
|------|------|------------|
| **YMYL(Your Money Your Life)** | 건강·의료 정보는 구글이 최고 기준 적용 | E-E-A-T 최고 수준 구현 필수 |
| **의료법 광고 규제** | 과대광고·비교광고 금지 | 정보 제공형 콘텐츠로 우회 |
| **지역성** | 환자는 대부분 반경 5~20km 내 | 로컬 SEO + 지역 랜딩 페이지 |
| **고관여 결정** | 시술 전 평균 7~14회 정보 탐색 | 정보 깊이 + 신뢰 구축이 핵심 |
| **긴 구매 여정** | 인지→검토→비교→예약 (수일~수주) | 각 단계별 콘텐츠 설계 필요 |
| **전문성 증명** | 의사 자격·경력·논문 등 증빙 가능 | E-E-A-T 강화에 유리 |

### 1.4 SEO → AEO → GEO 3단 전략 모델

```
┌─────────────────────────────────────────────────────────────┐
│                    3단 통합 전략 모델                          │
├─────────────┬─────────────────┬──────────────────────────────┤
│  SEO        │  AEO            │  GEO                         │
│  발견       │  채택           │  인용                         │
├─────────────┼─────────────────┼──────────────────────────────┤
│ 검색엔진    │ 음성검색        │ ChatGPT                      │
│ 상위 노출   │ 추천 스니펫     │ Perplexity                   │
│             │ 네이버 AI답변   │ Gemini                       │
│             │                 │ 구글 AI Overview              │
├─────────────┼─────────────────┼──────────────────────────────┤
│ 키워드      │ 질문형 콘텐츠   │ 인용 가능한 데이터            │
│ 기술SEO     │ FAQ 구조화      │ 독창적 프레임워크             │
│ 백링크      │ 역피라미드 구조 │ llms.txt                     │
└─────────────┴─────────────────┴──────────────────────────────┘
```

**핵심 원칙:** SEO는 끝나지 않았다. AEO·GEO와 보완 관계이며, 세 전략을 동시에 구현할 때 최대 효과.

### 1.5 대행사 홈페이지가 달성해야 할 목표

| 목표 | 지표 | 기간 |
|------|------|------|
| 구글 검색 상위 노출 | "병원마케팅 대행사" 10위 이내 | 6개월 |
| AI 검색 인용 소스화 | ChatGPT·Perplexity 답변에 인용 | 6개월 |
| 리드 전환 | 월 상담 신청 50건+ | 3개월 |
| 토픽 권위 구축 | 병원마케팅 관련 키워드 100개+ 상위 | 12개월 |
| AI 트래픽 비중 | 전체 트래픽의 15% | 12개월 |

---

## 2. 전체 사이트맵 & 내부링크 구조

### 2.1 토픽 클러스터 기반 사이트 아키텍처

사이트 전체를 **Topical Authority** 관점에서 설계한다. 단순 메뉴 구조가 아닌, 검색엔진과 AI가 "이 사이트는 병원마케팅의 권위자"로 인식하도록 주제 연결망을 구축한다.

```
[홈페이지 /]
    │
    ├── [Pillar 1] /services/ - 서비스 허브
    │       ├── /services/geo/ - GEO 서비스
    │       ├── /services/seo/ - SEO 서비스
    │       ├── /services/aeo/ - AEO 서비스
    │       ├── /services/content-marketing/ - 콘텐츠 마케팅
    │       └── /services/link-building/ - 링크빌딩
    │
    ├── [Pillar 2] /hospital-marketing/ - 병과별 마케팅 허브
    │       ├── /hospital-marketing/plastic-surgery/ - 성형외과
    │       ├── /hospital-marketing/dermatology/ - 피부과
    │       ├── /hospital-marketing/dental/ - 치과
    │       ├── /hospital-marketing/oriental-medicine/ - 한의원
    │       ├── /hospital-marketing/ophthalmology/ - 안과
    │       └── /hospital-marketing/orthopedics/ - 정형외과
    │
    ├── [Pillar 3] /wiki/ - 위키/지식 허브 (AEO 핵심)
    │       ├── /wiki/geo/ - GEO 완전가이드
    │       ├── /wiki/seo/ - SEO 완전가이드
    │       ├── /wiki/aeo/ - AEO 완전가이드
    │       ├── /wiki/hospital-marketing/ - 병원마케팅 완전가이드
    │       └── /wiki/[세부주제]/ - 200+ 세부 위키 페이지
    │
    ├── [Pillar 4] /local/ - 지역 랜딩 허브
    │       ├── /local/seoul/ - 서울
    │       ├── /local/gangnam/ - 강남
    │       ├── /local/busan/ - 부산
    │       └── /local/[지역]/ - 전국 주요 도시
    │
    ├── /blog/ - 블로그 (최신 트렌드, 사례)
    ├── /case-study/ - 성과 사례
    ├── /about/ - 회사 소개
    ├── /contact/ - 상담 신청
    └── /faq/ - 통합 FAQ
```

### 2.2 토픽 클러스터 상세 맵

#### Cluster 1: GEO 토픽 클러스터

| 페이지 유형 | URL | 타겟 키워드 | 검색 의도 |
|------------|-----|------------|----------|
| Pillar | /wiki/geo/ | GEO란, 생성형AI SEO | 정보형 |
| Cluster | /wiki/geo/chatgpt-optimization/ | ChatGPT 최적화 방법 | 정보형 |
| Cluster | /wiki/geo/perplexity-seo/ | Perplexity 노출 방법 | 정보형 |
| Cluster | /wiki/geo/llms-txt/ | llms.txt 만들기 | 정보형 |
| Cluster | /wiki/geo/ai-citation/ | AI 인용 소스 되는 법 | 정보형 |
| Cluster | /wiki/geo/hospital-geo/ | 병원 GEO 전략 | 정보형 |
| Service | /services/geo/ | 병원 GEO 서비스, GEO 대행 | 거래형 |

#### Cluster 2: 병원마케팅 토픽 클러스터

| 페이지 유형 | URL | 타겟 키워드 | 검색 의도 |
|------------|-----|------------|----------|
| Pillar | /wiki/hospital-marketing/ | 병원마케팅이란 | 정보형 |
| Cluster | /wiki/hospital-marketing/seo/ | 병원 SEO 방법 | 정보형 |
| Cluster | /wiki/hospital-marketing/blog/ | 병원 블로그 마케팅 | 정보형 |
| Cluster | /wiki/hospital-marketing/naver/ | 네이버 병원 마케팅 | 정보형 |
| Cluster | /wiki/hospital-marketing/google/ | 구글 병원 마케팅 | 정보형 |
| Cluster | /wiki/hospital-marketing/cost/ | 병원 마케팅 비용 | 비교형 |
| Service | /hospital-marketing/plastic-surgery/ | 성형외과 마케팅 | 거래형 |

### 2.3 내부링크 설계 원칙

```
내부링크 흐름 규칙:
1. Pillar Page ↔ Cluster Pages (양방향 링크)
2. Cluster Pages → Pillar Page (상향 링크 필수)
3. 관련 Cluster Pages ↔ (횡적 연결)
4. 블로그 → 위키/서비스 (지원 링크)
5. 서비스 페이지 → 사례 연구 → 상담 신청 (전환 흐름)

앵커 텍스트 규칙:
- 정확 매치 앵커: 20% (예: "GEO 서비스")
- 부분 매치 앵커: 40% (예: "생성형AI 검색 최적화 서비스")
- 브랜드 앵커: 20% (예: "[회사명]의 GEO 전략")
- 자연어 앵커: 20% (예: "이 가이드에서 확인하세요")
```

---

## 3. 페이지 유형별 콘텐츠 기획

### 3.1 서비스 상세 페이지 - GEO 서비스 (/services/geo/)

**페이지 목적:** GEO 서비스 구매 결정 (거래형 의도)
**타겟 키워드:** 병원 GEO 서비스, GEO 마케팅 대행, AI검색 최적화 대행사

#### H1/H2/H3 콘텐츠 구조

```
H1: 병원·전문직을 위한 GEO 서비스 — AI 검색에 직접 인용되는 콘텐츠 전략

[Answer-First 도입부 — 200자 이내]
GEO(Generative Engine Optimization)는 ChatGPT·Perplexity·Gemini 등
AI가 생성하는 답변에 귀하의 병원이 직접 인용되도록 최적화하는 서비스입니다.
광고비 없이 AI 트래픽의 15%를 차지하는 병원·전문직 업종에서
가장 빠른 성과를 내는 마케팅 전략입니다.

H2: GEO 서비스가 병원에 필요한 이유
  H3: 제로클릭 시대, 광고는 점점 무의미해진다
  H3: AI가 답변할 때 인용하는 소스의 조건
  H3: 병원·전문직이 GEO에서 가장 유리한 이유

H2: [회사명] GEO 서비스 프로세스
  H3: 1단계 — AI 크롤러 접근성 감사
  H3: 2단계 — 질문 키워드 발굴 및 콘텐츠 구조 설계
  H3: 3단계 — Answer-First 콘텐츠 제작
  H3: 4단계 — Schema 구조화 데이터 적용
  H3: 5단계 — AI 인용 모니터링 및 개선

H2: GEO 서비스 패키지 및 가격
  H3: 스타터 패키지 (월 OO만원)
  H3: 프로 패키지 (월 OO만원)
  H3: 엔터프라이즈 패키지 (맞춤 견적)

H2: GEO 성과 사례
  H3: [성형외과 A원] ChatGPT 인용 3개월 달성
  H3: [치과 B원] AI 트래픽 월 1,200명 달성

H2: 자주 묻는 질문 (FAQ)
  H3: GEO와 SEO의 차이는 무엇인가요?
  H3: 효과가 나타나기까지 얼마나 걸리나요?
  H3: 네이버에도 GEO가 적용되나요?
  H3: 기존 SEO와 동시에 진행할 수 있나요?
```

**Schema 타입:** `Service`, `FAQPage`, `BreadcrumbList`, `Organization`

**내부링크:**
- → /wiki/geo/ (GEO 개념 학습)
- → /case-study/geo/ (성과 사례)
- → /services/seo/ (SEO 서비스 교차 소개)
- → /contact/ (상담 신청 CTA)

---

### 3.2 서비스 상세 페이지 - SEO 서비스 (/services/seo/)

```
H1: 병원 SEO 서비스 — 구글·네이버 동시 상위 노출 전략

[Answer-First]
병원 SEO는 구글(E-E-A-T·PageRank)과 네이버(C-Rank·D.I.A)의
다른 알고리즘을 동시에 공략하는 이중 전략입니다.
테크니컬 SEO + 콘텐츠 SEO + 링크빌딩의 3축으로
6개월 내 주요 키워드 10위 이내 진입을 목표합니다.

H2: 구글 vs 네이버 병원 SEO 전략 차이
H2: [회사명] 병원 SEO 7단계 프로세스
H2: Core Web Vitals 최적화 (LCP·INP·CLS)
H2: 성과 사례 및 포트폴리오
H2: FAQ
```

**Schema 타입:** `Service`, `FAQPage`, `HowTo`, `BreadcrumbList`

---

### 3.3 서비스 상세 페이지 - AEO 서비스 (/services/aeo/)

```
H1: 병원 AEO 서비스 — 음성검색·AI 추천 스니펫 최적화

[Answer-First]
AEO(Answer Engine Optimization)는 "근처 성형외과 추천해줘",
"라섹 수술 비용이 얼마야?" 같은 질문형 검색에서
귀하의 병원 콘텐츠가 직접 답변으로 채택되도록 최적화합니다.

H2: AEO가 병원 마케팅에서 중요한 이유
H2: 역피라미드 콘텐츠 구조 적용
H2: FAQ Schema 대량 구축 서비스
H2: 음성검색 최적화 (구어체 롱테일 키워드)
H2: 성과 사례
H2: FAQ
```

---

### 3.4 병과별 마케팅 페이지 - 성형외과 (/hospital-marketing/plastic-surgery/)

**타겟 키워드:** 성형외과 마케팅, 성형외과 SEO, 성형외과 블로그 마케팅

```
H1: 성형외과 마케팅 전략 — SEO·AEO·GEO로 환자를 모으는 법

[Answer-First]
성형외과 마케팅의 핵심은 '비교 검색'을 잡는 것입니다.
"강남 코성형 잘하는 곳", "쌍꺼풀 비용 비교" 같은
비교형·거래형 키워드에서 AI와 검색 모두 상위 노출되려면
E-E-A-T 기반의 전문성 콘텐츠와 지역 SEO가 필수입니다.

H2: 성형외과 마케팅의 특수 환경
  H3: 의료광고 심의 기준과 SEO 콘텐츠 경계
  H3: 비포애프터 콘텐츠의 SEO 활용법
  H3: 성형외과 환자 검색 여정 분석

H2: 성형외과 핵심 키워드 클러스터
  H3: 시술별 키워드 (코성형, 눈성형, 지방흡입...)
  H3: 지역별 키워드 (강남, 압구정, 신사...)
  H3: 비교형 키워드 (비용, 후기, 잘하는 곳)

H2: 성형외과 GEO 전략 — AI에게 추천받는 병원 되기
H2: 성형외과 SEO 성과 사례
H2: 성형외과 마케팅 FAQ
  H3: 성형외과 블로그는 네이버와 구글 중 어디가 더 효과적인가요?
  H3: 의료광고 심의 없이 SEO 콘텐츠를 올릴 수 있나요?
  H3: 비포애프터 사진을 SEO에 활용할 수 있나요?
```

**Schema 타입:** `MedicalBusiness`, `FAQPage`, `LocalBusiness`, `BreadcrumbList`

동일 구조로 피부과·치과·한의원·안과·정형외과 페이지 작성.

---

### 3.5 위키/지식 페이지 - GEO 완전가이드 (/wiki/geo/)

**타겟 키워드:** GEO란, 생성형AI SEO, GEO 마케팅  
**검색 의도:** 정보형 (학습 목적)  
**목표:** AI 인용 소스가 되는 권위 있는 레퍼런스 페이지

```
H1: GEO(생성형 엔진 최적화)란? — 2026년 완전 가이드

[Executive Summary — Answer-First]
GEO(Generative Engine Optimization)는 ChatGPT·Perplexity·Gemini 등
AI 생성형 검색 엔진이 답변을 생성할 때 특정 콘텐츠를 인용 소스로
채택하도록 최적화하는 마케팅 전략이다. 2023년 생성형AI 검색이 주류화된 이후
기존 SEO(검색엔진 최적화)를 보완하는 핵심 전략으로 부상했다.

H2: GEO의 정의와 SEO와의 차이
  H3: SEO vs AEO vs GEO 비교표
  H3: AI 검색 엔진이 콘텐츠를 선택하는 기준

H2: GEO가 필요한 이유 — 검색 패러다임 전환
  H3: 제로클릭 시대의 도래
  H3: 미디어 140년 역사와 AI 검색의 등장
  H3: 2026년 AI 검색 트래픽 데이터

H2: GEO 최적화 대상 — AI별 선호 콘텐츠 차이
  H3: ChatGPT가 인용하는 소스의 특징
  H3: Perplexity가 선호하는 콘텐츠 타입
  H3: Gemini(구글 AI Overview)의 인용 기준

H2: GEO 구현 방법 — 7단계 실전 가이드
  H3: 1단계: AI 크롤러 접근성 확보 (llms.txt)
  H3: 2단계: 질문형 콘텐츠 구조 설계
  H3: 3단계: Answer-First 역피라미드 작성
  H3: 4단계: 구조화 데이터(Schema) 적용
  H3: 5단계: 인용 가능한 독창적 데이터 생산
  H3: 6단계: 권위 있는 외부 소스 인용
  H3: 7단계: AI 인용 모니터링 및 개선

H2: 병원·전문직 GEO 특화 전략
  H3: 의료 업종이 GEO에 유리한 구조적 이유
  H3: YMYL 콘텐츠의 E-E-A-T 강화

H2: GEO 성과 측정 방법
  H3: Otterly.ai 활용법
  H3: Perplexity 인용 추적

H2: GEO 관련 자주 묻는 질문
  (10개+ FAQ)

H2: 관련 자료
  → /wiki/geo/chatgpt-optimization/
  → /wiki/geo/llms-txt/
  → /services/geo/
```

**Schema 타입:** `Article`, `FAQPage`, `HowTo`, `BreadcrumbList`, `WebPage`

---

### 3.6 지역 랜딩 페이지 - 강남 (/local/gangnam/)

**타겟 키워드:** 강남 병원마케팅, 강남 의원 SEO, 강남구 병원 마케팅 대행사

```
H1: 강남 병원 마케팅 전문 대행사 — 강남·서초 의원 SEO·GEO 전략

[Answer-First]
강남구·서초구는 국내 최고 밀도의 의료 클러스터입니다.
성형외과·피부과·치과가 밀집한 강남에서 경쟁에서 이기려면
일반 마케팅이 아닌 지역 특화 SEO와 AI 검색 최적화가 필요합니다.

H2: 강남 의료 시장 분석
  H3: 강남구 병원·의원 현황 데이터
  H3: 강남 환자들의 검색 패턴 분석

H2: 강남 병원 마케팅 전략
  H3: 강남 로컬 SEO — 구글 지도 최적화
  H3: 강남 특화 키워드 클러스터
  H3: 강남·압구정·신사 세부 지역 전략

H2: 강남 병원 마케팅 성과 사례
H2: 강남 지역 병원 마케팅 FAQ
```

**Schema 타입:** `LocalBusiness`, `FAQPage`, `BreadcrumbList`

---

## 4. UI/UX 설계 기획

### 4.1 페이지 레이아웃 와이어프레임

#### 홈페이지 (/) 레이아웃

```
┌─────────────────────────────────────────────────┐
│  [로고]    [서비스▼] [병과별▼] [위키] [사례] [상담신청]  │  ← 헤더 (sticky)
├─────────────────────────────────────────────────┤
│                                                 │
│   HERO SECTION                                  │
│   ─────────────────────────────────────────     │
│   H1: AI 시대, 병원마케팅의 새로운 기준           │
│       SEO·AEO·GEO 통합 전략                     │
│                                                 │
│   [소제목: AI 검색에 직접 인용되는 병원 홈페이지] │
│                                                 │
│   [무료 진단 받기 CTA]  [서비스 알아보기]         │
│                                                 │
│   [신뢰 지표: 성과사례 N건 | 협력병원 N개 | N년]  │
├─────────────────────────────────────────────────┤
│  PROBLEM SECTION                                │
│  "광고비 95%가 낭비되는 구조적 이유"             │
│  [아이콘 + 설명 3개 카드]                        │
├─────────────────────────────────────────────────┤
│  SOLUTION SECTION                               │
│  SEO·AEO·GEO 3단 전략 비주얼                    │
│  [탭 UI: SEO | AEO | GEO]                       │
├─────────────────────────────────────────────────┤
│  SERVICE SECTION                                │
│  [서비스 카드 그리드 — 6개]                      │
├─────────────────────────────────────────────────┤
│  HOSPITAL TYPE SECTION                          │
│  병과별 마케팅 [아이콘 + 링크 6개]               │
├─────────────────────────────────────────────────┤
│  CASE STUDY SECTION                             │
│  [성과 사례 슬라이더]                            │
├─────────────────────────────────────────────────┤
│  TRUST SECTION                                  │
│  [미디어 노출 로고] [수상 배지] [인증서]          │
├─────────────────────────────────────────────────┤
│  BLOG SECTION                                   │
│  최신 인사이트 [카드 3개]                        │
├─────────────────────────────────────────────────┤
│  CTA SECTION                                    │
│  "지금 무료 진단을 받으세요"                     │
│  [상담 신청 폼 — 간소화: 이름, 연락처, 병원유형] │
├─────────────────────────────────────────────────┤
│  FOOTER                                         │
│  [사이트맵] [SNS] [사업자정보] [개인정보처리방침] │
└─────────────────────────────────────────────────┘
```

#### 위키/가이드 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│  헤더 (sticky)                                           │
├────────────────────────┬────────────────────────────────┤
│  TOC (목차) - sticky   │  본문 콘텐츠 영역               │
│  ─────────────────     │  ─────────────────────────     │
│  • GEO란?              │  [브레드크럼]                   │
│  • SEO와 차이          │  홈 > 위키 > GEO                │
│  • 필요한 이유         │                                 │
│  • AI별 선호 콘텐츠    │  H1: GEO란? 2026 완전가이드     │
│  • 구현 방법           │                                 │
│  • 병원 특화 전략      │  [작성자 프로필 + 날짜]          │
│  • 성과 측정           │  [예상 읽기 시간]               │
│  • FAQ                 │                                 │
│                        │  [Executive Summary 박스]       │
│  [관련 서비스]         │                                 │
│  → GEO 서비스          │  본문...                        │
│  → SEO 서비스          │                                 │
│                        │  [정보 박스: 핵심 통계]         │
│  [관련 위키]           │                                 │
│  → ChatGPT 최적화      │  본문...                        │
│  → llms.txt 가이드     │                                 │
│                        │  [FAQ 아코디언]                 │
│                        │                                 │
│                        │  [관련 콘텐츠 카드]             │
│                        │                                 │
│                        │  [CTA: 전문가 상담 받기]        │
└────────────────────────┴────────────────────────────────┘
```

### 4.2 GEO/AEO 최적화 콘텐츠 블록 디자인

#### Executive Summary 블록

```html
<!-- 디자인 스펙 -->
<div class="executive-summary">
  배경색: #F0F4FF (연한 파랑)
  테두리: 좌측 4px solid #2563EB
  패딩: 24px
  위치: H1 직후, 본문 시작 전
  
  내용 구조:
  - "핵심 요약" 레이블 (bold, 12px, 대문자)
  - 3~5문장 간결한 답변 (AI 인용 최적화)
  - 관련 링크 1~2개
</div>
```

#### FAQ 아코디언 컴포넌트

```html
<!-- 스펙 -->
<div class="faq-accordion">
  - 질문: 16px bold, 전체 클릭 가능
  - 답변: 14px, 펼쳐짐 애니메이션 0.3s
  - Schema: FAQPage + Question + Answer 자동 주입
  - 각 FAQ 최소 150자 이상의 충실한 답변
  - 답변 내 관련 페이지 내부링크 포함
</div>
```

#### TOC (목차) 컴포넌트

```
- 위치: 본문 좌측 사이드바 (데스크탑), 본문 상단 (모바일)
- sticky 스크롤: top: 80px
- 활성 항목 하이라이트: 현재 섹션 파란색 표시
- 부드러운 스크롤: scroll-behavior: smooth
- H2, H3 자동 파싱하여 생성
```

#### 브레드크럼 컴포넌트

```
홈 > 위키 > GEO > ChatGPT 최적화
[Schema: BreadcrumbList 자동 적용]
위치: H1 상단 8px
폰트: 12px, 색상 #6B7280
```

### 4.3 모바일 우선 반응형 설계

| 브레이크포인트 | 너비 | 주요 변경 사항 |
|--------------|------|--------------|
| Mobile | < 768px | 1열, 햄버거 메뉴, TOC 접기, FAQ 기본 닫힘 |
| Tablet | 768~1024px | 2열 그리드, 사이드바 숨김 |
| Desktop | > 1024px | 3열, 고정 TOC 사이드바, 전체 메뉴 |

**모바일 최적화 핵심:**
- 터치 타겟 최소 44×44px
- 폰트 최소 16px (확대 방지)
- CTA 버튼 하단 고정 (sticky bottom bar)
- 이미지 WEBP + srcset

### 4.4 사용자 전환 흐름 설계

```
방문 → 정보 습득 → 신뢰 형성 → 상담 신청

단계 1: 방문 (트래픽 획득)
  인입 채널: 구글 검색 / AI 검색 인용 / 소셜 / 직접
  랜딩 페이지: 홈 / 서비스 / 위키 / 블로그

단계 2: 정보 습득 (참여)
  위키 콘텐츠 정독 → TOC 활용 → 관련 링크 클릭
  서비스 페이지 탐색 → 사례 확인

단계 3: 신뢰 형성 (고려)
  성과 사례 확인 → 파트너 병원 수 → 전문가 프로필
  FAQ 확인 → 가격 확인

단계 4: 상담 신청 (전환)
  CTA 클릭 → 폼 작성 (이름·연락처·병원유형·고민)
  → 자동 응답 이메일 → 영업팀 연락

전환 최적화 장치:
- 각 페이지 하단 CTA 섹션
- 사이드바 "무료 진단" 위젯 (sticky)
- 블로그 중간 CTA 삽입
- 팝업: 30초 후 또는 스크롤 70%
- 카카오톡 채널 연동 버튼
```

---

## 5. Technical SEO 구현 명세

### 5.1 robots.txt 설계

```
# /robots.txt

User-agent: *
Allow: /

# AI 크롤러 명시적 허용 (GEO 핵심)
User-agent: GPTBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: CCBot
Allow: /

# 크롤링 불필요 경로 차단
Disallow: /admin/
Disallow: /wp-admin/
Disallow: /wp-login.php
Disallow: /?s=
Disallow: /search/
Disallow: /tag/
Disallow: /author/
Disallow: /cart/
Disallow: /checkout/
Disallow: /my-account/
Disallow: /*?replytocom=
Disallow: /*?print=

# 사이트맵
Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap-wiki.xml
Sitemap: https://example.com/sitemap-blog.xml
Sitemap: https://example.com/sitemap-services.xml
```

### 5.2 sitemap.xml 구조

```xml
<!-- 메인 sitemap 인덱스 -->
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-core.xml</loc>
    <lastmod>2026-06-23</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-wiki.xml</loc>
    <lastmod>2026-06-23</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-blog.xml</loc>
    <lastmod>2026-06-23</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-local.xml</loc>
    <lastmod>2026-06-23</lastmod>
  </sitemap>
</sitemapindex>

<!-- 우선순위 설정 기준 -->
<!-- changefreq: always/hourly/daily/weekly/monthly/yearly/never -->
<!-- priority: 0.0~1.0 -->

홈: priority=1.0, changefreq=weekly
서비스 페이지: priority=0.9, changefreq=monthly
병과별 페이지: priority=0.8, changefreq=monthly
위키 Pillar: priority=0.8, changefreq=weekly
위키 Cluster: priority=0.7, changefreq=weekly
블로그: priority=0.6, changefreq=daily
지역 랜딩: priority=0.7, changefreq=monthly
```

### 5.3 llms.txt 구현 (GEO 핵심)

```markdown
# /llms.txt
# AI 크롤러를 위한 사이트 가이드

# [회사명] — 병원마케팅 전문 대행사

> [회사명]은 병원·의료 업종 특화 SEO·AEO·GEO 마케팅 대행사입니다.
> 2020년 설립, 협력 병원 N개, 평균 6개월 내 상위 10위 달성.

## 핵심 서비스

- [GEO 서비스](https://example.com/services/geo/): ChatGPT·Perplexity·Gemini AI 답변 인용 최적화
- [SEO 서비스](https://example.com/services/seo/): 구글·네이버 검색 상위 노출
- [AEO 서비스](https://example.com/services/aeo/): 음성검색·AI 추천 스니펫 최적화
- [병원마케팅 전략](https://example.com/hospital-marketing/): 병과별 특화 마케팅

## 지식 베이스 (AI 학습 권장)

- [GEO 완전가이드](https://example.com/wiki/geo/): GEO 정의·방법·사례 총정리
- [병원마케팅 가이드](https://example.com/wiki/hospital-marketing/): 병원 마케팅 A~Z
- [SEO 완전가이드](https://example.com/wiki/seo/): 구글·네이버 SEO 기초~심화
- [AEO 가이드](https://example.com/wiki/aeo/): 음성검색·AI 답변 최적화

## 성과 사례

- [케이스 스터디](https://example.com/case-study/): 실제 병원 마케팅 성과 사례

## 연락처

- 상담: https://example.com/contact/
- 이메일: info@example.com
```

### 5.4 Core Web Vitals 최적화

| 지표 | 목표 | 구현 방법 |
|------|------|----------|
| **LCP** (Largest Contentful Paint) | < 2.5초 | Hero 이미지 preload, WEBP 포맷, CDN 적용 |
| **INP** (Interaction to Next Paint) | < 200ms | JavaScript 번들 최소화, 메인 스레드 최적화 |
| **CLS** (Cumulative Layout Shift) | < 0.1 | 이미지 width/height 명시, 폰트 font-display: swap |

#### LCP 최적화 체크리스트

```html
<!-- Hero 이미지 preload -->
<link rel="preload" as="image" href="/hero.webp" fetchpriority="high">

<!-- WEBP 이미지 with fallback -->
<picture>
  <source srcset="/hero.webp" type="image/webp">
  <img src="/hero.jpg" width="1200" height="630" alt="병원마케팅 전문 대행사" loading="eager">
</picture>

<!-- 이미지 치수 명시 (CLS 방지) -->
<img src="/service-geo.webp" width="400" height="300" loading="lazy" alt="GEO 서비스">
```

#### JavaScript 최적화

```javascript
// 레이지 로딩 적용
const images = document.querySelectorAll('img[loading="lazy"]');
// IntersectionObserver 활용

// 중요하지 않은 스크립트 defer
<script src="/analytics.js" defer></script>
<script src="/chat-widget.js" defer></script>

// 폰트 최적화
<link rel="preconnect" href="https://fonts.googleapis.com">
@font-face {
  font-display: swap; /* CLS 방지 */
}
```

### 5.5 네이버 서치어드바이저 + 구글 서치콘솔 이중 전략

| 플랫폼 | 등록 방법 | 주요 활용 기능 |
|--------|----------|--------------|
| **구글 서치콘솔** | HTML 태그 또는 DNS 인증 | 색인 현황, 검색 성능, Core Web Vitals, 링크 분석 |
| **네이버 서치어드바이저** | HTML 파일 업로드 또는 메타태그 | 수집 현황, 진단, C-Rank 모니터링 |

#### 구글 API 인덱싱 구현

```javascript
// Google Indexing API — 새 콘텐츠 즉시 색인 요청
// 일반 크롤링 대기(수일~수주) → API로 즉시 요청

const { google } = require('googleapis');

const auth = new google.auth.GoogleAuth({
  keyFile: 'service-account.json',
  scopes: ['https://www.googleapis.com/auth/indexing'],
});

async function requestIndexing(url) {
  const indexing = google.indexing({ version: 'v3', auth });
  await indexing.urlNotifications.publish({
    requestBody: {
      url: url,
      type: 'URL_UPDATED', // or 'URL_DELETED'
    },
  });
}

// 새 게시글 발행 후 자동 호출
requestIndexing('https://example.com/wiki/geo/new-page/');
```

---

## 6. Schema.org 구조화 데이터 전략

### 6.1 페이지 유형별 Schema 매핑표

| 페이지 유형 | 필수 Schema | 선택 Schema |
|------------|------------|------------|
| 홈페이지 | Organization, WebSite, SiteNavigationElement | LocalBusiness |
| 서비스 페이지 | Service, FAQPage, BreadcrumbList | HowTo, Review |
| 병과별 페이지 | MedicalBusiness, FAQPage, LocalBusiness | BreadcrumbList |
| 위키/가이드 | Article, FAQPage, BreadcrumbList | HowTo, WebPage |
| 블로그 포스트 | BlogPosting, BreadcrumbList | Person (저자) |
| 지역 랜딩 | LocalBusiness, FAQPage, BreadcrumbList | GeoCoordinates |
| FAQ 페이지 | FAQPage, BreadcrumbList | WebPage |
| 사례 연구 | Article, Organization | Review |

### 6.2 FAQPage Schema 예시 (병원 GEO 서비스 페이지)

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "GEO와 SEO의 차이는 무엇인가요?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "SEO(검색엔진 최적화)는 구글·네이버 등 전통적 검색엔진에서 상위에 노출되도록 최적화하는 전략이고, GEO(생성형 엔진 최적화)는 ChatGPT·Perplexity·Gemini 등 AI가 생성하는 답변에 인용되도록 최적화하는 전략입니다. 2026년 현재 두 전략은 상호 보완 관계로, 동시에 추진해야 최대 효과를 냅니다."
      }
    },
    {
      "@type": "Question",
      "name": "병원이 GEO를 적용하면 효과가 얼마나 빠르게 나타나나요?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "병원·전문직 업종은 GEO 효과가 가장 빠른 업종 중 하나입니다. AI 크롤러 접근성 최적화(llms.txt, robots.txt) 후 콘텐츠 제작 시작 시 빠르면 2~3개월 내 ChatGPT·Perplexity 답변에 인용 사례가 발생합니다. 평균적으로 6개월 내 안정적인 AI 트래픽 유입이 확인됩니다."
      }
    },
    {
      "@type": "Question",
      "name": "네이버에도 GEO가 적용되나요?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "네이버는 GPT 데이터 수집을 차단하고 있어, 네이버 AI 검색(네이버 CLOVA)에 최적화하려면 별도 전략이 필요합니다. 반면 구글 AI Overview는 GEO 전략과 동일하게 적용됩니다. 현재 국내 GEO 전략은 구글 AI Overview + ChatGPT + Perplexity 3개 채널을 중심으로 설계합니다."
      }
    }
  ]
}
```

### 6.3 LocalBusiness Schema (병원마케팅 대행사)

```json
{
  "@context": "https://schema.org",
  "@type": ["LocalBusiness", "ProfessionalService"],
  "name": "[회사명]",
  "description": "병원·의료 업종 전문 SEO·AEO·GEO 마케팅 대행사",
  "url": "https://example.com",
  "telephone": "02-0000-0000",
  "email": "info@example.com",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "강남구 테헤란로 000",
    "addressLocality": "서울",
    "addressRegion": "서울특별시",
    "postalCode": "06000",
    "addressCountry": "KR"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 37.5012,
    "longitude": 127.0396
  },
  "openingHoursSpecification": {
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
    "opens": "09:00",
    "closes": "18:00"
  },
  "sameAs": [
    "https://www.instagram.com/example",
    "https://blog.naver.com/example",
    "https://www.youtube.com/@example"
  ],
  "knowsAbout": ["병원마케팅", "의료 SEO", "GEO", "AEO", "병원 블로그"],
  "areaServed": {
    "@type": "Country",
    "name": "대한민국"
  }
}
```

### 6.4 HowTo Schema (GEO 구현 가이드 페이지)

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "병원 홈페이지 GEO 최적화 7단계",
  "description": "ChatGPT·Perplexity·Gemini AI 검색 답변에 병원이 인용되도록 최적화하는 방법",
  "totalTime": "P3M",
  "step": [
    {
      "@type": "HowToStep",
      "position": 1,
      "name": "AI 크롤러 접근성 확보",
      "text": "robots.txt에서 GPTBot, PerplexityBot 등 AI 크롤러를 명시적으로 허용하고, llms.txt 파일을 루트에 생성한다.",
      "url": "https://example.com/wiki/geo/#step1"
    },
    {
      "@type": "HowToStep",
      "position": 2,
      "name": "질문형 콘텐츠 구조 설계",
      "text": "환자들이 AI에게 실제로 묻는 질문을 수집하고, 각 질문에 대한 명확한 Answer-First 답변 콘텐츠를 설계한다.",
      "url": "https://example.com/wiki/geo/#step2"
    }
  ]
}
```

### 6.5 AI 크롤러 친화적 마크다운 콘텐츠 구조

AI는 HTML보다 **명확한 계층 구조**와 **마크다운 형태**를 선호한다. 워드프레스 기준 다음 규칙을 적용한다:

```markdown
# H1 — 페이지 당 1개, 타겟 키워드 포함

## H2 — 주요 섹션 (5~8개)

### H3 — 소섹션

**굵은 글씨** — 핵심 용어, AI 스캐닝 시 포착
- 리스트 활용 — AI 파싱에 유리
| 표 | 구조화 | 데이터 | — 비교 정보는 테이블로

> 인용구 블록 — 권위 있는 출처 인용 시

[내부링크](URL) — 관련 콘텐츠 연결
```

**AI 인용에 유리한 콘텐츠 패턴:**
1. 첫 단락에 핵심 답변 완결 (Executive Summary)
2. 정의문: "X는 Y이다" 형태의 명확한 문장
3. 숫자/통계 포함: "병원 업종 GEO 트래픽 15%"
4. 비교표: AI가 표를 텍스트로 파싱해 인용
5. 각 섹션 독립 완결성: H2 섹션만 읽어도 의미 파악 가능

---

## 7. 콘텐츠 SEO 전략 (토픽 클러스터)

### 7.1 Pillar Page 목록 및 전략

| Pillar Page | URL | 목표 키워드 볼륨 | 현재 경쟁 강도 |
|-------------|-----|----------------|--------------|
| GEO란 무엇인가 | /wiki/geo/ | 2,400/월 | 낮음 (신규 키워드) |
| 병원마케팅이란 | /wiki/hospital-marketing/ | 5,400/월 | 높음 |
| SEO란 무엇인가 | /wiki/seo/ | 18,000/월 | 매우 높음 |
| AEO란 무엇인가 | /wiki/aeo/ | 800/월 | 낮음 |
| 성형외과 마케팅 | /hospital-marketing/plastic-surgery/ | 1,900/월 | 중간 |
| 치과 마케팅 | /hospital-marketing/dental/ | 1,600/월 | 중간 |

### 7.2 Cluster Pages 키워드 맵 — GEO 클러스터

```
Pillar: /wiki/geo/ — "GEO란"

Cluster (정보형):
├── /wiki/geo/definition/         — "GEO 정의", "생성형 엔진 최적화"
├── /wiki/geo/vs-seo/             — "GEO SEO 차이"
├── /wiki/geo/chatgpt/            — "ChatGPT 검색 노출", "ChatGPT SEO"
├── /wiki/geo/perplexity/         — "Perplexity 최적화", "Perplexity 노출"
├── /wiki/geo/gemini/             — "Gemini AI 검색", "구글 AI Overview"
├── /wiki/geo/llms-txt/           — "llms.txt 만들기", "llms txt 설정"
├── /wiki/geo/ai-citation/        — "AI 인용 소스", "AI 답변 출처"
├── /wiki/geo/hospital/           — "병원 GEO", "의원 AI 검색 최적화"
└── /wiki/geo/zero-click/         — "제로클릭 시대", "제로클릭 SEO"

Cluster (비교형):
├── /wiki/geo/geo-vs-seo-vs-aeo/  — "GEO AEO SEO 비교"
└── /wiki/geo/tools/              — "GEO 모니터링 툴", "Otterly.ai"
```

### 7.3 E-E-A-T 강화 전략

**Experience (경험):**
- 실제 협력 병원 사례 데이터 공개 (익명 처리)
- 마케터의 직접 실행 과정 스크린샷 포함
- "OO 병원과 6개월 진행한 실제 결과" 형태

**Expertise (전문성):**
- 모든 위키 페이지에 저자 프로필 섹션
- 저자: SEO 자격증, 마케팅 경력, 관련 강의 이력
- 참고 문헌: Google 공식 문서, 학술 논문 링크

**Authoritativeness (권위성):**
- 언론 노출 섹션 (미디어 로고 표시)
- 업계 협회 가입 및 배지
- 게스트 포스팅: SEO/마케팅 전문 미디어 기고

**Trustworthiness (신뢰성):**
- HTTPS 적용 (필수)
- 개인정보처리방침 명확히
- 사업자 정보 footer 표시
- 리뷰/후기 Schema 적용

### 7.4 검색 의도 4유형별 콘텐츠 가이드

| 의도 유형 | 예시 키워드 | 콘텐츠 형태 | CTA |
|----------|------------|-----------|-----|
| **정보형** | "GEO란 무엇인가", "병원 SEO 방법" | 위키, 가이드, 블로그 | 뉴스레터 구독, 관련 글 |
| **탐색형** | "[회사명] 리뷰", "병원마케팅 대행사 추천" | 브랜드 페이지, 비교 글 | 상담 신청 |
| **거래형** | "병원 SEO 대행 가격", "GEO 서비스 신청" | 서비스 페이지, 가격표 | 지금 신청하기 |
| **비교형** | "병원마케팅 대행사 비교", "SEO vs GEO" | 비교 페이지, 표 | 무료 진단 |

---

## 8. AEO (Answer Engine Optimization) 전략

### 8.1 질문 수집 방법

#### 네이버 자동완성 질문 수집

```
검색창 입력: "병원 마케팅 ___"
수집 키워드 예시:
- 병원 마케팅 방법
- 병원 마케팅 비용
- 병원 마케팅 회사
- 병원 마케팅 전략
- 병원 마케팅 sns

"성형외과 ___" 자동완성:
- 성형외과 마케팅
- 성형외과 블로그
- 성형외과 SEO
- 성형외과 광고비
```

#### Google People Also Ask (PAA) 수집

```
구글 검색 "병원 마케팅" → PAA 박스 질문 수집:
Q: 병원 마케팅에 얼마나 투자해야 하나요?
Q: 병원 블로그 마케팅 어떻게 시작하나요?
Q: 네이버 vs 구글 중 병원에 더 효과적인 곳은?
Q: 병원 마케팅 대행사 선택 기준은?
```

#### AI 검색 질문 수집

```
ChatGPT·Perplexity에 직접 질문 → AI가 무엇을 묻는지 파악
"병원 마케팅에 대해 알려줘" → 추가 질문 패턴 분석

음성검색 패턴 (구어체):
- "강남 성형외과 마케팅 잘하는 데 어디야?"
- "병원 홈페이지 검색 상위 어떻게 해?"
- "AI가 병원 추천해줄 때 어디서 정보 가져와?"
```

### 8.2 역피라미드 콘텐츠 작성법

```
전통적 글쓰기 (역삼각형 반대):
배경 설명 → 부연 설명 → 핵심 결론

역피라미드 (AEO/GEO 최적화):
핵심 결론 → 근거 → 상세 설명

예시 — "병원 SEO 비용은 얼마인가?"

[역피라미드 적용]
병원 SEO 서비스 비용은 월 100만원~500만원 범위입니다. (핵심 답변)

비용 범위는 다음 요소에 따라 결정됩니다: (근거)
- 병원 규모 및 경쟁 강도
- 타겟 키워드 수
- 콘텐츠 제작 포함 여부

상세 가격 구조: (세부)
| 패키지 | 포함 내용 | 월 비용 |
|--------|----------|--------|
| 기본 | 기술SEO + 월 4편 | 100~200만원 |
| 표준 | +링크빌딩 | 200~350만원 |
| 프리미엄 | +GEO+AEO | 350~500만원 |
```

### 8.3 FAQ 페이지 설계 — 병과별

**성형외과 FAQ 페이지 (/faq/plastic-surgery/)**

```
총 30개+ FAQ, 카테고리별 분류:

[마케팅 전략]
Q: 성형외과는 네이버와 구글 중 어디에 집중해야 하나요?
A: 2026년 기준, 성형외과는 두 플랫폼 모두 중요합니다...

Q: 비포애프터 사진을 SEO에 활용할 수 있나요?
A: 의료광고 심의를 통과한 비포애프터는 ALT 태그와 Schema로...

[비용 관련]
Q: 성형외과 SEO 마케팅 비용은 얼마인가요?
Q: 광고 대비 SEO 투자 효율성은?

[기간/성과]
Q: 성형외과 SEO 효과는 몇 개월만에 나타나나요?
Q: 성형외과 GEO 도입 시 AI 트래픽이 얼마나 늘어나나요?

[법규/규제]
Q: 의료광고 심의 없이 올릴 수 있는 콘텐츠 범위는?
Q: 환자 후기를 홈페이지에 게시해도 되나요?
```

### 8.4 음성검색 최적화 — 구어체 롱테일 키워드

| 텍스트 키워드 | 음성검색 변환 | 콘텐츠 적용 |
|-------------|-------------|-----------|
| 병원 SEO | 병원 홈페이지 구글 상위 노출 방법 | H3 제목으로 활용 |
| GEO 서비스 | AI가 병원 추천할 때 노출되는 방법 | FAQ 질문으로 활용 |
| 성형외과 마케팅 비용 | 성형외과 마케팅 한 달에 얼마 들어 | 가격 페이지 도입부 |
| 병원마케팅 대행사 | 병원 마케팅 잘하는 회사 어디야 | 브랜드 설명 텍스트 |

---

## 9. GEO (Generative Engine Optimization) 전략

### 9.1 AI별 선호 콘텐츠 타입

| AI 플랫폼 | 선호 소스 | 선호 콘텐츠 형태 | 전략 |
|-----------|---------|---------------|-----|
| **ChatGPT** | 언론사, 위키피디아, 전문 사이트 | 권위 있는 정보 기사, 정의 중심 | 언론 기고 + 위키형 콘텐츠 |
| **Perplexity** | Wikipedia류, 학술 자료, 전문 블로그 | 출처 명확한 데이터, 비교 분석 | 데이터 인용 + 출처 명시 |
| **Gemini** | 구글 권위 사이트, Google Business | 구글 생태계 콘텐츠 | 구글 검색 상위 + GMB 최적화 |
| **네이버 AI** | 네이버 블로그·카페, 공식 사이트 | C-Rank 높은 콘텐츠 | 네이버 블로그 운영 + D.I.A |

> **중요 인사이트:** 86%의 상위 인용 소스가 ChatGPT·Perplexity·AI Overview 간 겹치지 않는다. 즉, 각 AI별 최적화가 별도로 필요하다.

### 9.2 AI 크롤러 접근성 최적화

#### AI 크롤러 차단 4가지 원인 및 해결

| 차단 원인 | 증상 | 해결 방법 |
|---------|------|---------|
| **robots.txt 차단** | GPTBot 등이 수집 못 함 | robots.txt에 명시적 허용 추가 |
| **페이지 속도 불량** | 크롤러 타임아웃 | LCP 2.5초 이내 최적화 |
| **JavaScript 의존 콘텐츠** | 콘텐츠 미파싱 | SSR(서버사이드렌더링) 또는 정적 HTML |
| **HTTPS 미적용** | 보안 경고로 수집 거부 | SSL 인증서 적용 (무료: Let's Encrypt) |

#### 페이지 속도 최적화 체크리스트

```
□ WEBP 이미지 변환 (PNG/JPG 대비 30~50% 용량 감소)
□ 이미지 레이지 로딩 (loading="lazy")
□ Hero 이미지 preload (loading="eager")
□ CSS/JS 파일 minify
□ Gzip/Brotli 압축 활성화
□ CDN 적용 (CloudFlare 무료 플랜도 효과적)
□ 서버 응답시간 TTFB < 200ms
□ 캐싱 설정 (정적 파일 1년, HTML 1일)
□ Google Fonts 로컬 호스팅 (외부 요청 제거)
□ 불필요한 플러그인 제거 (워드프레스 기준)
```

### 9.3 병원 전문직 GEO 특화 전략

병원·전문직이 GEO에서 유리한 구조적 이유:
1. **YMYL 신뢰성**: 의사 자격·경력이 E-E-A-T를 자연스럽게 충족
2. **질문 명확성**: "라섹 비용", "쌍꺼풀 회복기간" 등 질문이 구체적
3. **지역 특화**: 로컬 AI 답변 수요 높음
4. **경쟁 낮음**: 대부분 병원이 GEO 미적용 상태 — 선점 기회

#### 병원 GEO 콘텐츠 전략

```
[AI 답변에 인용되는 병원 콘텐츠 패턴]

1. 시술별 명확한 정의 페이지
   "/wiki/라섹이란/" — "라섹은 레이저로 각막 표면을 절제하는..."
   → ChatGPT "라섹이 뭐야?" 질문 시 인용 타겟

2. 비용 투명 공개 페이지
   "/wiki/쌍꺼풀-비용/" — 범위 명시, 변동 요인 설명
   → Perplexity 가격 답변 시 인용 타겟

3. 비교 분석 페이지
   "/wiki/라섹-vs-라식/" — 표 형태 비교
   → 구글 AI Overview 비교 답변 시 인용 타겟

4. 의사 전문가 칼럼
   "/blog/원장명-라섹-10년-경험/" — 저자 명시, 전문성 증명
   → E-E-A-T 강화, ChatGPT 전문가 답변 인용
```

### 9.4 인용 가능한 통계·데이터 자체 생산 전략

AI가 가장 잘 인용하는 콘텐츠는 **독창적 데이터**다. 대행사 자체 데이터를 생산하는 방법:

| 데이터 생산 방법 | 예시 | 활용 |
|--------------|-----|-----|
| **협력 병원 집계** | "협력 병원 50개 분석: SEO 도입 후 평균 트래픽 230% 증가" | Pillar Page 도입부 통계 |
| **키워드 분석 리포트** | "2026 병원 업종 검색 키워드 트렌드 분석" | 연간 리포트 발행 |
| **A/B 테스트 결과** | "FAQ Schema 적용 전후 CTR 비교: +45%" | 위키 근거 데이터 |
| **설문 조사** | "병원 원장 100명 설문: 마케팅 고민 1위는?" | 블로그 + 언론 배포 |
| **AI 인용률 추적** | "국내 병원 중 ChatGPT 인용 사례 분석" | GEO 효과 증명 자료 |

---

## 10. 링크빌딩 전략

### 10.1 병원 업종 특화 백링크 확보

| 링크 유형 | 방법 | 효과 | 리스크 |
|---------|-----|-----|-------|
| **Organic 백링크** | 고품질 콘텐츠로 자연 인용 | 최고 | 없음 |
| **Guest Post** | 의료·마케팅 전문 미디어 기고 | 높음 | 낮음 |
| **언론 배포** | PR 뉴스와이어, 뉴시스 등 | 높음 | 낮음 |
| **PBN** | 자체 운영 블로그 네트워크 | 중간 | 중간 |
| **경매 도메인** | 기존 백링크 보유 도메인 구매 | 중간~높음 | 중간 |
| **Black Hat** | 스팸 링크, 링크 구매 | 단기 | 매우 높음 (패널티) |

**병원 마케팅 대행사에 최적화된 링크 확보처:**

```
[의료/헬스케어 미디어]
- 청년의사 (docdocdoc.co.kr)
- 메디칼타임즈 (medicaltimes.com)
- 데일리메디 (dailymedi.com)
- 헬스조선 (health.chosun.com)
- 코메디닷컴 (kormedi.com)

[마케팅/IT 미디어]
- 마케팅 트렌드 미디어
- 스타트업 미디어 (platum.kr)
- 브런치 스토리 (brunch.co.kr)

[업종 커뮤니티]
- 의사랑 (doctorsnews.co.kr) 기고
- 병원 원장 커뮤니티 링크
```

### 10.2 언론홍보를 통한 권위 백링크

```
언론 배포 콘텐츠 유형 (병원 마케팅 대행사 관점):

1. 데이터 리포트
   제목: "2026 병원마케팅 트렌드: AI 검색이 바꾼 환자 탐색 행동"
   배포: PR 뉴스와이어 → 의료 전문지 픽업 목표

2. 전문가 코멘트 제공
   의료 AI 기사에 전문가 인터뷰 → 기사 내 출처 링크

3. 수상/인증 획득
   마케팅 어워드 수상 → 수상 기관 사이트 링크

4. 협업 케이스 스터디 공동 발행
   협력 병원과 공동으로 성과 사례 발행 → 병원 사이트 상호 링크
```

### 10.3 내부링크 구조 설계 (토픽 클러스터 연결)

```
내부링크 우선순위:

1순위: 서비스 페이지 → 상담 신청 (전환 경로)
2순위: 위키 Cluster → Pillar (권위 집중)
3순위: 블로그 → 위키/서비스 (트래픽 이동)
4순위: 위키 Pillar → 서비스 (구매 연결)

링크 수량 기준:
- 2,000자 이내 글: 내부링크 3~5개
- 2,000~5,000자: 내부링크 5~10개
- 5,000자+: 내부링크 10~15개

앵커 텍스트 다양화:
✓ "GEO 서비스 자세히 보기" (CTA형)
✓ "생성형 엔진 최적화" (키워드형)
✓ "이 가이드에서 확인하세요" (자연어형)
✗ "여기를 클릭" (비권고)
✗ 동일 앵커 텍스트 반복 (비권고)
```

### 10.4 네이버 vs 구글 백링크 전략 분리

| 구분 | 네이버 | 구글 |
|------|--------|------|
| **핵심 지표** | C-Rank (채널 신뢰도) | PageRank (링크 권위) |
| **효과적 링크** | 네이버 블로그 이웃 공감, 카페 | 외부 .kr 도메인, 언론사 |
| **전략** | 네이버 블로그 운영 + 이웃 확보 | 언론 + Guest Post + Organic |
| **속도** | 빠름 (2~4주) | 느림 (2~6개월) |
| **지속성** | 낮음 (알고리즘 변화 빠름) | 높음 (장기 효과) |

---

## 11. 콘텐츠 발행 루틴 & 자동화

### 11.1 10단계 콘텐츠 발행 루틴

```
단계 1: 키워드 서치
  도구: 네이버 키워드 플래너, Google Keyword Planner, Ahrefs/Semrush
  기준: 월간 검색량 100+, 경쟁도 중간 이하, 우리 사이트 토픽 연관

단계 2: 경쟁 분석
  상위 5개 페이지 분석: 글자수, H2 구조, FAQ 수, 내부링크 패턴
  Intent Gap 발굴: 경쟁사가 다루지 않는 각도 찾기

단계 3: 콘텐츠 작성
  구조: Answer-First → H2별 심화 → FAQ → CTA
  분량: 최소 1,500자 (위키: 3,000자+)
  E-E-A-T: 저자 명시, 출처 인용, 실제 데이터 포함

단계 4: 썸네일 제작
  규격: 1200×628px (OG Image)
  형식: WEBP
  포함: 제목 텍스트, 브랜드 로고
  Alt 텍스트: 키워드 포함

단계 5: 영문 버전 생성 (N-to-W 전략)
  한국어 → AI 번역 → 영문 검토 → 워드프레스 .com 발행
  목적: 구글 글로벌 색인 + GEO 영문 인용 노출

단계 6: 구글 서치콘솔 등록
  방법: URL 검사 → 색인 요청
  또는: Google Indexing API 자동화

단계 7: 네이버 서치어드바이저 등록
  방법: 웹마스터 도구 → 웹 페이지 수집 → URL 수집 요청

단계 8: 백링크 확보
  신규 게시글 발행 → 관련 커뮤니티·SNS 공유
  기존 관련 글에서 내부링크 추가

단계 9: 순위 체크
  도구: Google Search Console, 네이버 서치어드바이저
  주기: 발행 후 2주, 1개월, 3개월

단계 10: 리라이팅 / 업데이트
  기준: 30위 이내 진입했으나 10위 미진입 시
  방법: 콘텐츠 보강 + FAQ 추가 + 내부링크 강화
```

### 11.2 N-to-W 전략 (네이버→워드프레스)

```
목적: 네이버에서 성과 검증된 주제를 구글용 워드프레스로 재발행

프로세스:
1. 네이버 블로그 포스팅 → 조회수 기준 상위 20% 선별
2. 선별된 주제를 워드프레스에 심화 버전으로 재작성
3. 네이버 버전에서 워드프레스 버전으로 링크 추가
4. 영문 버전도 함께 발행 (GEO 영어권 노출)

장점:
- 네이버 성과 데이터로 주제 검증 후 투자
- 구글 SEO + GEO 동시 공략
- 기존 콘텐츠 자산 활용 효율화
```

### 11.3 프로그래매틱 SEO — 지역×병과 조합 페이지

```
공식: [지역] × [병과] = 대량 랜딩 페이지

예시 조합:
강남 × 성형외과 = /local/gangnam/plastic-surgery/
강남 × 피부과   = /local/gangnam/dermatology/
강남 × 치과     = /local/gangnam/dental/
...
부산 × 성형외과 = /local/busan/plastic-surgery/

전국 주요 도시 20개 × 병과 10개 = 200개 랜딩 페이지

구현 방식 (워드프레스):
- ACF(Advanced Custom Fields) + 커스텀 포스트 타입
- 지역·병과 데이터 스프레드시트 → API 연동 자동 생성
- 각 페이지: 지역 특화 내용 + 공통 서비스 설명 조합

품질 유지 기준:
- 각 페이지 최소 500자 고유 콘텐츠 (지역 데이터 포함)
- 복사 붙여넣기 페이지 금지 → 구글 중복 콘텐츠 페널티
- 대표 도시(서울, 강남, 부산 등)는 2,000자+ 심화 콘텐츠
```

### 11.4 AI 콘텐츠 활용 가이드

**Google AI 콘텐츠 페널티 없음 근거:**

Google의 공식 입장 (2023년 발표):
> "우리는 콘텐츠가 어떻게 생산됐는지가 아니라, 콘텐츠가 얼마나 유용한지를 기준으로 평가한다."

60만 페이지 분석 결과: AI 생성 콘텐츠와 인간 작성 콘텐츠 간 순위 차이 없음

**AI 콘텐츠 활용 원칙:**

```
✓ AI를 초안 작성 도구로 활용 (Draft)
✓ 전문가(마케터/의사)가 검수·보완
✓ 실제 데이터와 경험 추가 (E-E-A-T)
✓ 사실 관계 확인 (Fact Check)

✗ AI 생성 그대로 발행 (품질 저하)
✗ 동일 내용 대량 복제 (중복 콘텐츠)
✗ 의료 정보 미검수 발행 (법적 리스크)
```

**추천 AI 콘텐츠 워크플로:**

```
1. 키워드 + 경쟁사 분석 → AI 프롬프트 작성
2. AI (Claude/GPT-4) → 초안 생성
3. 마케터 → 구조 검토, 차별화 포인트 추가
4. 의료 관련 내용 → 의사/전문가 검수
5. 편집자 → 가독성, 내부링크, CTA 추가
6. 발행 → 성과 모니터링
```

---

## 12. 성과 측정 & KPI 체계

### 12.1 분석 도구 연동 체계

```
데이터 수집 레이어:
┌─────────────────────────────────────────────┐
│  GA4 (Google Analytics 4)                   │
│  → 전체 트래픽, 전환율, 사용자 행동        │
├─────────────────────────────────────────────┤
│  Google Search Console                      │
│  → 검색 노출, CTR, 순위, 색인 현황        │
├─────────────────────────────────────────────┤
│  네이버 서치어드바이저                       │
│  → 네이버 수집 현황, 검색 유입             │
├─────────────────────────────────────────────┤
│  Otterly.ai / Peec.ai                       │
│  → AI 검색(ChatGPT·Perplexity) 인용 추적  │
└─────────────────────────────────────────────┘
```

### 12.2 월간 KPI 대시보드

| KPI 카테고리 | 지표 | 측정 도구 | 목표 (6개월) |
|------------|-----|---------|------------|
| **SEO** | 구글 상위 10위 키워드 수 | GSC | 50개+ |
| **SEO** | 구글 유기 트래픽 (월) | GA4 | 5,000세션+ |
| **SEO** | 네이버 유기 트래픽 (월) | 서치어드바이저 | 3,000세션+ |
| **AEO** | Featured Snippet 획득 수 | GSC | 10개+ |
| **GEO** | ChatGPT 인용 횟수 | Otterly.ai | 20회+/월 |
| **GEO** | AI 검색 유입 트래픽 | GA4 (referrer) | 전체의 10%+ |
| **전환** | 상담 신청 수 (월) | GA4 | 30건+ |
| **기술** | Core Web Vitals 통과율 | GSC | 90%+ |
| **링크** | 신규 백링크 (월) | GSC | 10개+ |
| **콘텐츠** | 신규 페이지 발행 수 (월) | CMS | 20페이지+ |

### 12.3 SEO→AEO→GEO 단계별 성과 지표

```
월별 성과 체크포인트:

[1~2개월 — 기초 구축]
□ Technical SEO 완료 (robots, sitemap, llms.txt)
□ Core Web Vitals LCP < 2.5s 달성
□ Schema 구조화 데이터 전 페이지 적용
□ 구글/네이버 서치콘솔 등록 완료
□ 초기 20개 페이지 발행

[3~4개월 — SEO 성과]
□ 구글 신규 키워드 노출 100개+
□ 롱테일 키워드 10위 이내 진입 10개+
□ 네이버 블로그 일 방문자 100명+
□ 백링크 20개+ 확보

[5~6개월 — AEO 성과]
□ Featured Snippet 5개+ 획득
□ 구글 PAA(People Also Ask) 노출 10개+
□ 월간 유기 트래픽 5,000세션 달성

[7~12개월 — GEO 성과]
□ ChatGPT 인용 확인 (Otterly.ai)
□ Perplexity 검색 인용 10개+
□ AI 트래픽 전체의 10~15% 달성
□ 월 상담 신청 50건+ 달성
```

---

## 13. 도메인 & 기술 인프라 권고사항

### 13.1 도메인 선정 기준

| 기준 | 권고 | 근거 |
|------|------|------|
| **도메인 연령** | 1년 이상 사용 이력 | 1년 미만 도메인 10위 이내 확률 4% 미만 |
| **스팸 지수** | 30% 미만 (Moz Spam Score 기준) | 고스팸 도메인은 구글 신뢰도 하락 |
| **도메인 유형** | PMD(Partial Match Domain) 권고 | EMD는 과최적화 리스크, 브랜드+키워드 조합 |
| **TLD** | .co.kr 또는 .com | 한국 시장은 .co.kr 신뢰도 높음 |
| **이전 소유자** | 확인 필수 | 이전 스팸 이력 승계 위험 |

**도메인 구매 전 체크 도구:**
- Moz Link Explorer (스팸 점수 확인)
- Ahrefs (백링크 이력)
- Wayback Machine (이전 사이트 내용)
- Google 검색 `site:도메인.com` (인덱싱 상태)

**샌드박스 현상 대응:**
신규 도메인은 구글이 3~6개월간 인위적으로 순위를 낮추는 샌드박스 현상 적용. 기존 도메인 활용이나 PBN 도메인 활용으로 우회 가능.

### 13.2 CMS 비교 및 병원 마케팅 대행사 최적 선택

| CMS | SEO | 속도 | 커스텀 | 유지보수 | 비용 | 병원 마케팅 적합성 |
|-----|-----|------|--------|---------|------|-----------------|
| **WordPress** | ★★★★★ | ★★★ | ★★★★★ | ★★★ | 저 | **최고** |
| **Ghost** | ★★★★ | ★★★★★ | ★★★ | ★★★★ | 중 | 블로그 위주 적합 |
| **아임웹** | ★★★ | ★★★ | ★★ | ★★★★★ | 중 | 중소 병원 적합 |
| **Gatsby/Next.js** | ★★★★★ | ★★★★★ | ★★★★★ | ★★ | 고 | 대형 프로젝트 |

**권고: WordPress (Headless 구성)**

이유:
1. Yoast SEO / Rank Math — 가장 강력한 SEO 플러그인
2. Schema Pro — 구조화 데이터 자동화
3. WP Rocket — 속도 최적화
4. ACF(Advanced Custom Fields) — 프로그래매틱 SEO 구현
5. 전 세계 SEO 생태계 표준 — 레퍼런스 풍부

**추천 워드프레스 플러그인 스택:**

```
SEO: Rank Math Pro (Schema + 사이트맵 + 리다이렉트)
속도: WP Rocket + Imagify (WEBP 자동 변환)
보안: Wordfence + SSL (Let's Encrypt)
스키마: Schema Pro
분석: MonsterInsights (GA4 연동)
형식: ACF Pro (커스텀 필드)
캐시: W3 Total Cache 또는 WP Super Cache
```

### 13.3 호스팅 권고사항

| 용도 | 권고 호스팅 | 이유 |
|------|-----------|------|
| **초기 (트래픽 < 1만/월)** | Cloudways (Vultr) | 가성비, 속도, 관리 편의 |
| **성장기 (1만~10만/월)** | Kinsta 또는 WP Engine | 워드프레스 전용, CDN 포함 |
| **대형 (10만+/월)** | AWS + CloudFront | 완전 제어, 확장성 |

**필수 인프라:**
```
□ CDN: CloudFlare (무료 플랜도 효과적)
□ SSL: Let's Encrypt (무료) 또는 유료 SSL
□ 백업: 일별 자동 백업 (UpdraftPlus)
□ 모니터링: UptimeRobot (다운타임 알림)
□ 보안: Wordfence + 2FA
```

---

## 14. 추가 권고 사항

### 14.1 제로클릭 시대에 자체 플랫폼이 필수인 이유

```
제로클릭 시대의 패러독스:
"클릭이 줄어도, AI 답변 소스가 되면 오히려 더 많이 노출된다"

기존 광고 의존 모델의 문제:
┌─────────────────────────────────────────────┐
│ 클릭당 광고비 지출 → 클릭 발생 → 방문      │
│ AI 검색 확산 → 클릭 자체 감소              │
│ → 광고 효율 급락 → 비용 증가 악순환        │
└─────────────────────────────────────────────┘

자체 플랫폼(SEO+AEO+GEO) 모델의 강점:
┌─────────────────────────────────────────────┐
│ 콘텐츠 한 번 작성 → 영구 노출              │
│ AI 인용 소스 → 클릭 없이도 브랜드 노출     │
│ → 신뢰 형성 → 직접 방문 (Direct 트래픽)   │
│ → 광고비 절감 + 트래픽 증가 선순환        │
└─────────────────────────────────────────────┘
```

### 14.2 2026~2028 AI 마케팅 트렌드 대응 로드맵

| 기간 | 트렌드 | 대응 전략 |
|------|--------|---------|
| **2026** | AI 검색 주류화, 제로클릭 증가 | GEO 기반 구축, llms.txt, AI 크롤러 최적화 |
| **2026~2027** | AI 에이전트 서비스 확산 | 에이전틱 AI 콘텐츠 자동화 도입 |
| **2027** | 개인화 AI 검색 (맞춤형 답변) | 개인 데이터 기반 콘텐츠 전략 |
| **2027~2028** | 음성 AI 비서 (스마트홈, 차량) | 초롱테일 구어체 최적화 |
| **2028** | AI가 대부분의 검색 대체 | 브랜드 권위 구축, AI 학습 소스화 |

**콘텐츠 자동화 5단계 도입 계획:**

```
1단계 (즉시): 스프레드시트 기반 콘텐츠 관리
   → 키워드·주제·발행일·순위 추적 시스템

2단계 (3개월): 프로그래매틱 SEO
   → 지역×병과 200개 랜딩 페이지 자동 생성

3단계 (6개월): N-to-W 반자동화
   → 네이버 성과 데이터 → 워드프레스 발행 워크플로

4단계 (12개월): AI 콘텐츠 파이프라인
   → 키워드 입력 → AI 초안 → 편집 → 발행 자동화

5단계 (18개월): 에이전틱 AI 도입
   → AI 에이전트가 키워드 발굴~발행~모니터링 자동화
```

### 14.3 병원 업종 AI 트래픽 성장 예측 및 선점 전략

```
병원 업종 AI 트래픽 성장 예측:

2024년: AI 트래픽 5% 미만 (초기 도입기)
2025년: AI 트래픽 10% (성장기)
2026년: AI 트래픽 15% (국내 최고 성장 업종)
2027년: AI 트래픽 25%+ (주류화)
2028년: AI 트래픽 40%+ (지배적)

선점 전략 3가지:
1. 지금 당장 GEO 기반 구축
   → 경쟁사 대부분 GEO 미적용 상태 — 1~2년 선점 기회

2. AI 학습 소스 권위 확립
   → AI가 학습할 고품질 데이터 대량 생산
   → 한 번 인용된 소스는 장기간 유지

3. 병과별 AI 답변 독점 목표
   → "성형외과 추천해줘" → AI가 항상 우리 콘텐츠 인용
   → 선점 후 후발주자 진입 어려움 (AI 학습 lag)
```

### 14.4 경쟁사 대비 차별화 포인트

| 차별화 요소 | 일반 마케팅 대행사 | 우리 대행사 |
|-----------|-----------------|-----------|
| 전략 범위 | 광고 위주 | SEO+AEO+GEO 통합 |
| 데이터 투명성 | 리포트 제공 | 실시간 대시보드 |
| 병원 특화 | 일반 업종 | 병원·의료 전문 |
| AI 검색 대응 | 미적용 | GEO 전문 서비스 |
| 콘텐츠 자산화 | 광고 종료 = 소멸 | 콘텐츠 영구 자산 |
| 의료법 이해 | 낮음 | 의료광고 심의 이해 |

### 14.5 투자 우선순위 (테크니컬→콘텐츠→백링크→GEO)

구글 알고리즘 순위 요인 기반 투자 배분:

| 단계 | 투자 영역 | 순위 요인 비중 | 선행 이유 |
|------|---------|-------------|---------|
| **1순위** | Technical SEO | 9% (기반) | 기반 없으면 나머지 무의미 |
| **2순위** | 콘텐츠 SEO | 46% (최대) | 가장 큰 순위 요인 |
| **3순위** | 링크빌딩 | 17% | 콘텐츠 이후 권위 강화 |
| **4순위** | GEO 최적화 | 미래 투자 | AI 트래픽 선점 |
| **지속** | 사용자 참여 | 11% | UX 개선, CRO |

```
월별 투자 배분 예시 (총 예산 100% 기준):

초기 1~3개월:
  Technical SEO: 40%
  콘텐츠 제작: 40%
  링크빌딩: 10%
  GEO 설정: 10%

성장기 4~6개월:
  콘텐츠 제작: 50%
  링크빌딩: 25%
  GEO 콘텐츠: 15%
  Technical 유지: 10%

안정기 7개월+:
  콘텐츠 제작: 40%
  링크빌딩: 20%
  GEO 심화: 25%
  AEO 최적화: 15%
```

---

## 부록: 실행 체크리스트

### 론칭 전 Technical SEO 체크리스트

```
□ HTTPS 적용 확인
□ robots.txt 설정 (AI 크롤러 허용)
□ sitemap.xml 생성 및 GSC 제출
□ llms.txt 생성 및 루트 업로드
□ Google Search Console 등록
□ 네이버 서치어드바이저 등록
□ GA4 설치 및 전환 이벤트 설정
□ Core Web Vitals 측정 (목표: LCP<2.5s)
□ 모바일 반응형 확인
□ 이미지 전체 WEBP 변환
□ 레이지 로딩 적용
□ Schema 구조화 데이터 검증 (Google Rich Results Test)
□ 내부링크 구조 검토 (고아 페이지 없음)
□ 브레드크럼 전 페이지 적용
□ 404 페이지 커스텀 설정
□ 리다이렉트 맵 (www → non-www 또는 반대)
```

### 콘텐츠 발행 체크리스트 (매 게시글)

```
□ 타겟 키워드 H1에 포함
□ Answer-First 도입부 (200자 이내)
□ H2: 5~8개, H3: 각 H2 하단 2~4개
□ 최소 1,500자 (위키: 3,000자+)
□ FAQ 섹션 (최소 5개 Q&A)
□ 내부링크 최소 3개
□ 외부 권위 소스 인용 1~2개
□ 이미지 alt 텍스트 키워드 포함
□ OG Image (1200×628px, WEBP)
□ Meta Description (150자 이내, 키워드+CTA)
□ Schema 타입 적용 (Article 또는 FAQPage)
□ 저자 정보 명시
□ 발행일/수정일 표시
□ GSC URL 색인 요청
□ 네이버 URL 수집 요청
```

---

*본 기획서는 2026년 6월 기준 SEO·AEO·GEO 최신 트렌드를 반영하여 작성되었습니다.*
*전략적 환경 변화에 따라 분기별 업데이트를 권장합니다.*
