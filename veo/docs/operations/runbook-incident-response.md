# 런북: 장애 대응

새벽 3시에, 이걸 만들지 않은 사람이 읽는다고 가정합니다.
각 절은 **증상 → 확인 → 조치 → 끝났다고 판단하는 기준** 순서입니다.

> 검증 상태에 대해 먼저: 이 문서의 SQL 은 실제 VEO 스키마(PostgreSQL 16.14,
> alembic head `ce5b2b2c3f1e`)에 대해 컬럼명을 확인했습니다. Redis·Docker 가 없는
> 개발 머신에서 작성했으므로, **`redis-cli` 와 `celery` CLI 를 쓰는 명령은 실행해
> 보지 못했습니다.** 해당 위치에 그렇게 표시해 두었습니다.

---

## 0. 어떤 사고든 처음 5분

1. **시각과 담당자를 적습니다.** 나중에 "언제부터였나" 를 복원할 수 없으면 영향
   범위도 고지 여부도 판단할 수 없습니다.
2. **`request_id` 를 하나 확보합니다.** VEO 의 한 요청은 API → 큐 → 워커 → 제공자로
   흩어집니다. 상관관계 ID 없이 로그를 뒤지는 건 시간 낭비입니다.
   (`infra/monitoring/logging.md`)
3. **고치기 전에 증거를 남깁니다.** 재시작은 원인을 지웁니다. 최소한 로그 스냅샷과
   `jobs` 테이블의 현재 상태를 떠 두세요.
4. **이 사고가 §1~§4 중 무엇인지 판단합니다.** 셋 다이면 §4(테넌트 격리)가 항상
   최우선입니다. 나머지는 서비스 품질 문제이고, 그건 데이터 유출 문제입니다.

---

## 1. 외부 제공자 장애

**증상**: 특정 제공자를 쓰는 검사가 갑자기 전부 "측정 불가", 잡 실패율 급증,
`GET /api/providers` 에 `DEGRADED` 또는 `CIRCUIT_OPEN`.

### 1.1 확인 — 우리 문제인가 저쪽 문제인가

```bash
curl -s https://<api-host>/api/providers | python3 -m json.tool
```

`state` 가 무엇인지가 처방을 가릅니다. 이건 VEO 가 일부러 구분해 두는 값입니다
(ADR 0004):

| state | 뜻 | 이 절의 대상인가 |
|---|---|---|
| `CIRCUIT_OPEN` | 연속 실패로 우리가 호출을 끊었다 | **예** |
| `DEGRADED` | 응답이 불안정하다 | **예** |
| `DISABLED_NO_CREDENTIAL` | 자격증명이 아예 없다 | 아니오 — 설정 문제 |
| `DISABLED_INVALID_CREDENTIAL` | 값은 있는데 못 쓰는 값(예: `[SENSITIVE]` 자리표시자) | 아니오 — 설정 문제 |
| `NOT_AVAILABLE` | 제공자가 그 기능을 공개 API 로 안 준다 | 아니오 — 영구 상태 |

최근 실패의 모양:

```sql
SELECT type, error_code, count(*), max(finished_at) AS latest
FROM jobs
WHERE status = 'FAILED' AND finished_at > now() - interval '1 hour'
GROUP BY type, error_code
ORDER BY count(*) DESC;
```

`error_code` 가 `PROVIDER_RATE_LIMITED` 인지 `PROVIDER_UNAVAILABLE` 인지
`PROVIDER_UNAUTHORIZED` 인지가 결정적입니다.

### 1.2 조치

| error_code | 뜻 | 조치 |
|---|---|---|
| `PROVIDER_UNAVAILABLE` | 저쪽이 죽었다 | **아무것도 고치지 마세요.** 재시도 폭풍만 만듭니다. 상태 페이지 확인, 고객 공지, 복구 대기 |
| `PROVIDER_RATE_LIMITED` | 우리가 너무 많이 불렀다 | 해당 큐의 워커 동시성을 낮춥니다. 배치 스케줄을 미룹니다. 한도 상향을 협의합니다 |
| `PROVIDER_UNAUTHORIZED` / `_FORBIDDEN` | 키가 죽었거나 권한이 빠졌다 | `runbook-provider-credentials.md` 로. 키 교체가 필요합니다 |

