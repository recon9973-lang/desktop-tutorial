# VEO

**SEO · GEO · Naver Keyword Intelligence Platform**

Developed by **VENOM**
Research & Methodology by **VEO-LAB**

---

VEO는 검색엔진 준비도(SEO), AI 답변 엔진 준비도(GEO), 실제 AI 노출 관측, 네이버 키워드
수요를 **각각 정확하게 측정하고 서로 연결해서 해석하는** 통합 진단 플랫폼입니다.

네 가지 지표를 하나의 총점으로 합치지 않습니다. 합치는 순간 어느 쪽도 실행 가능한
정보가 되지 않기 때문입니다.

## 지금 무엇이 동작하는가 (Phase 0)

Phase 0은 **공통 기준과 기반**입니다. 계약, 점수 규격, 데이터 모델, 작업 구조가
테스트를 통과한 상태이며, 실제 수집·외부 API 연동은 다음 단계입니다.

| 영역 | 상태 |
|---|---|
| 모노레포 구조 (`apps/` `packages/` `infra/` `docs/` `tests/`) | 완료 |
| SEO·GEO 점수 명세 v1.0.0 (버전·체크섬·발행 상태) | 완료 |
| 결정적 scoring evaluator + golden fixture | 완료 |
| PostgreSQL 데이터 모델 36개 테이블 + Alembic | 완료 (up/down 실제 검증) |
| FastAPI 백엔드 + OpenAPI 계약 | 완료 (health · providers · scoring) |
| TypeScript API client (생성 + drift 검사) | 완료 |
| Next.js 프론트엔드 shell + 디자인 토큰 | 완료 |
| Redis·Celery 작업 구조 (멱등성·재시도·취소·부분성공) | 완료 |
| SSRF 방어 URL guard | 완료 |
| Docker 로컬 환경 정의 | 작성 완료, **이 머신에 Docker 미설치로 빌드 미검증** |
| SEO·GEO collector 실제 수집 | **미착수 — Phase 2** |
| 네이버 SearchAd·DataLab 실제 호출 | **미착수 — Phase 2** (자격증명 필요) |
| 인증·RBAC | **미착수 — Phase 1** |
| 실제 AI 관측 실행 | **미착수 — Phase 4** (자격증명 필요) |

아직 만들지 않은 분석은 그럴듯한 결과를 반환하지 않습니다. `NotImplementedError`로
거절하거나 `UNKNOWN`을 반환하고 이유를 남깁니다.

## 설계 원칙

1. **점수 규칙은 코드가 아니라 데이터다.** 배점·심각도·상한은
   `packages/scoring-specs/`의 버전이 있는 YAML에만 존재하고, 체크섬이 붙습니다.
2. **해당 없음은 0점이 아니다.** 적용되지 않는 검사는 분모에서 빠지고 가중치가
   재분배됩니다.
3. **측정 불가는 실패가 아니다.** 감점하지 않고 coverage와 confidence를 낮춥니다.
4. **GEO 준비도와 실제 AI 가시성은 끝까지 분리한다.** 별도 엔진, 별도 점수, 별도 화면.
5. **자격증명이 없으면 없다고 말한다.** 그럴듯한 값을 만들지 않습니다.
6. **모든 숫자는 방어 가능해야 한다.** 명세 버전, 체크섬, 적용 분모, 계산 과정,
   신뢰도가 항상 함께 나갑니다.
7. **준비도 점수는 순위 예측이 아니다.** 명세 스키마가 이를 강제합니다
   (`is_rank_prediction: const false`).

자세한 내용은 [docs/scoring/methodology.md](docs/scoring/methodology.md)와
[docs/adr/](docs/adr/)를 보세요.

## 빠른 시작

필요한 것: Python 3.12+, Node 20+, pnpm, PostgreSQL 16.

```bash
# 1) Python 환경
python3 -m venv .venv
.venv/bin/pip install -e "apps/api[dev]"

# 2) 데이터베이스
createdb veo && createdb veo_test
cd apps/api && VEO_DATABASE_URL="postgresql+psycopg://localhost:5432/veo" \
  ../../.venv/bin/python -m alembic upgrade head && cd ../..

# 3) 프론트엔드·클라이언트 패키지
pnpm install

# 4) 전체 검증
make ci-local
```

API 서버:

```bash
.venv/bin/python -m uvicorn veo.api.app:app --reload --port 8000
```

문서: <http://localhost:8000/docs>

## 검증

```bash
# 백엔드 (점수·스키마·마이그레이션·계약·보안)
VEO_TEST_DATABASE_URL="postgresql+psycopg://localhost:5432/veo_test" \
  .venv/bin/python -m pytest apps/api/tests

# 프론트엔드
pnpm -r test
pnpm -r typecheck
pnpm --filter @veo/web lint && pnpm --filter @veo/web build

# 생성물 drift — API를 바꾸고 생성물을 갱신하지 않으면 실패합니다
make check-contracts
```

`make ci-local`이 백엔드 쪽 게이트 전부(lint · typecheck · 계약 drift · DB 포함 전체
테스트)를 실행합니다. `veo/`가 아직 상위 저장소의 하위 디렉터리라
`.github/workflows/ci.yml`은 동작하지 않습니다. 별도 저장소로 분리하기 전까지는
`make ci-local`과 `pnpm -r test`가 유일한 게이트입니다.

## 저장소 구조

```text
veo/
├─ apps/
│  ├─ web/        Next.js — VEO Public(비로그인 간편 진단) + VEO Console(운영 도구)
│  ├─ api/        FastAPI — 계약, 점수, 데이터 모델
│  └─ worker/     Celery — 큐, 멱등성, 재시도, 취소, 부분 성공
├─ packages/
│  ├─ scoring-specs/  VEO-LAB 점수 명세 + JSON Schema + golden fixture
│  ├─ shared-types/   Python 계약에서 생성한 TypeScript 타입
│  ├─ api-client/     OpenAPI에서 생성한 타입 + 얇은 클라이언트
│  └─ ui/             VEO 디자인 토큰과 기본 컴포넌트
├─ infra/        Docker, CI, 관측성
├─ docs/         architecture · adr · scoring · operations · api · research
└─ tests/        contract · integration · e2e · security · fixtures
```

## 병렬 작업 규칙

- 공통 계약(`apps/api/src/veo/contracts/`), 점수 명세, DB migration, OpenAPI,
  생성된 client, 의존성 잠금 파일은 **통합 담당자만** 수정합니다.
- 각 작업자는 배정된 폴더만 수정하고, 계약 변경이 필요하면 `INTEGRATION_REQUEST.md`로
  제안합니다.
- 작업자 보고를 그대로 신뢰하지 않고 통합 담당자가 diff와 테스트를 다시 검증합니다.

## 사용하지 않는 표현

근거가 없으므로 제품 어디에도 쓰지 않습니다.

- "검색 1위 보장", "ChatGPT 1위"
- "스키마를 넣으면 인용 보장"
- "한 번의 질문 결과가 시장 점유율"
- 합법적 출처 없는 "실시간 인기검색어"
- 측정 엔진·모델·날짜·지역·표본을 숨긴 단일 점수

## 참고

VEO는 NXT를 비교 대상으로만 참고했습니다. NXT의 소스, 문구, 디자인, 자산은
복제하지 않았으며 독립적으로 설계·구현했습니다.
