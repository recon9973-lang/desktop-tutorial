# 베놈 마케팅 웹사이트 — 세션 인수인계 문서

> 마지막 업데이트: 2026-06-25  
> 브랜치: `claude/nice-cray-94p4hx`  
> 배포: `https://desktop-tutorial-chi-peach.vercel.app/`

---

## 파일 구조

```
/home/user/desktop-tutorial/
├── venom-wordpress/preview/
│   ├── index.html          ← 메인 SPA (모든 페이지 포함, ~414KB)
│   └── admin.html          ← 관리자 페이지 (블로그 포스팅·통계 등)
├── robots.txt              ← AI 크롤러 허용 설정
├── sitemap.xml             ← 사이트맵
├── vercel.json             ← Vercel 배포 설정
├── VENOM_PROJECT_SUMMARY.md ← 이전 세션 요약 (기술 참고용)
└── VENOM_SESSION_HANDOFF.md ← 이 파일
```

---

## SPA 라우팅 구조

### `sp(id)` — 최상위 페이지 전환
| ID | 페이지 |
|---|---|
| `home` | 홈 (랜딩) |
| `ai` | AI마케팅 허브 (GEO/AEO/SEO 탭) |
| `geo` | GEO 상세 |
| `aeo` | AEO 상세 |
| `seo` | SEO 상세 |
| `hosp_mkt` | 병원마케팅 카테고리 |
| `services` | 온라인마케팅 |
| `hospital` | 병원홈페이지 제작 |
| `blog` | 블로그 목록 |
| `blog-post` | 블로그 포스트 |
| `contact` | 문의/상담 |
| `detail` | 진료과목 상세 (ld()가 여기에 로드) |

### `ld(cat)` — 진료과목 상세 페이지 (`pages` 객체에서 로드)
| cat | 과목 |
|---|---|
| `dental` | 치과마케팅 |
| `implant` | 임플란트마케팅 |
| `ortho_dental` | 교정마케팅 |
| `skin` | 피부과마케팅 |
| `ortho` | 정형외과마케팅 |
| `oriental` | 한의원마케팅 |
| `plastic` | 성형외과마케팅 |
| `naegwa` | 내과마케팅 |
| `angwa` | 안과마케팅 |
| `shimui` | 의료광고심의 |
| `medical_device` | 의료기기마케팅 |

---

## 완료된 작업 목록 ✅

### 구조/기능
- [x] SPA 라우팅 (`sp`, `ld`) 완성
- [x] 사이드바 네비게이션 모든 과목 완성
- [x] localStorage 블로그 포스팅 (admin.html)
- [x] robots.txt — GPTBot, ClaudeBot, PerplexityBot, Google-Extended 허용
- [x] sitemap.xml 생성
- [x] vercel.json 헤더 설정

### Schema.org 구조화 데이터
- [x] LocalBusiness + MedicalBusiness (홈페이지 헤드)
- [x] FAQPage — GEO 페이지
- [x] FAQPage — AEO 페이지
- [x] FAQPage — SEO 페이지
- [x] FAQPage — 치과/피부과/병원 홈페이지 통합 (추가됨)

### 콘텐츠
- [x] 진료과목 14개 pages 객체 완성 (dental, skin, ortho, oriental, plastic, naegwa, angwa, shimui, medical_device, implant, ortho_dental)
- [x] 각 과목 5개 필수 조건 섹션 (ortho, plastic)
- [x] 원장 관점 현실 사례 — 치과 3건, 피부과 3건, 정형외과 2건, 성형외과 2건, 내과 2건, 안과 2건, 한의원 2건
- [x] 온라인마케팅 페이지 — 카카오/구글 광고, 콘텐츠 전략, ROI 계산기 추가
- [x] 병원홈페이지 페이지 — 레퍼런스 사이트 섹션 (대형병원/강남클리닉/지역개원의), 10가지 공통 요소
- [x] 블로그 포스트 풀텍스트 (geo1, geo2, aeo1, seo1, seo2)
- [x] CTA 버튼 전체 "상담신청"/"카카오상담" 통일

