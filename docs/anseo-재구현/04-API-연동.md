# API 연결관계

두 층으로 나눠서 본다: **① 내부 API**(웹 콘솔 ↔ 백엔드) · **② 외부 제공자
연동**(백엔드 ↔ 외부 서비스 11곳).

## 1. 내부 API — 계약 구조

- **OpenAPI가 유일한 계약이다**(ADR 0005). `apps/api/openapi.json`이 소스이고,
  TypeScript 클라이언트(`packages/api-client`)는 여기서 **생성**된다
  (`pnpm --filter @veo/api-client generate`). 계약 테스트(`test_openapi_contract.py`)가
  커밋된 문서와 실제로 뜨는 앱의 스키마가 어긋나면 빌드를 실패시킨다.
- 경로 접두사: `/api` (`api_prefix` 설정). 헬스체크: `GET /api/health`.
- API 경로 수 [실측 2026-08-12, veo-platform `docs/README.md`] **104개**, 작업(job) 정의
  127개 — 재구현 시 `python3 -c "import json;print(len(json.load(open('openapi.json'))['paths']))"`
  로 다시 잴 것.
- **에러 봉투(envelope) 고정 포맷** — 모든 실패가 같은 모양:
  ```json
  { "code": "VALIDATION_FAILED", "message": "...", "field_errors": [...] }
  ```
  401은 항상 "로그인이 필요합니다" 한 문장뿐(토큰 누락/만료/변조/세션 폐기를
  구분해서 알려주지 않음 — 공격자에게 "어느 절반이 맞았는지" 힌트를 주지 않기 위해).
  다른 조직의 리소스 ID를 넣으면 403이 아니라 **404**("찾을 수 없습니다") — 존재
  여부 자체를 흘리지 않는다.
- **요청 ID 전파** — 모든 응답에 상관관계 ID 헤더가 실려서, 로그·메트릭·에러 응답이
  하나의 ID로 이어진다.
- CORS: 허용 출처는 콤마 구분 평문 목록도 받아들이도록 관대하게 파싱하지만(예:
  `https://veo.seokorea.org`), 검증은 엄격 — 빈 값은 "기본값(localhost)으로 되돌리지
  않고 거부"한다. 그래야 운영 배포에 localhost가 조용히 남는 사고를 막는다.
- 인증: JWT(access 900초 + refresh 14일). 리프레시 토큰은 1회용이며 재사용 탐지 시
  전체 토큰 계보를 폐기하되, **회전 직후 10초 유예**를 둔다 — 콘솔이 화면 전환과
  백그라운드 조회 두 자리에서 동시에 갱신을 걸어(레이스 컨디션) 이긴 쪽까지 함께
  로그아웃되던 실측 사고(5분에 8회) 이후 추가된 조치.
- 권한: 기본 거부(ADR 0007), 테넌트 격리는 구조로 강제(ADR 0008) — 조직 범위 쿼리는
  전부 `organization_id` 필터가 걸리고, 잡·리포트·서명 URL·캐시 키까지 조직 경계를
  넘지 않는다(CI가 교차 테넌트 접근 테스트로 검증).

## 2. 외부 제공자(Provider) 11곳 — "자격증명 없으면 비활성, 지어내지 않는다"

`ProviderCredentials`(`core/settings.py`)가 관리하는 상태 머신. 셋 중 하나:
`ENABLED` / `DISABLED_NO_CREDENTIAL` / `DISABLED_INVALID_CREDENTIAL`. 화면·리포트는
비활성 제공자를 "UNKNOWN + 사유"로 보여줄 뿐 **다른 값으로 대체하지 않는다**(ADR 0004).

| 제공자 | 용도 | 필요 환경변수(`VEO_` 접두사) | [실측 2026-08-12] 상태 |
|---|---|---|---|
| OpenAI | AEO 관측(gpt-5) | `OPENAI_API_KEY` | 연결됨 |
| Anthropic | AEO 관측(claude-haiku-4-5) | `ANTHROPIC_API_KEY` | 연결됨 |
| Google Gemini | AEO 관측(gemini-3.5-flash) | `GOOGLE_GEMINI_API_KEY` | 연결됨 |
| Perplexity | AEO 관측(sonar, 검색 항상 켜짐) | `PERPLEXITY_API_KEY` | 연결됨 |
| xAI (Grok) | AEO 관측(grok-4.3) | `XAI_API_KEY` | 연결됨 |
| SerpAPI | 구글 PAA 질문 추출 **+** 네이버 AI 브리핑 **+** 구글 AI Overview — **열쇠 하나를 셋이 나눠 씀** | `SERPAPI_KEY` | 연결됨 |
| Google PageSpeed | SEO 성능 검사 | `GOOGLE_PAGESPEED_API_KEY` | 연결됨 |
| 네이버 SearchAd | 키워드 광고 데이터 | `NAVER_SEARCHAD_API_KEY` / `_SECRET_KEY` / `_CUSTOMER_ID` (3개 모두 필요) | 연결됨 |
| 네이버 DataLab | 검색 트렌드 | `NAVER_DATALAB_CLIENT_ID` / `_CLIENT_SECRET` | 연결됨 |
| 공공데이터포털(data.go.kr) | 심평원(HIRA) 병원정보 — 사실 단위 채움 | `DATA_GO_KR_SERVICE_KEY` | 연결됨 |
| Google Search Console | 실측 검색 성과(클릭·노출) 연동 | `GOOGLE_SEARCH_CONSOLE_CREDENTIALS_JSON` | **미연결** — 유일한 미연결 항목 |

