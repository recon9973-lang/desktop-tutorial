# VEO 부하 하네스

무엇을 재는지, 그리고 **무엇을 재지 못하는지**를 같이 적어 둡니다.
재지 못한 것을 적지 않으면 다음 사람이 재 봤다고 믿습니다.

---

## 0. 가장 중요한 규칙 — 남의 사이트를 때리지 않는다

VEO 의 크롤러는 남의 홈페이지를 가져옵니다. 부하 테스트는 정의상 기계가 낼 수 있는
가장 빠른 속도로 요청을 쏘는 일입니다. 이 둘을 붙이면 그건 부하 테스트가 아니라
어느 병원 홈페이지에 대한 서비스 거부 공격이고, 거기에는 우리 회사 IP 가 붙습니다.

그래서 이 디렉터리의 모든 표적은 **이 컴퓨터** 입니다.

- URL 을 받는 모든 경로는 `safety.assert_local_target()` 을 먼저 통과합니다.
- 통과하는 건 **루프백뿐** 입니다. 사설 대역(10.x, 192.168.x)도 거부합니다 —
  사설 주소도 결국 누군가의 장비입니다.
- **우회 플래그는 없습니다.** 원격 표적이 정말 필요하면 그건 환경변수로 켜는 일이
  아니라 사람과 상의할 일입니다.

확인한 동작:

```
$ PYTHONPATH=infra/load .venv/bin/python -c "..."
loopback ok: http://127.0.0.1:8731/
refused: https://www.example.com/ -> refusing to load-test 'www.example.com'.
refused: http://10.0.0.5/        -> refusing to load-test '10.0.0.5'.
refused: http://veo.co.kr/       -> refusing to load-test 'veo.co.kr'.
```

사이트가 필요하면 `infra/load/fixtures/site` 를 `fixture_site.py` 가 127.0.0.1 에
띄웁니다. 바인드 주소는 설정값이 아니라 상수입니다.

---

## 1. 실행

```bash
# API 만
.venv/bin/python infra/load/run.py --requests 600 --concurrency 16 --only api

# DB 시나리오까지 (마이그레이션된 DB + organizations 1행 필요)
VEO_LOAD_DATABASE_URL="postgresql+psycopg://localhost:5432/veo_load" \
  .venv/bin/python infra/load/run.py --requests 600 --concurrency 16

# 큐 백로그 (브로커 필요, 아래 §4 참고)
VEO_LOAD_BROKER_URL=redis://localhost:6379/1 \
  .venv/bin/python infra/load/run.py --only queue
```

DB 시나리오용 데이터베이스를 만드는 법:

```bash
createdb veo_load
cd apps/api && VEO_DATABASE_URL="postgresql+psycopg://localhost:5432/veo_load" \
  ../../.venv/bin/python -m alembic upgrade head
# organizations 1행과 projects 몇 행을 넣습니다 (§3 의 측정은 org 1 / project 25 기준)
```

---

## 2. 이 하네스가 재는 것과 못 재는 것

API 는 **프로세스 안에서** `httpx.ASGITransport` 로 구동합니다.

재는 것 (진짜입니다):

- FastAPI 라우팅·검증·의존성 그래프
- 점수 evaluator (제품의 핵심 경로)
- DB 시나리오에서는 SQLAlchemy·커넥션 풀·실제 PostgreSQL

**재지 못하는 것** (여기 나온 숫자를 용량 산정에 쓰지 마세요):

- 소켓·TLS·와이어 상의 HTTP 파싱 — 없습니다
- uvicorn 의 이벤트 루프, 워커 수, 백프레셔 — 전혀 건드리지 않습니다
- 리버스 프록시, 로드밸런서, 네트워크 지연

즉 여기 지연시간은 **운영 지연시간의 하한** 입니다. 용도는 하나입니다:
"이번 변경으로 evaluator 가 4배 느려졌나?" 를 잡는 회귀 기준선.

