# 관측(observability) 모듈 → 통합 담당자 요청

`veo/observability/**` 담당자가 다른 소유 영역에 요청하는 사항입니다. 이 패키지는 요청한
파일을 **직접 고치지 않았습니다**. `veo/api/app.py`, `veo/auth/**`, `veo/credentials/**`,
워커, `pyproject.toml`은 모두 이 패키지의 소유 밖입니다.

새 의존성은 추가하지 않았습니다. `structlog`만 사용하며 `prometheus_client`,
`opentelemetry-*`는 사용하지 않았습니다.

---

## 1. `veo.auth.hashing`를 단독으로 import 할 수 없습니다 (버그 · 우선순위 높음)

```
$ python -c "import veo.auth.hashing"
ImportError: cannot import name 'router' from partially initialized module
'veo.auth.router' (most likely due to a circular import)
```

경로: `veo/auth/__init__.py` → `veo.auth.router` → `veo.api.deps` → `veo.api.__init__`
→ `veo.api.app` → `veo.auth.router`(초기화 중).

**영향.** `veo.observability.logging.hash_identifier`는 감사 로그와 조인 가능한 다이제스트를
만들어야 하므로 `veo.auth.hashing.identifier_hash`와 같은 정규화·같은 SHA-256을 써야 합니다.
그런데 위 오류 때문에 import 할 수 없어, 세 줄짜리 정규화+해시를 **복제**했습니다. 로그 한 줄을
해시하려고 FastAPI 앱 전체를 import 하는 워커는 있을 수 없기 때문입니다.

**요청.** 다음 중 하나로 고쳐 주십시오.

- `veo/auth/__init__.py`에서 `router` 재노출을 제거하거나 지연 import 로 바꾸기, 또는
- 순수 함수인 `hashing.py`를 import 부작용이 없는 위치(`veo/common/` 등)로 옮기기.

고쳐지면 `logging.py`의 복제본을 삭제하고 정식 함수를 import 하겠습니다. 그때까지 드리프트는
`tests/observability/test_logging.py::test_the_log_digest_is_a_prefix_of_the_audit_digest`
가 잡습니다. 이 테스트는 `veo/auth/hashing.py`를 `importlib`로 **파일에서 직접** 로드합니다
(해당 파일은 `hashlib` 외에 아무것도 import 하지 않으므로 단독 로드가 정확합니다).

**부수 발견 — import 순서 결합.** 처음에는 이 테스트에서 `import veo.api`로 순환을
우회했는데, 그렇게 하면 전체 스위트 실행 시
`tests/public/test_service.py::test_a_site_that_refuses_the_connection_is_answered_not_raised`
가 실패했습니다(`httpx.ConnectError`가 `PublicRefusal`로 변환되지 않고 그대로 전파). 두 테스트를
따로 돌리면 모두 통과하므로, 애플리케이션을 이른 시점에 import 하면 어딘가의 전역/캐시 상태가
달라진다는 뜻입니다. 저희 쪽은 `veo.api` import를 제거해 회피했고 전체 스위트는 초록입니다.
다만 원인 자체(테스트 순서에 의존하는 전역 상태)는 `veo/api` 또는 `veo/public` 소유자가
확인해 주시는 편이 좋겠습니다 — 저희 소유 영역이 아니라 손대지 않았습니다.

---

## 2. ~~`veo/credentials/redaction.py`가 **작은따옴표** 안의 비밀값을 놓칩니다~~ — **해결됨 (CLOSED)**

통합 담당자가 `veo/credentials/redaction.py`를 수정했습니다. 값 패턴이 라벨 쪽과 값 쪽 양쪽에서
`['\"]?`를 받아들이도록 바뀌었고, 회귀 테스트 6건이 `tests/credentials/test_redaction.py`에
추가되었습니다. 이 패키지의 임시 조치(`logging.py`의 `_QUOTED_SECRET`, 그리고
`redaction._SENSITIVE_LABEL` 비공개 심볼 import)는 **삭제했습니다.** 지금 로그 경로의 스크러빙은
전적으로 `redaction.redact`가 수행합니다.

