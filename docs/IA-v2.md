# 베놈 사이트 v2 — 정보구조(IA) 재편 블루프린트

> 목적: "흩어진 페이지 → 의도한 사이트맵으로 재편". 실측(index.html #pg-*, vercel.json rewrites,
> 홈페이지 제작 최종 사이트맵.txt) 기준. **이 문서는 구현 청사진** — SPA/디자인은 파킹, 코드 미변경.
> 상태 범례: ✅ 구현(전용 #pg-*) · 🟡 라우트만(콘텐츠 없음, index로 폴백) · ⬜ 미정의

---

## 1. 목표 내비게이션 (5 메인 + 유틸)

```
병원마케팅-베놈 (Home /)
├─ 1. 병원마케팅            /hospital-marketing
│   ├─ 의료광고심의         /medical-ad-review
│   ├─ 치과                /dental      (+ 임플란트 /implant · 교정 /orthodontics)
│   ├─ 피부과              /dermatology
│   ├─ 정형외과            /orthopedics
│   ├─ 한의원              /oriental-medicine
│   ├─ 성형외과            /plastic-surgery
│   ├─ 내과                /internal-medicine
│   ├─ 안과                /ophthalmology
│   └─ 의료기기            /medical-device
├─ 2. AI마케팅             /ai
│   ├─ GEO                 /geo         (란?·프로세스·효과)
│   ├─ AEO                 /aeo
│   └─ SEO                 /seo         (콘텐츠·테크니컬·링크빌딩) + 용어사전 /seo-dictionary
├─ 3. 병원홈페이지 제작     /website     (기본형·중급형·고급형)
├─ 4. 온라인마케팅         /online-marketing
│   ├─ 검색광고            /naver-ads (파워링크·파워컨텐츠·브랜드검색·플레이스) · /google-ads
│   ├─ SNS·앱광고          /channel-management
│   ├─ 언론                /pr
│   └─ 브랜드마케팅        /online-marketing/branding
└─ 5. 블로그               /blog
    ├─ 칼럼               (인사이트·팁·노하우·소식·트렌드·SEO·GEO·AEO)
    └─ 지역마케팅          (인천·대전·대구·울산·부산·광주)

유틸: 무료진단 /diagnose · 문의하기 /contact · 회사소개 /about · 개인정보 /privacy · 이용약관 /terms
```

---

## 2. 현재 ↔ 목표 매핑 (실측)

| 목표 페이지 | 라우트 | 현재 #pg-* | 상태 |
|-----------|--------|-----------|:--:|
| 홈 | `/` | `pg-home` | ✅ |
| 병원마케팅(허브) | `/hospital-marketing` | `pg-hospital` | ✅(제네릭) |
| 진료과별(치과·피부과·정형·한의원·성형·내과·안과) | `/dental` 등 | — | 🟡 라우트만 |
| 의료광고심의 | `/medical-ad-review` | — | 🟡 |
| 의료기기 | `/medical-device` | — | 🟡 |
| AI마케팅(허브) | `/ai` | `pg-ai` | ✅ |
| GEO / AEO / SEO | `/geo` `/aeo` `/seo` | `pg-geo` `pg-aeo` `pg-seo` | ✅ |
| SEO 용어사전 | `/seo-dictionary` | `pg-seo-dict` | ✅ |
| 병원홈페이지 제작 | `/website` | — | 🟡 |
| 온라인마케팅(허브) | `/online-marketing` | `pg-services`(추정) | 🟡 |
| 검색광고/SNS/언론 | `/naver-ads` `/google-ads` `/channel-management` `/pr` | — | 🟡 |
| 블로그 / 글 | `/blog` `/blog/:slug` | `pg-blog` `pg-blog-post` | ✅ |
| 무료진단 | `/diagnose` | `pg-diagnose` | ✅ |
| 문의 / 회사소개 / 개인정보 / 약관 | `/contact` `/about` `/privacy` `/terms` | `pg-contact` `pg-about` `pg-privacy` `pg-terms` | ✅ |
| (범용 상세 템플릿) | — | `pg-detail` | ✅ |

**요지:** 클린 URL 라우트(vercel.json)는 **목표 구조대로 이미 넓게 준비**돼 있으나,
**진료과별·서비스 서브 페이지의 전용 콘텐츠(#pg-*)가 없어 index로 폴백**된다(=SEO·전문성 손실 지점).

---

## 3. 갭 & 우선순위 (구현 순서)

| 순위 | 갭 | 이유 |
|:--:|----|------|
| **P4-1** | **진료과별 페이지**(dental·dermatology·orthopedics·oriental-medicine·plastic-surgery·internal-medicine·ophthalmology) | 전환·지역 SEO 직결. 원장 검색 진입점. **최우선** |
| P4-2 | 온라인마케팅 서브(naver-ads·google-ads·channel-management·pr) | 서비스 라인업 명확화 |
| P4-3 | 병원홈페이지 제작 `/website`(기본·중급·고급) | 별도 상품 라인 |
| P4-4 | 의료광고심의·의료기기 | 롱테일 전문성 |

**구현 방식 제안(비파괴):** 새 #pg-*를 매번 손코딩하지 말고 **`pg-detail` 범용 템플릿 + 데이터(진료과 config)** 로
렌더 → 진료과 7개를 한 템플릿으로 생성(취합 원칙). 각 페이지 고유 H1·FAQ·지역 스니펫만 데이터로 주입.

---

## 4. 라우트/URL 규칙 (canonical — vercel.json 기준)

- 최상위: `ai|geo|aeo|seo|hospital-marketing|online-marketing|website|about|blog|contact|seo-dictionary|diagnose|privacy|terms|naver-ads|google-ads|channel-management|pr`
- 진료과: `dental|implant|orthodontics|dermatology|orthopedics|oriental-medicine|plastic-surgery|internal-medicine|ophthalmology|medical-ad-review|medical-device` (+ `/:sub`)
- 블로그: `/blog/:slug`
- 전부 SPA 클라이언트 라우팅(`index.html` 폴백) — **라우트 추가 시 vercel.json + sitemap.xml 동시 갱신**

---

## 5. 취합·정리 원칙

1. **제네릭 → 분화**: `pg-hospital`(병원마케팅 제네릭)은 **허브**로 두고, 진료과별은 **템플릿+데이터**로 분화.
2. **AI마케팅 그룹핑**: `ai/geo/aeo/seo/seo-dictionary`를 "AI마케팅" 한 메뉴 하위로 IA 상 묶기(현재 개별 산재).
3. **진단 단일 목적지**: 모든 페이지 CTA는 `/diagnose`(무료 AI 노출 진단, 리드폼→Airtable P2) 하나로.
4. **블로그 택소노미**: 칼럼(8) + 지역(6) 태그 체계를 글 메타에 정착 → 지역 SEO.
5. **sitemap/robots 동기화**: 페이지 신설 시 `sitemap.xml`·`llms.txt` 자동 반영(sitemap-builder 활용).

---

## 6. 다음 액션 (승인 시)
- **P4-1** 진료과 7페이지를 `pg-detail` 템플릿 + 진료과 config로 일괄 생성(비파괴, 라우트 이미 존재).
- 랜딩 디자인 재개 시 상단 GNB를 위 5-메인 구조로 정렬.
