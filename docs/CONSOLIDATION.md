# 프로젝트 결합 결정 (베놈 사이트로의 취합)

> "흩어져 있는 베놈 사이트에 들어가야 할 기능·프로젝트 결합" 판단 기록.
> 원칙: 비파괴 · claude 브랜치 · ERP 제외(별도 작업 중) · 랜딩 비주얼 디자인 파킹.

| 프로젝트/기능 | 결정 | 근거 |
|---|---|---|
| **webp** (이미지→WebP 변환) | ✅ **편입 완료** | 자립형 클라이언트 도구(서버 불필요). 사이트 `tools/webp.html`로 편입 + 베놈 톤 리브랜드. 접근: `/tools/webp.html` |
| **seo-generator** (키워드→SEO 글, OpenAI) | 🔁 **흡수(코드 이관 불필요)** | 사이트 엔진(`lib/post-generator` + `generate-post.js`: 이미지·의료광고검증·번역·GitHub저장·키워드리서치)이 **상위집합**. 사이트가 이미 더 완전 → seo-generator는 중복. 코드 가져올 것 없음. (seo-generator 레포는 사이트 엔진을 정본으로 두고 폐기/리다이렉트 권장) |
| **seo-writing-skill** | ⏸ 결합 대상 아님 | Claude Skill(작성 표준). 코드가 아니라 규격 → 사이트 `post-generator` 프롬프트가 이 표준을 채택하는 방식(별도 과제) |
| **your-supplement** | ❌ 별개 제품 | 소비자(B2C) 영양제 앱 — 병원마케팅 사이트와 무관 |
| **design-resources** | ❌ 별개 | 디자인 리소스 카탈로그 |
| **marketing-agency-erp** | ⛔ 제외 | 회원님이 별도로 작업 중(충돌 방지) — 지시 전까지 미접촉 |

## 이미 사이트 안에 있는 기능 (재확인)
검색·트렌드·AEO 실측(`insights.js`), SEO/속도/GEO(`seo-proxy.js`), 키워드리서치(`keyword-research.js`),
콘텐츠 파이프라인(`lib/venom-content`), GrowthOps(`growthops.js`), 리드 접수(`contact.js`→Airtable, P2).
## ★ 정정·추가 — 원장님_앱 발견 및 결합 (Design-resources 레포 브랜치)
앞서 "원장님 도구는 신규 빌드"라 한 것은 **오판**이었다. 실제로는 이미 완성돼 있었다 —
`Design-resources-repository`의 브랜치 `claude/hospital-marketing-analysis-3bni1v` `hospital-marketing/`
(레포 이름과 내용이 달라 초기 스윕에서 놓침).

| 항목 | 처리 |
|---|---|
| **원장님_앱**「(주)베놈 병원 검색정보 운영 진단 프로그램」 | ✅ **결합 완료** → `preview/clinic/` (99파일) |
| 구성 | 프론트(대시보드·자가진단=노출점검·입지(SGIS)·무료진단신청폼·리포트·관리자) + Python 엔진(medirank: HIRA·네이버로컬/플레이스·SGIS·점수) + Supabase Edge Functions + Postgres/PostGIS 스키마 + 법무검토 문서 |
| 동작 | 프론트 자립형(외부CDN 0) → mockup 데이터로 즉시 동작(검증됨). 실데이터는 Phase 2(Supabase 프로비저닝) |

## 전 레포·브랜치 스윕 완료 (완결성)
webp·원장님_앱 외에 사이트로 끌어올 "기능/앱"은 없음. 나머지: seo-generator(중복·흡수),
ai-marketing-6week/seminar(강의·세미나 자료), your-supplement(B2C 별개제품), seo-writing-skill(스킬),
ERP(제외). → **"모두 끌어오기"의 pull 단계 완료.**

## 후속
- **Phase 2 (Supabase 라이브 배선)**: 회원님이 Supabase 프로젝트 생성+`clinic/supabase/deploy.sh` →
  REF·ANON 주면 `set-endpoints.sh`로 프론트 배선 마무리 (`docs/…` 배포 가이드 동봉됨)
- `/clinic` 및 webp를 GNB/푸터 노출 + sitemap 등록 → **랜딩 디자인 재개 시**