수정 후 확인:

```python
>>> from veo.credentials.redaction import redact
>>> redact("password='hunter2xyz'")
"password='[REDACTED]'"
>>> redact("{'api_key': 'naver-customer-1234567'}")
"{'api_key': '[REDACTED]'}"
>>> redact("Settings(token='nv-abc1234567', provider='NAVER')")
"Settings(token='[REDACTED]', provider='NAVER')"
>>> redact("clinic_name='서울온담의원'")     # 비밀이 아닌 값은 그대로
"clinic_name='서울온담의원'"
```

### 최초 보고의 정정 — 피해 범위를 과장했습니다

처음 보고서에는 아래 예시가 **유출 사례로** 적혀 있었습니다.

```python
>>> redact('{"api_key": "naver-customer-1234567"}')
'{"api_key": "naver-customer-1234567"}'   # ← 틀렸습니다
```

**사실이 아닙니다.** 수정 전 패턴에도 값 앞의 큰따옴표(`\"?`)는 이미 들어 있었으므로
큰따옴표 JSON 페이로드는 **처음부터 지워지고 있었습니다.** 실제 결함은 그보다 좁았습니다 —
값이 **작은따옴표**로 시작할 때만 매칭이 시작되지 못했습니다. 저는 작은따옴표·따옴표 없는
형태만 실제로 실행해 보고 큰따옴표 형태는 확인 없이 단언했습니다. 보안 결함의 범위를 부풀리는
것은 축소하는 것과 마찬가지로 다음 사람에게 비용을 남기므로, 기록으로 남깁니다.

**여전히 유효한 부분**은 작은따옴표 형태가 중요했던 이유입니다. 파이썬 `repr()`은 문자열을
작은따옴표로 씁니다. 트레이스백의 프레임 라인, f-string의 `!r`, dump 된 설정 dict가 전부
`password='...'` 형태이고, 트레이스백은 자격증명이 로그를 만나는 가장 흔한 지점입니다.

로그 경계에서의 단언은 그대로 유지했습니다
(`tests/observability/test_logging.py::test_a_quoted_credential_is_scrubbed`). 스크러빙 자체는
이제 상류가 하지만, 프로세서 체인이 어떤 필드에 `redact`를 적용하지 않게 바뀌면 그 회귀는
운영이 아니라 이 테스트에서 드러나야 합니다.

---

## 2-1. `veo.credentials.redaction` import 가 FastAPI·SQLAlchemy를 끌고 옵니다 (경량화 요청)

```
$ python -c "import sys, veo.observability.logging; print('fastapi' in sys.modules)"
True
```

`veo/credentials/__init__.py`가 라우터까지 재노출하기 때문에, 순수 정규식 모듈인
`redaction.py` 하나를 쓰려 해도 HTTP 계층 전체가 로드됩니다(동작에는 문제 없고 순환도
없습니다 — 무게만 문제입니다). 로그 한 줄을 지우려고 FastAPI를 import 하는 워커는 바람직하지
않으므로, 1번과 같은 방향(패키지 `__init__`의 라우터 재노출 제거 또는 지연 import)을 함께
검토해 주시면 좋겠습니다.

---

## 3. 개인정보 형태 판별기가 두 곳에 있습니다

`veo/auth/audit.py`의 `_looks_sensitive`는 이메일·IPv4·IPv6를 알지만 비공개이고, 값 길이
64자 초과를 전부 민감으로 보기 때문에 로그(경로 템플릿, 트레이스백)에는 그대로 쓸 수 없습니다.
그래서 `logging.py`에 `_PERSONAL_DATA`로 이메일·IPv4·IPv6·한국 전화번호 패턴을 별도로 두었고,
IPv6 패턴은 ISO 타임스탬프의 `12:00:00`을 주소로 오인하지 않도록 콜론 그룹 3개 이상을
요구하도록 좁혔습니다.