백분위수는 표본이 받쳐 줄 때만 인쇄합니다. p95 는 성공 표본 100개, p99 는 500개가
없으면 숫자 대신 `n/a (needs >=500 ok samples, had 60)` 을 찍습니다. 표본 40개로 낸
p99 는 최댓값에 더 그럴듯한 이름을 붙인 것뿐입니다.

---

## 3. 실측값 (2026-07-28, 이 저장소, macOS / Python 3.14 / PostgreSQL 16.14)

`--requests 600 --concurrency 16`, 시나리오당 워밍업 10회 버림.

| 시나리오 | 처리량 | p50 | p95 | p99 | 오류율 |
|---|---:|---:|---:|---:|---:|
| `health` | 3658/s | 4.30 ms | 5.17 ms | 5.59 ms | 0% |
| `scoring-spec-list` | 1119/s | 14.07 ms | 17.70 ms | 20.51 ms | 0% |
| `scoring-spec-detail` | 1708/s | 9.30 ms | 11.58 ms | 12.69 ms | 0% |
| `scoring-evaluate` | 951/s | 15.76 ms | 24.43 ms | 45.87 ms | 0% |
| `projects-list` (PostgreSQL) | 230/s | 63.6 ms | 105 ms | 125 ms | 0% |

`projects-list` 만 **재측정하지 않았습니다.** 위 실행은 `--only api` 라 DB 시나리오를
돌리지 않았습니다. 그 행만 스펙 캐시 도입 **이전** 값이 그대로 남아 있습니다.

### 스펙 캐시 도입 전후

`spec.py` 의 `load_spec_file()` 에 파싱 결과 캐시가 들어가기 전(같은 날 이른 시각)
측정값과 비교하면:

| 시나리오 | 전 | 후 | 배수 |
|---|---:|---:|---:|
| `health` (코드 변경 없음) | 3118/s | 3658/s | 1.2× |
| `scoring-spec-list` | 32/s | 1119/s | **35×** |
| `scoring-spec-detail` | 64/s | 1708/s | **27×** |
| `scoring-evaluate` | 61/s | 951/s | **16×** |

읽는 법:

- **`health` 도 손대지 않았는데 1.2배 움직였습니다.** 이게 이 하네스의 잡음
  바닥입니다. 실행 간 ±20% 는 의미 없는 변동으로 보십시오. 위 35×·27×·16× 는
  잡음보다 한참 크므로 결론은 확실합니다. 반대로 1.2배짜리 변화를 개선이라고
  주장하면 안 됩니다.
- 원인이었던 것: `load_spec()` 이 요청마다 스펙 YAML 을 다시 읽고, 파싱하고, JSON
  스키마 전체 검증을 다시 돌렸습니다. `GET /api/scoring/specs` 는 발행된 스펙을
  **전부** 그렇게 했습니다. 지금은 `load_spec_file()` 이 `(경로, 크기, mtime_ns)`
  로 파싱 결과를 캐시합니다. 파일이 바뀌면 키가 바뀌므로 새 버전 발행도, 테스트가
  스펙 루트를 복사본으로 바꿔치기하는 것도 자동으로 반영됩니다.
- **남은 격차는 정상입니다.** `health` 대비 `scoring-spec-detail` 2.1배,
  `scoring-evaluate` 3.8배. 이 엔드포인트들은 47개 검사 항목을 직렬화하고 실제로
  evaluator 를 돌립니다. 아무 일도 안 하는 라우트와 같아질 이유가 없습니다.
- `scoring-evaluate` 만 p99(45.87 ms)가 p50(15.76 ms)의 **3배**로 벌어집니다. 다른
  시나리오는 1.4배 수준입니다. 계산이 실제로 도는 유일한 경로라 스케줄링 지터가 더
  드러납니다. 지금은 문제로 보지 않지만, 이 비율이 더 벌어지면 여기부터 보십시오.