**절대 하지 말 것**: 제공자 장애를 "추정값" 으로 메우는 것. VEO 는 측정 못 한 것을
측정 못 했다고 말합니다. 그게 제품의 전부입니다. 그럴듯한 숫자를 넣으면 고객은
그걸 측정값으로 믿고, 그 신뢰는 되돌릴 수 없습니다.

### 1.3 끝났다고 판단하는 기준

- `GET /api/providers` 가 `ENABLED` 로 돌아왔고,
- 최근 15분 잡 실패율이 평소 수준이고,
- 장애 구간에 **측정 불가로 기록된 검사** 를 재실행할지 결정했다.
  (자동 재실행하지 마세요. 재실행은 비용이 들고, 고객이 이미 받아 본 리포트의
  숫자를 조용히 바꿉니다. 재실행할 거면 새 스캔으로, 기록을 남기고.)

---

## 2. 큐 백로그

**증상**: 잡이 `QUEUED` 에서 안 움직임, 진행률 정체, "리포트가 안 나온다" 문의.

### 2.1 확인 — 밀린 건가, 멈춘 건가

이 둘은 완전히 다른 사고입니다. **밀린 것** 은 소비가 되고 있는데 생산이 더 빠른
상태고, 시간이 해결합니다. **멈춘 것** 은 소비가 0 이고, 사람이 붙어야 합니다.

```sql
-- 상태별 잡 수와 가장 오래 대기 중인 것
SELECT status, count(*),
       min(created_at) AS oldest,
       now() - min(created_at) AS waited
FROM jobs
WHERE created_at > now() - interval '6 hours'
GROUP BY status ORDER BY count(*) DESC;
```

```sql
-- 지난 10분 동안 실제로 끝난 잡이 있는가  ← 이게 핵심 질문
SELECT count(*) FROM jobs
WHERE finished_at > now() - interval '10 minutes';
```

**0 이면 멈춘 것입니다.** 0 이 아니면 밀린 것입니다.

브로커 쪽 깊이 (**이 명령은 이 머신에서 검증되지 않았습니다 — Redis 가 없습니다**):

```bash
redis-cli -u "$VEO_BROKER_URL" llen crawl
redis-cli -u "$VEO_BROKER_URL" llen seo
redis-cli -u "$VEO_BROKER_URL" llen geo
redis-cli -u "$VEO_BROKER_URL" llen keyword
redis-cli -u "$VEO_BROKER_URL" llen report
redis-cli -u "$VEO_BROKER_URL" llen dead_letter    # 여기가 0이 아니면 §2.4
```

큐 이름은 `veo_worker/runtime/app.py` 의 `QUEUE_NAMES` 에서 옵니다:
`crawl`, `seo`, `geo`, `keyword`, `report`, 그리고 `dead_letter`.

살아 있는 워커 (**검증되지 않음**):

```bash
celery -A veo_worker.runtime.app:celery_app inspect active
celery -A veo_worker.runtime.app:celery_app inspect reserved
```

### 2.2 멈췄을 때

원인은 대개 셋 중 하나입니다.

1. **워커가 없다.** `inspect active` 가 비었거나 응답이 없음 → 워커 프로세스/파드가
   죽었습니다. 다시 띄웁니다. 왜 죽었는지는 그 다음에 봅니다 (OOM 이 흔합니다).
2. **워커는 있는데 한 잡에 묶여 있다.** `inspect active` 에 오래된 잡 하나가
   `prefetch_multiplier=1` 로 각 워커를 붙들고 있음 → 소프트 타임리밋
   (`VEO_WORKER_TASK_SOFT_TIME_LIMIT`, 기본 1500초)이 걸릴 때까지 기다리거나,
   그 잡을 취소합니다.
3. **브로커에 못 붙는다.** 워커 로그에 연결 오류 → Redis 를 봅니다. 여기서
   워커를 계속 재시작해 봐야 아무 소용 없습니다.

큐를 **비우지 마세요** (`redis-cli FLUSHDB` 금지). 고객이 요청한 작업이 조용히
사라지고, 그들은 결과를 계속 기다립니다. 반드시 비워야 한다면 먼저 `jobs` 에서
해당 행을 실패 처리해 고객이 알 수 있게 합니다.