### 미완료 / 사용자 제공 필요 ❌
- [ ] YouTube Shorts 실제 영상 ID (현재: `dQw4w9WgXcQ` 더미 4개 사용 중, 라인 963/970/977/984)
- [ ] OG 이미지 `/og-image.jpg` 1200×630px 파일
- [ ] 실제 카카오 채널 ID (현재: `pf.kakao.com/_jxjxdcxj` 플레이스홀더)
- [ ] 네이버 API 키 (NAVER_CLIENT_ID, NAVER_SECRET_KEY) Vercel 환경변수

---

## CSS 커스텀 클래스 목록

```css
/* 기본 색상 변수 */
--p: #533afd      /* 보라색 메인 */
--bd: #1c1e54     /* 다크 블루 */
--ink: #0d253d    /* 메인 텍스트 */
--ink2: #4b5a70   /* 서브 텍스트 */
--soft: #f6f9fc   /* 배경 소프트 */
--border: #e3e8ee /* 보더 */

/* dc- 클래스 (상세 페이지 공통) */
.dc-hero          /* 히어로 헤더 */
.dc-kpi           /* KPI 카드 그리드 */
.dc-kpi-card      /* KPI 개별 카드 */
.dc-section       /* 콘텐츠 섹션 */
.dc-case          /* 사례 박스 */
.dc-case-label    /* 사례 레이블 */
.dc-result        /* 결과 뱃지 행 */
.dc-table         /* 테이블 */
.dc-refs          /* 레퍼런스 섹션 */
.dc-cta-box       /* CTA 박스 */
.dc-faq-item      /* FAQ 아이템 */
.dc-model-step    /* 3단계 모델 스텝 */
.dc-model-num     /* 스텝 번호 */
```

---

## 다음 세션에서 처리할 작업

### 즉시 가능 (코드만 수정)
1. **더 많은 사례 추가** — naegwa, angwa, shimui, medical_device, implant, ortho_dental 페이지에도 원장 스토리 섹션 추가
2. **SEO 더 개선** — BreadcrumbList Schema, HowTo Schema 추가
3. **블로그 포스트 추가** — dental1, dental2, skin1, ortho1 등 과목별 블로그 콘텐츠
4. **온라인마케팅 TOC** — services 페이지에 TOC 네비게이션 추가
5. **키워드 검색량 도구** — 네이버 광고 API 연동 (환경변수 설정 후)

### 사용자 입력 필요
1. **YouTube Shorts ID** — 실제 베놈 유튜브 채널 영상 ID 4개
2. **OG 이미지** — 1200×630px PNG/JPG 파일
3. **카카오 채널 ID** — 실제 채널 주소 (pf.kakao.com/_{ID})
4. **네이버 API 키** — Vercel 환경변수에 설정

---

## Git 히스토리 (최근 순)

| 커밋 | 내용 |
|---|---|
| `5e2f1e4` | feat: add online marketing sections, hospital references, doctor story cases, FAQ schemas |
| `8ace9b6` | feat: add realistic doctor-perspective cases + complete sidebar nav |
| `79220ef` | feat: add 5 conditions + realistic doctor-perspective case studies to ortho and plastic |
| `d2a3bf1` | docs: update project summary |
| `29f6ef4` | feat: add localStorage persistence for blog posts in admin page |
| `fab360a` | feat: add implant and orthodontics marketing pages |
| `bc83f23` | feat: add rich content guides, fix CTAs, add search ad details, SEO improvements |

---

## 주요 JS 함수

```javascript
sp(id)            // 최상위 페이지 전환
ld(cat)           // 진료과목 상세 로드 (pages 객체에서)
switchAI(id)      // AI 마케팅 탭 전환 (geo/aeo/seo)
switchTool(id)    // 도구 탭 전환 (geo-check/seo-check/keyword)
loadBlogPost(id)  // 블로그 포스트 로드
tocClick(el,id)   // TOC 클릭 → 해당 섹션 스크롤
```

---

## 참고 사이트 (디자인 레퍼런스)

- `https://www.venomad.com/` — 베놈 공식 사이트
- `https://www.next-t.co.kr/` — 왼쪽 카테고리 + 오른쪽 목차 구조 참고
- `https://ezloan.io/wiki/` — 우측 목록, 마우스 액션, 구조 참고