**요청.** 개인정보 **형태** 판별을 공개 헬퍼로 한 곳에 모아 주시면(예:
`veo/common/pii.py::looks_like_personal_data`) 감사 로그와 애플리케이션 로그가 같은 정의를
쓰게 됩니다. 지금은 감사 로그가 잡는 것을 애플리케이션 로그가 놓칠 여지가 구조적으로 있습니다.

---

## 4. `veo/api/app.py` 배선 (필수 · 이 패키지는 이 파일을 수정하지 않았습니다)

### 4-1. 시작 시 로깅 구성

```python
from veo.observability import configure_logging

def create_app() -> FastAPI:
    configure_logging(level=settings.log_level)   # json_output 은 VEO_LOG_FORMAT 또는 TTY 판정
    ...
```

`VEO_LOG_FORMAT=json|console`로 렌더러를 강제할 수 있습니다. 지정이 없으면 스트림이 TTY가
아닐 때 JSON입니다.

### 4-2. 요청 종료 로그 한 줄

기존 `attach_request_id` 미들웨어 안에서:

```python
from veo.observability import get_logger, log_request_completed, record_http_request
from veo.observability import get_metric_sink

_log = get_logger("veo.api")

@app.middleware("http")
async def attach_request_id(request: Request, call_next: Any) -> Any:
    request_id = get_request_id(request)
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    route = getattr(request.scope.get("route"), "path", None) or "unmatched"

    log_request_completed(
        _log,
        correlation_id=request_id,
        route=route,                      # 경로 "템플릿"이어야 합니다 (아래 주의)
        method=request.method,
        status_code=response.status_code,
        latency_ms=int(elapsed_ms),
        outcome="OK" if response.status_code < 400 else "ERROR",
    )
    record_http_request(
        get_metric_sink(),
        route=route,
        method=request.method,
        status_code=response.status_code,
        duration_ms=elapsed_ms,
    )
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
```

**주의 — `route`는 반드시 템플릿이어야 합니다.** `/api/v1/sites/{site_id}`이지
`/api/v1/sites/9f3a…`가 아닙니다. 해석된 경로를 넣으면 (a) 메트릭 카디널리티가 고객 수만큼
늘어나고 (b) 고객 식별자가 DB의 접근통제가 전혀 없는 메트릭 저장소로 흘러갑니다.
`request.scope["route"]`는 라우팅 이후에 채워지므로 위처럼 `call_next` **뒤**에 읽어야 합니다.

### 4-3. 조직 식별자를 로그에 넣는 경우

`organization_id`는 **UUID만** 통과합니다. 이름을 넣으면 `[REDACTED]`가 됩니다(의도된 동작).
테넌트별 요청량이 필요하면 `record_http_request(..., organization_hash=hash_identifier(str(org_id)))`
를 쓰십시오 — 메트릭 저장소가 고객 목록을 학습하지 않습니다.

---

## 5. `/readyz` 라우트 (이 패키지는 라우터를 소유하지 않습니다)

`ReadinessProbe`는 준비되어 있으나 마운트되어 있지 않습니다. DB 세션과 큐 연결의 소유자가
점검 함수를 제공해 주셔야 합니다.

```python
from veo.observability import ReadinessProbe

probe = ReadinessProbe(
    checks={"database": check_database, "queue": check_queue},   # 정상이면 None, 저하면 한국어 문장, 장애면 raise
    provider_states=lambda: {...},        # {"NAVER": ProviderState.ENABLED, ...}
    price_table=load_price_table_or_none,
)

@router.get("/readyz")
def readyz() -> dict:
    report = probe.run()
    return report.to_dict()          # ready 가 False 면 503 으로 내려 주십시오
```

규칙:

- `checks`에 준 것만 **필수**입니다. DOWN 이면 `ready=False`.
- 프로바이더 상태와 가격표는 **참고용**입니다. 자격증명이 없는 프로바이더는 DEGRADED이지만
  준비 상태를 막지 않습니다 — VEO는 그 항목을 '측정 불가'로 보고하며, 그것은 제품 상태이지
  인스턴스를 로드밸런서에서 빼야 할 이유가 아닙니다.