### 2.3 밀렸을 때

- 어느 큐인지 봅니다. 한 큐만 밀렸으면 그 잡 종류의 문제입니다 (보통 `crawl`).
- 그 큐의 워커를 늘립니다. 큐가 종류별로 나뉘어 있는 이유가 이것입니다 —
  느린 크롤이 키워드 조회를 굶기지 않도록.
- **생산을 줄이는 쪽이 대개 더 빠릅니다.** 예약 스캔을 미루고, 대량 등록을 멈춥니다.
- 드레인 속도를 재서 언제 끝날지 고객에게 말할 수 있게 합니다.

> **알려진 미검증 영역**: "생산을 멈추면 백로그가 실제로 빠지는가" 는 이 저장소에서
> **측정된 적이 없습니다.** 개발 머신에 Redis 가 없어서입니다. 하네스는
> `infra/load/queue_backlog.py` 에 있고 브로커만 있으면 돌아갑니다:
> ```
> VEO_LOAD_BROKER_URL=redis://localhost:6379/1 \
>   .venv/bin/python infra/load/run.py --only queue --produce 2000
> ```
> 스테이징에 Redis 가 생기면 이걸 먼저 돌리고 이 문단을 실제 숫자로 바꿔 주세요.
> 자세한 사정은 `infra/load/README.md` §4.

### 2.4 dead_letter 큐가 비어 있지 않을 때

`dead_letter` 는 **아무도 받아 갈 수 없는 메시지** 가 가는 곳입니다
(`route_task()` 가 등록되지 않은 태스크 이름을 여기로 보냅니다).

여기 메시지가 쌓인다는 건 보통 **배포 불일치** 입니다: API 가 새 태스크 이름으로
잡을 넣고 있는데 워커는 아직 옛 코드입니다.

1. API 와 워커의 배포 버전을 비교합니다.
2. 워커를 API 와 같은 버전으로 올립니다.
3. dead-letter 메시지는 자동으로 재처리되지 않습니다. 해당 `jobs` 행을 찾아
   재요청할지 판단합니다.

### 2.5 끝났다고 판단하는 기준

- `QUEUED` 수가 계속 **감소** 하고 있고,
- 가장 오래된 대기 잡의 나이가 줄고 있고,
- `dead_letter` 가 0 이고,
- 밀린 동안 만료된 잡(`expires_at` 경과)이 있으면 고객에게 알렸다.

---

## 3. 자격증명 유출 의심

**증상**: 로그·티켓·스크린샷·깃 커밋에서 제공자 키로 보이는 문자열 발견, 제공자로부터
비정상 사용 통지, 백업 파일이 통제 밖으로 나감.

**의심되면 유출된 것으로 취급합니다.** "아마 괜찮을 것" 은 판단이 아닙니다.

### 3.1 먼저 — 확산시키지 마세요

- 의심되는 값을 **채팅·티켓·이 문서 어디에도 붙여넣지 마세요.** 유출 조사가
  유출을 늘리는 가장 흔한 경로입니다.
- 스크린샷을 찍지 마세요.
- 대화할 때는 조직 ID + 제공자 + 필드로 지칭합니다.

### 3.2 범위 판단

무엇이 샜는지에 따라 완전히 다릅니다.

| 샌 것 | 의미 | 조치 |
|---|---|---|
| 제공자 API 키 (평문) | 그 고객의 제공자 계정이 노출 | §3.3 키 교체 |
| DB 덤프 / 백업 세트 | 암호문은 나갔지만 **마스터키는 안 나갔다** | §3.4 |
| `VEO_CREDENTIAL_ENCRYPTION_KEY` | **최악.** 덤프까지 같이 나갔으면 모든 고객의 자격증명이 평문과 같음 | §3.5 |

이 구분이 가능한 이유: 금고는 AES-256-GCM 이고 키는 DB 안에 없습니다. 그리고
암호문은 조직·제공자·필드·키버전에 묶여 있어(`build_associated_data`) 한 테넌트의
블롭을 다른 테넌트 행에 옮겨 붙여도 복호화되지 않습니다.

