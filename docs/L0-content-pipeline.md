# L0 콘텐츠 파이프라인 — 추출 설계 (v1)

> 목적: 4곳에 흩어진 콘텐츠 생성 로직을 **하나의 공유 파이프라인(L0)**으로 추출.
> 모든 화면(surface)이 같은 엔진을 호출 → 품질·의료광고법 준수·유지보수 일원화.

## 1. 현재 (분산된 4곳)

| # | 위치 | 하는 일 | 문제 |
|---|------|--------|------|
| A | `seo-generator` (별도 웹앱) | 키워드→SEO 글 생성(OpenAI web_search) | 독립 중복 |
| B | 베놈사이트 `lib/*` 자동발행 | GPT생성·이미지·번역·의료광고검증·검수·디자인·키워드·사이트맵 (**가장 완전**) | 사이트에 갇힘 |
| C | ERP `public/studio.html` 원고 스튜디오 | 기획→집필→검수→발행 (사내 수동) | 자체 구현 |
| D | `seo-writing-skill` (Claude Skill) | GEO/AEO 글 표준·JSON-LD | 규격만, 엔진 없음 |

→ 같은 로직(GPT 생성·의료광고 검증·SEO 구조)이 4벌. 출력 품질이 화면마다 다르고 수정이 4배.

## 2. 목표 구조 — L0 파이프라인 1벌 + 얇은 화면들

```
        ┌──────────── 화면(surface) ────────────┐
        │  ERP 원고스튜디오   사이트 자동발행(봇)  │
        │  seo-writing 스킬   (seo-generator 흡수) │
        └───────────────┬────────────────────────┘
                        │ 같은 API/모듈 호출
        ┌───────────────▼──── L0 콘텐츠 파이프라인 ────┐
        │  1) research   키워드·주제 리서치            │
        │  2) generate   GPT 본문·메타 (skill 규격 적용)│
        │  3) image      DALL-E·webp·Higgsfield/Canva  │
        │  4) validate   의료광고법 + 콘텐츠 검수 ⛔게이트│
        │  5) design     베놈 브랜드 스타일 적용        │
        │  6) structure  JSON-LD·메타·sitemap          │
        │  7) publish    GitHub·WordPress·Vercel 어댑터 │
        └──────────────────────────────────────────────┘
```

## 3. 표준 계약 (이미 존재함)

surface들이 주고받는 표준 타입 = **`ContentDraft`**
`{ 제목후보[5], 추천제목, 메타디스크립션, 목차, 본문섹션[], FAQ[], 해시태그[5], JSON-LD, 이미지[] }`

→ 이 규격은 **seo-generator와 seo-writing-skill이 이미 동일하게 쓰고 있음.** 계약이 이미 서 있으니 추출 난이도가 낮다.

## 4. 각 스테이지 = 독립 모듈 (재사용원)

| 스테이지 | 추출 원본 | 비고 |
|---------|----------|------|
| research | `lib/keyword-research.js` | Naver 검색광고·데이터랩·자동완성 |
| generate | `lib/post-generator.js` + `seo-writing-skill` 규격 | 스킬이 프롬프트/구조 표준 제공 |
| image | `lib/image-generator.js`(DALL-E) + `webp`(변환) + Higgsfield/Canva | 이미지 스튜디오와 공유 |
| validate | `lib/medical-ad-validator.js` + `lib/content-validator.js` | **모든 surface 공통 필수 게이트** |
| design | `lib/post-designer.js` | 브랜드 인라인 스타일 |
| structure | seo-writing skill(JSON-LD) + `lib/sitemap-builder.js` | GEO/AEO 구조 |
| publish | `lib/github-store.js` + WordPress MCP + Vercel | 발행처별 어댑터 |

## 5. 핵심 원칙

- **의료광고법 검증(validate)은 항상 마지막 게이트** — 사내·봇·스킬 어느 경로든 통과해야 발행. (지금은 사이트 봇만 통과, 원고스튜디오는 별도)
- **스테이지는 조립 가능(composable)** — 원고스튜디오는 1~6 수동 검토, 봇은 1~7 자동, 스킬은 1~2+6만.
- **파이프라인은 라이브러리(공유 패키지) + 얇은 API.** 각 스테이지 독립 테스트.

## 6. 이관 순서 (expand → migrate → contract, 무중단)

1. **P1** 사이트 `lib/*`를 **공유 패키지 `venom-content`로 승격**(코드 이동 없이 export 정리). 사이트는 그대로 동작.
2. **P2** ERP 원고스튜디오가 `venom-content`의 validate/generate를 호출 → 자체 중복 제거.
3. **P3** `seo-writing-skill`을 generate/structure의 프롬프트 표준으로 연결.
4. **P4** `seo-generator`를 L0의 **얇은 웹 프론트**로 재정의(엔진은 L0 사용) 또는 흡수.
5. **P5** 각 화면 중복 로직 제거(contract).

## 7. 기대 효과
- 출력 품질·톤·의료광고 준수가 **모든 화면에서 동일**.
- 새 발행처(원장님 앱 등) 추가 시 파이프라인 재사용 → 즉시 콘텐츠 생성 가능.
- 수정 1곳 → 전 화면 반영.

---
*L0 콘텐츠 파이프라인 v1 · 2026-07-05 · 계약(ContentDraft)이 이미 서 있어 추출 난이도 낮음 · 아키텍처 L0의 콘텐츠 축 구현*
