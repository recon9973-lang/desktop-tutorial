# venom-content — L0 콘텐츠 파이프라인

사이트 `lib/*`의 콘텐츠 생성 모듈을 **7스테이지 파이프라인 한 표면**으로 재노출한다.
모든 화면(사이트 자동발행·ERP 원고스튜디오·seo-writing 스킬·seo-generator)이 이 한 곳을 import해
**같은 엔진·같은 의료광고법 게이트**를 쓴다. (설계: `docs/L0-content-pipeline.md`)

## 사용

```js
const pipeline = require('./lib/venom-content'); // 또는 상대경로

pipeline.status(); // 스테이지 로드 상태 진단 { research:'ok', ... }
```

## 스테이지 API (실제 함수)

| 스테이지 | 접근 | 주요 함수 |
|---------|------|----------|
| **research** | `pipeline.research` | `researchKeywords(...)` · `buildResearchPrompt(...)` · `looksLikeQuestion(...)` |
| **generate** | `pipeline.generate` | `generatePost(...)` · `buildFaqSchema(...)` · `CAT_LABEL` |
| ↳ openai | `pipeline.openai` | `chatComplete(...)` |
| **image** | `pipeline.image` | `generateAndSaveImage(...)` |
| **translate** | `pipeline.translate` | `translatePostToEnglish(...)` |
| **validate** ⛔ | `pipeline.validate.medicalAd` | `validateMedicalAd(...)` · `autoFix(...)` · `FORBIDDEN` · `RISKY` |
| | `pipeline.validate.content` | `cleanContent(...)` · `detectContentErrors(...)` · `reviewContent(...)` |
| **design** | `pipeline.design` | `designPost(...)` |
| **structure** | `pipeline.structure.sitemap` | `updateSitemap(...)` · `buildXml(...)` |
| **publish** | `pipeline.publish.github` | GitHub 저장/커밋 함수 |

## 표준 흐름 (권장 조립)

```
research → generate → image → [validate ⛔ 필수] → design → structure → publish
```

**의료광고법 게이트는 어느 경로든 발행 전 필수 통과:**

```js
// 1) 생성
const draft = await pipeline.generate.generatePost({ keyword, region, ... });

// 2) ⛔ 검증 게이트 — 통과 못 하면 발행 금지
const check = pipeline.validate.medicalAd.validateMedicalAd(draft.body);
const safe  = check.ok ? draft.body : pipeline.validate.medicalAd.autoFix(draft.body);

// 3) 디자인 → 발행
const html = pipeline.design.designPost({ ...draft, body: safe });
await pipeline.publish.github.savePost(html); // 저장소별 어댑터
```

## 화면별 조립 (스테이지 선택)

| 화면 | 쓰는 스테이지 |
|------|--------------|
| 사이트 자동발행(봇) | 1~7 전체 자동 |
| ERP 원고 스튜디오 | 1~6 (사람이 검토, validate 필수) |
| seo-writing 스킬 | generate·structure 규격 |
| seo-generator(흡수 예정) | research·generate |

## 원칙
- **validate는 공통 필수 게이트** — 사내·봇·스킬 어느 경로든 통과해야 발행.
- **스테이지는 조립 가능** — 화면마다 필요한 스테이지만 선택.
- **비파괴** — 이 배럴은 기존 모듈을 재노출만. 사이트 동작 무영향.

## 이관 로드맵
- ✅ P1 배럴 + API 문서(현재)
- P2 ERP 원고스튜디오 → `validate`·`generate` 호출로 중복 제거
- P3 seo-writing 스킬을 generate/structure 표준으로 연결
- P4 seo-generator를 L0 얇은 프론트로 재정의/흡수
- P5 각 화면 중복 로직 제거
