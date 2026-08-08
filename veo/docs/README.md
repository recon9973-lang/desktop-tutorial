# VEO — 프로젝트 전체 설명서

**이 문서는 지도다.** 무엇을 만들고 있고, 어떻게 생겼고, **57개 문서 중 무엇을 언제
읽는지**를 적는다. 개별 주제의 기준 문서는 각자 따로 있고, 이 문서는 그것들을 대신하지
않는다 — 여기서 자세히 적으면 두 벌이 되고 언젠가 한쪽만 고쳐진다(지침서 0-D).

**모든 숫자는 2026-08-08 에 명령을 실행해 얻었다.**

---

# 1. 무엇을 만드는가

병원마케팅 대행사 **베놈애드**가 거래처(주로 병·의원)의 검색·AI 노출을 진단하는 도구.
사장님이 정한 범위는 셋이다 — **SEO · GEO · AI 답변.** 콘텐츠 제작은 ERP 로 넘긴다.

```
① SEO 진단        검색엔진이 사이트를 발견·크롤링·해석할 수 있는가     ✅ 운영 중
② GEO 준비도      AI 답변 엔진이 접근·추출·검증할 수 있는 구조인가     ✅ 운영 중
③ AI 답변 관측    AI 가 실제로 우리를 말하는가 (외부 관측)             ← 만드는 중
④ 네이버 키워드   어떤 검색어로 들어오는가                             열쇠는 있음, 데이터 0
⑤ 리포트·전달     거래처에 내보내는 것                                 배선만 있음
```

**②와 ③을 절대 합치지 않는다.** ②는 우리 사이트를 뜯어보는 것(점수), ③은 AI 에게 직접
묻는 것(관측 기록). 대상도 방법도 다르다 — `docs/adr/0003`.

```
[실측] 운영 데이터 2026-08-08
   거래처 8곳 · SEO/GEO 채점 45건 · 판정 2,207행 · 이슈 165건 · 근거 3,820행
   AI 관측 0건 · 질문 집합 0 · 브랜드 신원 4
```

---

# 2. 어떻게 생겼는가

## 2-A. 저장소

```
veo/
├── apps/
│   ├── api/       FastAPI · Python  파이썬 309파일 79,380줄 · 시험 231파일
│   ├── web/       Next.js · TS      183파일 27,892줄
│   └── worker/    Celery            11파일
├── packages/
│   ├── scoring-specs/   채점 명세 YAML — **코드가 아니라 데이터**
│   ├── model-prices/    날짜가 붙은 모델 가격표
│   ├── api-client/      OpenAPI 에서 생성한 타입
│   ├── shared-types/
│   └── ui/
└── docs/          57개 (이 문서 포함)
```

## 2-B. 배포

```
웹      Vercel        veo.seokorea.org
API     Railway       veo-platform-production.up.railway.app  (Southeast Asia)
워커    Railway       veo-worker  (동시 4)
큐      Railway       Redis
DB      Neon          PostgreSQL · 테이블 47개 (ap-southeast-1)
```

**배포는 `make deploy` 하나뿐이다.** subtree 로 떼어내 `deploy-candidate` 로 밀고, CI 가
초록일 때만 `main` 으로 간다. 이 관문을 우회한 적이 없다 — GitHub 장애로 두 번 막혔을
때도. 자세히: `docs/operations/release-checklist.md`

## 2-C. API 와 화면

```
[실측] API 경로 93개
   observations 12 · lab 9 · seo 8 · keywords 7 · reports 7 · issues 6 · auth 5 · geo 4

[실측] 콘솔 화면 15개
   대시보드 · 업체관리 · 진단 · AI가시성 · AI답변검수 · 키워드 · 브랜드식별
   이슈 · 리포트 · 원고검수 · 사용량비용 · 팀 · 계정 · 채점명세 · 변경이력
```

---

# 3. 이 제품이 지키는 것 — 읽는 순서대로

## 3-A. 개발 원칙 `0-A ~ 0-J`

> `docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md`

**손대기 전에 이것부터.** 각 항목이 **실제로 난 사고**에서 나왔다.

| | 무엇 | 왜 생겼나 |
|---|---|---|
| 0-A | 재지 않은 것을 잰 것처럼 말하지 않는다 | |
| 0-D | **있는 것을 다시 만들지 않는다** | 세 번 틀림. 중복은 낭비로 끝나지 않고 **나중 것이 원본의 제약을 모른 채 관대해진다** |
| 0-E | **부를 수 없는 기능은 없는 기능이다** | 2026-08-08 한 세션에 3건 발견 |
| 0-F | 시험이 초록인 것과 운영에서 도는 것은 다르다 | |
| 0-H | 규칙에는 관문이 필요하다 | |
| 0-I | 결함을 지켜주던 시험이 있다 | |