주의할 설계 포인트:

1. **네이버 AI 브리핑·구글 AI Overview는 네이버/구글 키가 아니라 SerpAPI 키로
   켜진다** — 두 회사가 직접 긁을 API를 안 열어서(`search.naver.com/robots.txt`가
   전면 Disallow). 세 기능(PAA 추출·네이버 브리핑·AI Overview)이 **같은 SerpAPI
   호출 한도**를 나눠 쓴다. 그 중 AI Overview는 질문 1개당 **2회** 호출한다.
2. **심평원(HIRA) 상태는 두 축이다** — API 호출 가능 여부(`data_go_kr_service_key`
   유무)와 별개로, 저장소에 미리 내려받아 둔 원본 파일 경로(`VEO_HIRA_DATASET_DIR`)가
   있으면 열쇠 없이도 파일 기반으로 사실을 채울 수 있다. 배포 이미지에는 543,220행
   짜리 정리본(9.04MB)이 `apps/api/data/hira`로 함께 들어간다.
3. **공개 도구용 키를 거래처용과 분리할 수 있다** — `PUBLIC_GOOGLE_PAGESPEED_API_KEY`
   등 `public_*` 접두사 키가 따로 있고, 비어 있으면 공용 키로 폴백. 목적은 익명
   방문자의 남용이 거래처 진단의 일일 한도를 깎아먹지 않게 하는 것.
4. **플레이스홀더 값 탐지** — `.env` 임포트 과정에서 `[SENSITIVE]`, `changeme`,
   `xxxx` 같은 스캐폴딩 문자열이 들어오면 "설정됨"이 아니라 `DISABLED_INVALID_CREDENTIAL`
   로 판정한다. `vercel env pull`이 민감 변수를 `[SENSITIVE]`로 마스킹해서 돌려주는
   실제 사고를 겪은 뒤 추가된 방어.
5. `/api/providers`가 이 표를 그대로 반환한다 — **값은 절대 안 주고 상태만**. 화면
   (`/console/credentials`)이 이걸 렌더링.

## 3. AI 답변 관측이 부르는 순서 (한 판의 실제 호출 흐름)

```
발행된 프롬프트 집합(N개 질문)
  → 5개 엔진에 각각 1회씩 병렬 호출(observation_max_concurrency=4)
  → 각 응답에서 브랜드 언급/인용 탐지 + 원문 저장(06번 문서 §4)
  → 위험 표현 탐지 → 사람 검수 대기열로
  → 결과 집계(언급률·인용률) → 다음 판(3일 뒤)까지 반복 없음
```

단가(2026-08-13 실측): 질문 1개 × 엔진 5개 × 1회 = **$0.3399 ≈ 476원**. 정기 관측
1판(질문 5개 기준) ≈ **$1.70 ≈ 2,400원**. 반사실 실험은 이 100~360배까지 뛸 수 있어
`counterfactual_monthly_budget_usd`(기본 0, 실행 자체를 막음)로 상한을 건다.

## 4. 콘솔(프론트) ↔ API 통신 방식

- 콘솔은 자체 Next.js API 라우트(`apps/web/src/app/api/*`, 약 50여 개)를 프록시로 두고
  브라우저는 이 프록시만 호출한다 — 백엔드(Railway) 주소나 서버 전용 비밀값이
  브라우저 번들에 노출되지 않는다.
- 브라우저 번들에 인라인되는 유일한 공개 값은 `NEXT_PUBLIC_VEO_API_BASE_URL`
  (Next.js 규칙상 `NEXT_PUBLIC_*`는 빌드 시점에 클라이언트 번들에 그대로 박힌다 —
  그래서 이 이름의 변수에는 비밀값을 절대 넣지 않는다, `web.Dockerfile` 주석).
- 세션은 쿠키 기반, 토큰 자동 갱신은 화면 전환 시 + 백그라운드 조회 시 두 지점에서
  각각 트리거된다(`proxy.ts`의 matcher) — 위 §1의 리프레시 유예 10초가 이 구조 때문에
  필요해졌다.

## 5. 재구현 시 체크리스트

- [ ] OpenAPI를 코드보다 먼저 두고 클라이언트를 **생성**하게 만들 것(손으로 타입
      맞추지 말 것 — drift 검사 테스트를 이식할 것).
- [ ] 제공자 상태 3단계(`ENABLED`/`DISABLED_NO_CREDENTIAL`/`DISABLED_INVALID_CREDENTIAL`)
      를 처음부터 열거형으로 설계할 것 — 나중에 추가하면 "값 없음"과 "고장"이
      뒤섞인 화면이 이미 배포돼 있다.
- [ ] SerpAPI처럼 **한 키를 여러 기능이 나눠 쓰는 경우** 한도 계산을 기능별이 아니라
      키 단위로 설계할 것.
- [ ] 에러 응답 포맷을 처음부터 통일하고 401/403/404의 정보 노출 정책(위 §1)을
      전역 예외 핸들러 한 곳에서 강제할 것 — 라우터마다 따로 처리하게 두면 반드시
      한 곳에서 새어나간다.