### 3.3 특정 자격증명이 샜을 때

1. **제공자 콘솔에서 먼저 폐기합니다.** VEO 에서 지우는 건 그 다음입니다 —
   VEO 에서 지워도 제공자 쪽 키는 살아 있습니다.
2. VEO 에서 비활성화:
   ```
   DELETE /api/credentials/{provider}
   ```
   (금고의 `deactivate`. 행을 지우지 않고 비활성화하며 암호문을 비웁니다.)
3. 새 키를 받아 재입력: `runbook-provider-credentials.md`.
4. 영향 기간의 사용 흔적을 확인합니다:
   ```sql
   SELECT created_at, actor_kind, action, target_type, target_id, request_id
   FROM audit_logs
   WHERE organization_id = '<org-uuid>'
     AND action LIKE 'credential%'
     AND created_at > now() - interval '30 days'
   ORDER BY created_at DESC;
   ```

### 3.4 백업/덤프가 통제 밖으로 나갔을 때

- 자격증명 자체는 **암호문** 입니다. 마스터키 없이는 복호화되지 않습니다
  (`apps/api/tests/operations/test_backup_restore.py` 가 이걸 검증합니다).
- 하지만 덤프에는 **고객 데이터 전체가 평문** 으로 들어 있습니다. 조직·프로젝트·
  사이트·리포트 내용·감사 로그. 개인정보 사고로 처리하세요. 자격증명이 안전한 것과
  고객 데이터가 안전한 것은 다른 얘기입니다.
- 마스터키 로테이션을 **권고** 합니다(필수는 아님): §3.5 절차의 로테이션 부분만.

### 3.5 마스터키가 샜을 때 — 최우선

1. 새 마스터키를 만듭니다 (32바이트, base64):
   ```bash
   .venv/bin/python -c "import base64,secrets;print(base64.b64encode(secrets.token_bytes(32)).decode())"
   ```
   출력은 화면에 남습니다. 바로 비밀 보관소에 넣고 터미널 기록을 정리하세요.
2. `VEO_CREDENTIAL_KEY_VERSION` 을 올리고, 새 키를
   `VEO_CREDENTIAL_ENCRYPTION_KEY` 에, **옛 키를
   `VEO_CREDENTIAL_PREVIOUS_ENCRYPTION_KEYS` 에** 둡니다. 옛 키가 없으면 기존 행을
   읽어서 다시 암호화할 수 없습니다.
3. `CredentialVault.rotate_key` 로 전 행을 재암호화합니다
   (`runbook-credential-rotation.md`).
4. **그런데 로테이션은 유출된 평문 자격증명을 무효화하지 않습니다.** 공격자가
   덤프 + 옛 키를 둘 다 가졌다면 이미 평문을 얻었습니다. 따라서 **모든 고객의 제공자
   키를 실제로 교체해야 합니다.** 이건 고객 커뮤니케이션이 필요한 일입니다.
5. 옛 키를 `VEO_CREDENTIAL_PREVIOUS_ENCRYPTION_KEYS` 에서 제거합니다.

### 3.6 끝났다고 판단하는 기준

- 제공자 콘솔에서 옛 키가 폐기됐고,
- VEO 에 새 키가 들어가 `verify` 가 성공하고,
- 로테이션이 필요했다면 `SELECT DISTINCT key_version FROM provider_credentials` 가
  새 버전 하나만 반환하고,
- 노출 경로(로그 설정, 접근 권한, 백업 위치)가 실제로 막혔습니다.
  같은 경로로 다시 샐 수 있으면 아직 안 끝난 겁니다.

---

## 4. 테넌트 격리 경보 (`TenantIsolationError`)

**운영에서 이 예외가 났다는 것은 VEO 의 버그이며, 다른 조직의 데이터가 노출됐을
가능성이 있다는 뜻입니다.** 고객 입력 문제가 아닙니다.

`veo/authz/errors.py`: *"쿼리가 조직 경계를 넘으려 했다. 구조적 가드가 낸 것이지
사용자 입력이 낸 것이 아니다."* 코드 경로가 테넌트 필터를 빠뜨렸다는 뜻입니다.

