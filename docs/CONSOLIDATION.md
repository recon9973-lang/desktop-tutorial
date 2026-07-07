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
→ 외부에서 "새로 들여올" 실코드는 사실상 **webp가 유일**. 나머지는 이미 사이트가 보유하거나 성격상 결합 대상이 아님.

## 후속 (신규 빌드 — "결합"이 아니라 신규 개발이라 별도 승인 대상)
- 원장님 도구: NAVER 노출점검·입지분석(네이버 검색 API — 사이트가 이미 자격증명 보유, 신규 엔드포인트 필요)
- webp 도구를 GNB/푸터에 노출 + sitemap 등록 → **랜딩 디자인 재개 시**