## 3-B. 채점 규칙 — ADR 16개

> `docs/adr/`

명세를 바꾸는 판단은 전부 여기 있다. **숫자를 고치려면 먼저 ADR 을 고쳐야 한다**
(`tests/test_thresholds_cite_a_decision.py` 가 강제).

| ADR | 무엇 |
|---|---|
| 0001 | 채점 명세는 **데이터**다 — 코드에 숫자를 박지 않는다 |
| 0002 | 해당없음(N/A) 과 측정불가(UNKNOWN) 는 다르다 |
| **0003** | **GEO 준비도는 AI 노출이 아니다** |
| 0010 | 비교는 같은 조건에서만 |
| 0012 | 발행된 방법론은 불변 — 과거 점수는 그때 규칙으로 설명된다 |
| 0013 | 비율은 맨숫자로 내지 않는다 |
| **0015** | **프롬프트 집합은 감사 대상 산출물이다** — 질문만 골라도 조작이 된다 |
| 0016 | 절대 평가 — 못 잰 것은 분모에 남는다 |

## 3-C. 보안·운영 제약

- **비밀값을 대화창에 출력하지 않는다.** `veo/.env` 는 0600 · gitignore
- 자격증명이 없으면 **그럴듯한 값을 지어내지 않는다** → "공급자 비활성"(ADR 0004)
- 테넌트 격리는 구조로(ADR 0008) · 권한은 기본 거부(ADR 0007)

---

# 4. 채점이 어떻게 되는가

```
[실측] veo.seo.readiness 1.9.0   영역 9 · 검사 59 · 총점 상한 5 · 발행본 10판
[실측] veo.geo.readiness 1.3.0   영역 7 · 검사 37 · 총점 상한 0 · 발행본 4판
```

산식은 한 곳(`scoring/evaluator.py`)에만 있고 모든 화면이 그것을 쓴다.

```
coverage    결함이 퍼진 범위
breadth     coverage ** 0.7   — 템플릿 하나의 문제를 40%가 아니라 53%로 센다
penalty     배점 × 상태 × breadth × 확신도
reach       관문 영역의 곱  — 색인이 막히면 뒤가 통째로 무의미
overall     reach × Σ(영역점수×가중치) / Σ(채점된 영역 가중치)
caps        그 위에 상한. 상한은 점수를 올리지 않는다
```

**분모는 100.0 고정이다.** 연동(서치콘솔 등) 3영역은 `contributes_to_score: false` 로
점수 밖이라, **연결하든 안 하든 100점의 뜻이 같다.**

자세히: `docs/scoring/methodology.md`(SEO) · `docs/scoring/geo-methodology.md`(GEO) ·
`docs/research/SEO_SCORING_ALGORITHM_V2.md`
③ AI 답변 관측은 채점이 아니라 관측이다 — `docs/observation-engine.md`

## 4-A. 세 영역의 기준 문서 (2026-08-08 확인)

| 영역 | 기준 문서 | 상태 |
|---|---|---|
| ① SEO | `scoring/methodology.md` | ✅ 본문 **1.9.0** 기준 (운영과 같음). 2026-08-08 갱신 |
| ② GEO 준비도 | `scoring/geo-methodology.md` | ✅ 본문 **1.3.0** 기준. 2026-08-08 신규 |
| ③ AI 답변 관측 | `observation-engine.md` | ✅ 2026-08-08 신규 |

`research/GEO_RECOMMENDED_SCORING_MODEL.md` 와 `research/SEO_*` 는 **처음 권장안**이지
발행본 설명이 아니다. 운영이 무엇을 쓰는지는 위 두 문서를 본다.

**표의 숫자는 손으로 옮겨 적은 것이다.** 명세와 어긋났는지 의심되면 세어 본다:

```bash
python3 scripts/spec_weights.py                # SEO 발행본
python3 scripts/spec_weights.py --domain geo   # GEO 발행본
```

---

# 5. 문서 지도 — 무엇을 언제 읽나

## 처음 오는 사람

```
1  이 문서
2  docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md  §0-A~0-J     원칙
3  docs/architecture/requirements-traceability.md                      요구↔실물
4  docs/HANDOFF.md                                                     직전 맥락
5  docs/SESSION-2026-08-08.md                                          최근 작업
```

## 목적별