- 출력에는 비밀도 접속 문자열도 들어가지 않습니다(`scheme://…` 전체가 제거됩니다).
  `tests/observability/test_health.py`가 직렬화 결과를 실제 비밀 문자열로 검색해 확인합니다.

---

## 6. 워커 쪽 (`apps/worker`)

1. 큐 메시지에 `correlation_id`를 실어 주십시오. 워커에서
   `tracer.start_span("worker.scan.run", correlation_id=message.correlation_id)`로
   열면 그 아래 모든 스팬·로그가 같은 상관 ID를 갖습니다.
2. 큐 상태를 주기적으로 보고해 주십시오:
   `record_queue_state(sink, queue=..., depth=..., wait_ms=..., retries=..., dead_lettered=...)`.
   depth·wait·retry·dead-letter 네 가지가 "큐가 빠지고 있는가"에 답합니다.
3. 태스크 시작 시 `bind_log_context(correlation_id=..., job_id=...)`, 종료 시
   `clear_log_context()`.

---

## 7. 프로바이더 어댑터 · `veo/observations` 쪽

기록 함수는 준비되어 있고, 호출은 해당 패키지 소유자가 넣어 주셔야 합니다.

| 지점 | 호출 |
| --- | --- |
| 프로바이더 호출 종료 | `record_provider_call(sink, provider=…, outcome=…, duration_ms=…, cache_hit=…, circuit_state=breaker.state)` |
| 토큰 사용량 | `record_llm_usage(sink, engine=…, model=…, input_tokens=…, output_tokens=…)` |
| 비용 | `record_cost(sink, engine=…, cost_usd=outcome.cost_usd, basis=outcome.cost_basis)` |
| 예산 | `BudgetTracker.record(organization_id=…, cost_usd=outcome.cost_usd, basis=outcome.cost_basis)` |

`MeteredOutcome.cost_usd`가 `None`이면 **그대로 넘겨 주십시오.** 0으로 바꾸지 마십시오.
`record_cost`와 `BudgetTracker`는 `None`을 `basis`별 '측정 불가'로 따로 셉니다. 0으로 접으면
가격표가 만료된 달의 예산 경보가 초록색으로 남고, 그것이 이 모듈이 존재하는 이유입니다.

`outcome` 문자열 중 `"RATE_LIMITED"`와 `"SERVER_ERROR"`는 전용 카운터를 추가로 올립니다.

---

## 8. `BudgetTracker`의 영속성 (설계 확인 요청)

현재 `BudgetTracker`는 **프로세스 메모리**에만 누적합니다. 재시작하면 그 달의 누계가 사라지고,
워커가 여러 프로세스면 각자 따로 셉니다. 실제 예산 한도를 강제하려면 DB 테이블이 필요합니다
(`organization_id`, `month`, `spent_usd`, `measured_calls`, 사유별 `unmeasurable_calls`).

이 패키지는 `veo/db/**`와 마이그레이션을 소유하지 않으므로 스키마를 만들지 않았습니다.
`BudgetTracker.record()` / `.report()` 시그니처는 저장소가 바뀌어도 그대로 유지되도록
설계했습니다. 스키마 소유자가 정해지면 알려 주십시오.

---

## 9. 메트릭 익스포터 (미래 작업, 이 패키지 소유 아님)

`MetricSink`는 3개 메서드짜리 프로토콜입니다. Prometheus/OTLP/StatsD 어댑터는 이 프로토콜을
구현하고 `set_metric_sink(...)`로 설치하면 되며, 호출 지점은 한 줄도 바뀌지 않습니다.
`set_metric_sink`는 받은 객체를 `SafeMetricSink`로 감싸므로, 익스포터가 던지는 예외가 요청으로
새어 나가지 않습니다. 이 패키지에는 `prometheus_client` 의존성이 없고 앞으로도 없어야 합니다.