응답은 500 이고 내부 사정은 밖으로 나가지 않습니다. 로그에는
`veo.security` 로거로 `"tenant isolation guard tripped"` 와 `request_id` 가 남습니다.

### 4.1 이건 훈련이 아닙니다 — 순서대로

1. **먼저 `request_id` 를 잡습니다.** 로그에서:
   ```
   event="tenant isolation guard tripped" request_id=<...>
   ```
2. **그 요청이 무엇이었는지 특정합니다.** 어떤 엔드포인트, 어느 조직의 principal,
   어떤 리소스. `audit_logs.request_id` 로 붙습니다:
   ```sql
   SELECT created_at, organization_id, actor_user_id, action, target_type, target_id
   FROM audit_logs WHERE request_id = '<request-id>';
   ```
3. **같은 코드 경로가 얼마나 오래 살아 있었는지 봅니다.** 이 가드는 쿼리 *실행 전* 에
   터집니다 — 즉 이번 요청은 데이터를 반환하지 **않았습니다.** 위험한 건
   **가드가 없는 다른 경로** 입니다. 같은 배포에서 같은 종류의 쿼리가 성공적으로
   반환된 적이 있는지 확인해야 합니다.
   ```sql
   -- 같은 엔드포인트/액션의 최근 성공 요청
   SELECT created_at, organization_id, actor_user_id, request_id
   FROM audit_logs
   WHERE action = '<위에서 나온 action>'
     AND created_at > now() - interval '7 days'
   ORDER BY created_at DESC LIMIT 200;
   ```
4. **해당 엔드포인트를 내립니다.** 원인 코드가 확인될 때까지. 노출 가능성이 있는
   읽기 경로를 열어 둔 채 조사하지 마세요.
5. **보안 담당자와 개인정보 책임자에게 보고합니다.** 조직 간 데이터 노출은 고지
   의무가 걸릴 수 있는 사안이며, 그 판단은 엔지니어가 혼자 내리는 것이 아닙니다.
6. 롤백이 답이면 `runbook-rollback.md`.

### 4.2 절대 하지 말 것

- **가드를 끄거나 우회하지 마세요.** 이 예외는 유출을 막고 있는 것이지 유출을 일으키는
  것이 아닙니다. 끄면 500 이 사라지고 대신 남의 데이터가 응답에 실립니다.
- "재현이 안 된다" 를 종결 사유로 쓰지 마세요. 재현이 안 되는 격리 버그는
  타이밍·캐시·세션 재사용에 걸린 것일 수 있고, 그게 더 나쁩니다.
- 재시작으로 넘기지 마세요.

### 4.3 복구 직후에 이게 뜬다면

복구가 제약을 빠뜨렸을 수 있습니다. `runbook-backup-restore.md` §3.5 의
`organization_id IS NULL` 확인을 즉시 돌리고, 0 이 아니면 그 복구본을 폐기합니다.

### 4.4 끝났다고 판단하는 기준

- 원인 코드 경로가 특정되고 고쳐졌으며 회귀 테스트가 붙었고,
- 같은 배포에서 **실제로 남의 데이터가 반환된 요청이 있었는지** 결론이 났고,
- 있었다면 영향 조직·건수·기간이 문서화됐고 고지 판단이 끝났고,
- 내렸던 엔드포인트를 되살렸습니다.

---

## 5. 에스컬레이션 기준

| 상황 | 즉시 보고 대상 |
|---|---|
| `TenantIsolationError` (운영) | 보안 담당자 + 개인정보 책임자. **지체 없이** |
| 마스터키 유출 의심 | 보안 담당자. 고객 커뮤니케이션 준비 |
| DB 덤프가 통제 밖으로 | 보안 담당자 + 개인정보 책임자 |
| 백업 검증 연속 2회 실패 | 인프라 책임자. 백업 파이프라인을 장애로 처리 |
| 큐가 30분 이상 완전 정지 | 서비스 책임자. 고객 공지 판단 |
| 제공자 장애 4시간 초과 | 서비스 책임자. 고객 공지 |

관련 런북: `runbook-backup-restore.md`, `runbook-rollback.md`,
`runbook-credential-rotation.md`, `runbook-provider-credentials.md`.