| 하려는 일 | 읽을 것 |
|---|---|
| 채점 규칙을 바꾼다 | `adr/` 해당 항목 → `scoring/methodology.md` → `research/SEO_SCORING_ALGORITHM_V2.md` |
| 화면을 만든다 | `architecture/screen-plan.md` → `research/VEO_IMPLEMENTATION_PLAN.md` |
| 권한을 만진다 | `architecture/authorization.md` (ADR 0007·0008) |
| 배포한다 | `operations/release-checklist.md` · `operations/runbook-rollback.md` |
| 자격증명을 다룬다 | `operations/runbook-provider-credentials.md` · `runbook-credential-rotation.md` |
| 워커를 만진다 | `operations/worker-deployment.md` |
| 사고가 났다 | `operations/runbook-incident-response.md` · `runbook-backup-restore.md` |
| 봇 정책 | `operations/bot-identification.md` |
| **AI 답변 관측(③)을 만진다** | **`observation-engine.md`** ← 기준 문서. 그다음 `adr/0014·0015` |
| 인용 지원 모델을 넓힌다 | `operations/verifying-citation-support.md` |
| 콘텐츠 프로그램을 만든다 | `research/CONTENT-PROGRAM-NOTES.md` |
| 용어가 헷갈린다 | `architecture/glossary.md` |
| 무엇이 틀렸었나 | **`CORRECTIONS.md`** |

## 참고만 하는 것 (지난 판단의 기록)

```
audit/2026-08-04-AUDIT-LEDGER.md      감사 원장
design/2026-08-07-score-split.md      **취소된 계획.** 이미 되어 있던 것을 다시 지으려 함
design/2026-08-07-per-site-applicability.md   미착수
architecture/session-log-2026-07.md   지난 세션 기록
PLAN-2026-08-total-review.md          전수조사 기획서
```

---

# 6. 지금 상태와 남은 것

## 도는 것

```
✅ SEO·GEO 진단 — 한 번 측정, 두 눈금. 거래처 8곳에 45건 채점
✅ 이슈·작업 큐 · 재진단으로 닫힘(ADR 0011)
✅ 워커 · 큐 · 정기 재진단 스케줄러
✅ 의료광고법 원고 검수기
✅ 자격증명 볼트 · 감사 로그 · 테넌트 격리
```

## 만드는 중 — ③ AI 답변 관측

```
✅ 서버 (라우트 12 · 제공자 4 · 탐지 · 위험 · 검수)
✅ 가격표 · 검색 요금 계산
✅ 브랜드 식별 화면 (공유 도메인 차단 포함)
✅ 질문 집합 만들기 · 지식iN 실수집
⬜ 검색 켬/끔 2모드 · 수동 측정 · 첫 실행 · 인포그래픽
```

## 열쇠 상태

```
[실측] 연결됨   OpenAI · Google PageSpeed · 네이버 DataLab · 네이버 SearchAd
[실측] 미연결   Anthropic · Gemini · Perplexity · Google Search Console · SerpAPI
```

## 알려진 결함 (과제 번호)

```
#59  우리가 읽는 토큰이 실제 청구의 64% — 검색 호출은 모델을 두 번 부른다
#58  관측 인포그래픽 — 그릴 데이터가 없음
#33  flow.seokorea.org 가 싱가포르에서 돌고 있다
#36  journeymap 이 한 디스크에만 존재 — 백업 없음
```

---

# 7. 이 프로젝트가 특별히 조심하는 것

세 가지가 반복해서 사고를 냈고, 그래서 관문이 있다.

## 7-A. 0 과 "모른다" 를 섞지 않는다

못 잰 것을 0으로 적으면 **없는 결함을 지어내거나 없는 성과를 만든다.** 가격표가 비면
"0원" 이 아니라 "가격 미설정" 이고, 인용을 못 돌려주는 모델은 "인용 0건" 이 아니라
"측정 불가" 다.

## 7-B. 유리한 방향의 거짓은 아무도 잡아주지 않는다

ADR 0015 의 문장이 이 제품 전체를 설명한다:

> 경쟁 비교를 조작하는 데 숫자를 위조할 필요가 없다. **질문만 고르면 된다.**
> 이후 모든 계산은 산술적으로 완벽하고 결론은 거짓이다. 그리고 이 실패는 데이터에
> 아무 흔적을 남기지 않는다.

## 7-C. 지어낸 값이 제품에 들어간다

2026-08-08 실측 — "복사해서 붙여넣으세요" 코드 안에 지어낸 진료비·통계·의학 서술이
들어가 운영까지 나갔다. 그 뒤로 시험이 막는다(금액·기간·통계·주소가 `[대괄호]` 밖에
있으면 실패).

**전체 기록: `CORRECTIONS.md` — 13건, 그중 5건은 사장님이 잡았다.**