- `projects-list` 는 이제 점수 엔드포인트보다 **느립니다**(230/s 대 951~1708/s).
  캐시 이전과 정반대입니다. 병목이 DB 가 아니었다는 사실은 그대로이고, 이제는
  DB 시나리오가 이 표에서 가장 느린 축입니다. 다음에 볼 곳은 여기입니다.
- 오류율 0% 는 정상 기준선입니다. 오류가 섞인 실행은 기준선이 아닙니다 —
  `run.py` 는 그런 경우 종료코드 1 을 냅니다.

---

## 4. 큐 백로그 — 이 환경에서 **검증되지 않았습니다**

목표는 "큐가 얼마나 빠른가" 가 아니라 **"생산을 멈추면 백로그가 빠지는가, 아니면
멈춰 버리는가"** 입니다. 과부하에서 멈추는 큐는 트래픽이 줄어도 스스로 회복하지
않습니다. 백로그가 정점을 찍은 그 시각에 사람이 붙어야 합니다.

**이 컴퓨터에는 Redis 가 없고, 그래서 이 항목은 측정하지 못했습니다.**

시도한 것과 결과:

1. **eager 모드** (`VEO_BROKER_URL` 미설정). Celery 가 태스크를 호출자 안에서
   그 자리에서 실행합니다. 큐에 들어가는 것도, 꺼내는 것도 없습니다.
   여기서 "드레인 시간" 을 재면 for 루프 속도를 재서 큐 회복이라고 부르는 겁니다.
2. **kombu `memory://` 인프로세스 전송.** 원칙이 아니라 측정으로 탈락시켰습니다.
   실제 Celery 워커(스레드 2, 태스크 5 ms, `acks_late` 켜고 끄고, `polling_interval`
   5 ms)로 60건을 넣었을 때 15초 동안 16–18건만 소비하고 42–44건이 큐에 남은 채
   진전이 멈췄습니다. 테스트하려는 바로 그 조건에서 멈추는 전송으로는 그 조건에
   대한 주장을 할 수 없습니다.

그래서 `queue_backlog.py` 는 브로커가 없으면 **숫자를 만들어 내지 않고 거부합니다.**
거부 출력이 정직한 결과이고, 그게 이 항목의 결론입니다.

Redis 가 생기면:

```bash
VEO_LOAD_BROKER_URL=redis://localhost:6379/1 \
  .venv/bin/python infra/load/run.py --only queue --produce 2000
```

`VEO_LOAD_BROKER_URL` 은 `VEO_BROKER_URL` 과 **일부러 다른 변수** 입니다. 같은 변수를
쓰면 로컬 워커를 띄워 둔 사람이 진짜 잡이 도는 브로커에 2000건을 쏟아붓게 됩니다.
하네스는 시작 전에 대상 큐가 비어 있는지도 확인하고, 비어 있지 않으면 남의 백로그
위에 부하를 얹기를 거부합니다.

여전히 **검증되지 않은 채로 남는 것** (Redis 를 붙여도 이 하네스만으로는 못 봅니다):

- 워커가 죽었을 때의 재전달 (`acks_late` + visibility timeout)
- 워커 프로세스 여러 개 사이의 prefetch 분배
- 브로커 연결이 끊겼다 붙을 때의 동작
- dead-letter 큐로 실제로 흘러가는 경로

---

## 5. 파일

| 파일 | 하는 일 |
|---|---|
| `run.py` | CLI 진입점. `--only api` / `--only queue` |
| `api_load.py` | 시나리오 정의와 동시성 실행기 |
| `metrics.py` | 지연 백분위수·오류율. 표본이 모자라면 `n/a` |
| `queue_backlog.py` | 백로그·드레인 실험. 브로커 없으면 거부 |
| `fixture_site.py` | 루프백 전용 고정 사이트 서버 |
| `fixtures/site/` | 고정 HTML. 실제 의료기관 아님 |
| `safety.py` | 루프백 외 표적 거부. 우회 없음 |
