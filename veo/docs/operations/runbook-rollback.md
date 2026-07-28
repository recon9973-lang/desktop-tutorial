# 런북: 롤백

나쁜 배포를 되돌립니다.

**핵심 한 문장부터**: 코드는 되돌릴 수 있습니다. 데이터는 대개 되돌릴 수 없습니다.
그리고 VEO 에는 **설계상 되돌릴 수 없는 것** 이 있습니다 — 그건 되돌리는 게 아니라
새 버전으로 **대체(supersede)** 해야 합니다 (§4).

> 이 문서의 마이그레이션 관련 주장은 전부 실제로 돌려서 확인했습니다.
> PostgreSQL 16.14, 2026-07-28, 일회용 DB `veo_rollback_demo`.
> 실행 출력은 각 절에 그대로 붙여 두었습니다.

---

## 0. 롤백하기 전에 30초만

1. **정말 롤백인가?** 롤백은 공짜가 아닙니다. 배포 이후 들어온 데이터가 옛 코드에서
   어떻게 보일지 아무도 모릅니다. 앞으로 고치는 게 (hotfix) 빠른 경우가 많습니다.
2. **마이그레이션이 포함된 배포인가?** 이게 갈림길입니다.
   ```bash
   cd apps/api && ../../.venv/bin/python -m alembic current
   git log --oneline -- apps/api/alembic/versions | head -5
   ```
   - 마이그레이션 **없음** → §1. 쉽습니다.
   - 마이그레이션 **있음** → §2. 읽고 하세요.
3. **먼저 백업합니다.** 롤백이 더 나쁜 결과를 낳았을 때 돌아올 지점.
   ```bash
   infra/backup/backup.sh --database veo --out /var/backups/veo/pre-rollback-$(date -u +%Y%m%dT%H%M%SZ)
   ```
4. 시각·담당자·롤백 사유를 기록합니다.

---

## 1. 마이그레이션 없는 배포 되돌리기

가장 흔하고 가장 안전한 경우입니다.

```bash
# 이전 이미지/커밋으로 되돌립니다 (배포 도구에 맞게)
git revert <bad-sha>            # 히스토리를 남기는 쪽. force-push 하지 마세요.
```

순서:

1. **API 와 워커를 같은 버전으로** 되돌립니다. 한쪽만 되돌리면 워커가 모르는
   태스크 이름이 큐에 남고, 그건 `dead_letter` 로 갑니다
   (`runbook-incident-response.md` §2.4).
2. `GET /api/health` 로 버전을 확인합니다.
3. 롤백 전에 큐에 들어간 잡은 옛 코드가 처리합니다. 그 잡들이 새 코드에서만
   말이 되는 파라미터를 들고 있다면 실패합니다 — 실패하게 두고, `jobs.error_code`
   로 확인한 뒤 재요청 여부를 판단합니다.

끝났다고 판단하는 기준: 버전이 맞고, 5xx 율이 배포 전 수준이고, `dead_letter` 가 0.

---

## 2. 마이그레이션이 포함된 배포 되돌리기

### 2.1 먼저 알아야 할 것 — alembic downgrade 는 백업이 아닙니다

`downgrade` 는 스키마를 되돌립니다. **그 스키마 안에 있던 데이터는 되돌리지
않습니다. 지웁니다.** 그리고 다시 `upgrade` 해도 돌아오지 않습니다.

실제로 확인한 것 (head `ce5b2b2c3f1e` → `-1` → 다시 head):

```
before downgrade:
1                                        ← brand_identities 행 1개
INFO  Running downgrade ce5b2b2c3f1e -> 7f3c9a1d64e2, brand identity and run completeness
INFO  Running upgrade 7f3c9a1d64e2 -> ce5b2b2c3f1e, brand identity and run completeness
brand_identities rows after down+up round trip:
0                                        ← 사라짐
```

`ce5b2b2c3f1e` 의 `downgrade()` 는 `brand_identities` 테이블을 통째로 `drop` 하고
`observation_runs` 에서 컬럼 6개(`is_complete`, `stopped_reason`,
`executions_planned`, `executions_skipped`,
`prompts_below_repetition_floor`, `skipped_detail`)를 `drop` 합니다.
그 안에 있던 값은 어디에도 남지 않습니다.

### 2.2 이 저장소의 마이그레이션별 실제 영향

| revision | 무엇을 되돌리나 | downgrade 하면 잃는 것 |
|---|---|---|
| `ce5b2b2c3f1e` (head) | 브랜드 아이덴티티, 실행 완전성 컬럼 | **`brand_identities` 전체.** 고객이 입력한 상호·주소어·전화번호·구분어. 재입력해야 합니다. `observation_runs` 의 완전성 정보 6컬럼 |
| `7f3c9a1d64e2` | DB 레벨 불변성 트리거 | 데이터는 안 잃습니다. **대신 보장이 사라집니다** — §3 |
| `9f0c1c619171` | 세션·자격증명·로그인 시도 | **`provider_credentials` 전체** (모든 고객 제공자 키), `user_sessions` (전원 로그아웃), `login_attempts` (잠금 이력) |
| `ac33acd167c5` | 최초 스키마 | 전부. 사실상 서비스 삭제입니다 |

**`9f0c1c619171` 이하로 내리는 것은 롤백이 아니라 재해입니다.** 자격증명은 암호문이라
백업에서 복구해도 마스터키가 있어야 읽힙니다 (`runbook-backup-restore.md` §5).

### 2.3 그래서 어떻게 하나

**원칙: 앞으로 고치세요 (roll forward).** 스키마를 내리는 건 마지막 수단입니다.

| 상황 | 방법 |
|---|---|
| 새 코드가 버그, 스키마는 무해 | **코드만 되돌립니다.** 스키마는 head 그대로 둡니다. 새로 추가된 컬럼/테이블을 옛 코드가 안 쓸 뿐입니다. **이게 거의 항상 정답입니다.** |
| 마이그레이션 자체가 잘못됨 (잘못된 제약, 잘못된 기본값) | **새 마이그레이션을 앞으로 씁니다.** 잘못된 것을 고치는 마이그레이션을 추가합니다. downgrade 하지 않습니다 |
| 마이그레이션이 데이터를 파괴했음 | downgrade 로는 못 되돌립니다. `runbook-backup-restore.md` 의 **복구** 절차입니다 |
| 배포 직후, 새 스키마에 아무 데이터도 안 들어감 | downgrade 가 안전할 수 있습니다. §2.4 의 확인을 먼저 하세요 |

### 2.4 downgrade 를 정말 해야 한다면

```bash
# 1) 무엇이 지워질지 눈으로 확인합니다 — 실행하지 말고 SQL 만 뽑습니다
cd apps/api
../../.venv/bin/python -m alembic downgrade -1 --sql

# 2) 지워질 테이블에 실제로 데이터가 있는지 셉니다
psql -d veo -c "SELECT count(*) FROM brand_identities"

# 3) 0이 아니면 멈추고, 그 데이터를 따로 뜹니다
pg_dump --host="$PGHOST" --username=veo --dbname=veo \
  --format=custom --table=brand_identities \
  --file=/var/backups/veo/brand_identities-$(date -u +%Y%m%dT%H%M%SZ).dump

# 4) 앱을 먼저 멈추고
# 5) 그 다음에 내립니다
../../.venv/bin/python -m alembic downgrade -1
```

`--sql` 로 먼저 보는 단계를 건너뛰지 마세요. 자동 생성된 downgrade 는 사람이 검토한
적 없는 `DROP` 을 들고 있을 수 있습니다.

---

## 3. 되돌릴 수 없는 것 (1) — 불변성 트리거를 내리면 보장이 사라집니다

`7f3c9a1d64e2` 는 두 개의 DB 레벨 트리거를 만듭니다:

- `report_versions_are_immutable` — `report_versions` 에 **UPDATE 자체를 금지**
- `scoring_versions_freeze_when_published` — `PUBLISHED`/`RETIRED` 상태의 점수 명세는
  `specification`, `checksum`, `spec_id`, `semantic_version`,
  `golden_fixture_results` 를 바꿀 수 없음

이걸 downgrade 하면 **데이터는 하나도 안 없어집니다.** 그래서 안전해 보입니다.
안전하지 않습니다. 실제로 돌려 본 결과:

```
=== WITH trigger (at head): try to edit a delivered report ===
ERROR:  VEO: report_versions is append-only; row 4444…4444 cannot be updated

INFO  Running downgrade 7f3c9a1d64e2 -> 9f0c1c619171, Enforce immutability …

=== AFTER downgrading past 7f3c9a1d64e2: same UPDATE ===
UPDATE 1
{"seo": {"score": 95.0}}          ← 고객에게 나간 72.5 가 조용히 95.0 이 됐습니다
```

그리고 다시 head 로 올리면:

```
after re-upgrade to head, the report says:
{"seo": {"score": 95.0}}          ← 원래 값은 돌아오지 않습니다
and the trigger is back:
ERROR:  VEO: report_versions is append-only; …
```

트리거는 돌아오지만 **바뀐 숫자는 안 돌아옵니다.** 그리고 이제 그 행은 다시 불변이
되어, 고쳐진 거짓말이 영구히 고정됩니다.

교훈: 이 revision 아래로 내려가 있는 동안에는 **`report_versions` 와
`scoring_versions` 에 어떤 쓰기도 하지 마세요.** ORM 이벤트 리스너는 남아 있지만
그건 ORM 을 통과하는 코드에만 적용됩니다 — psql 세션, 관리 스크립트, 마이그레이션은
그냥 지나갑니다. 그게 애초에 이 트리거를 만든 이유입니다.

---

## 4. 되돌릴 수 없는 것 (2) — 대체(supersede)해야 하는 것들

### 4.1 `report_versions` 는 append-only 입니다

DB 레벨에서 UPDATE 가 금지되어 있습니다. 잘못된 리포트가 나갔다면:

- **고치지 않습니다.** 고칠 수 없습니다.
- **새 버전을 발행합니다.** `version_number` 를 올린 새 행을 만듭니다.
- 고객에게 새 버전이 나온 이유를 알립니다. 옛 버전은 남아 있고, 남아 있어야 합니다 —
  고객이 이미 본 숫자를 우리가 조용히 지웠다는 사실이 나중에 밝혀지는 것이
  틀린 숫자를 냈던 것보다 나쁩니다.

```sql
-- 잘못 나간 버전 확인 (고치지 말고 확인만)
SELECT id, report_id, version_number, created_at, content->'seo'->>'score'
FROM report_versions WHERE report_id = '<report-uuid>'
ORDER BY version_number;
```

### 4.2 발행된 점수 명세는 동결됩니다

`scoring_versions` 가 `PUBLISHED` 나 `RETIRED` 가 되면 명세·체크섬·골든 결과는
트리거가 잠급니다. `status` 는 바뀔 수 있습니다 (발행 → 폐기).

배포된 명세에 오류가 있으면:

- 그 버전을 **수정하지 않습니다.** 못 합니다.
- 새 semantic version 을 발행합니다.
- 옛 버전을 `RETIRED` 로 바꿉니다 (이건 트리거가 허용합니다).
- **이미 그 명세로 계산된 점수는 그대로 둡니다.** 그 점수는 그 시점의 그 방법론으로
  낸 값이고, 그게 사실입니다. 소급해 다시 계산하면 고객이 받은 리포트와 DB 가
  달라지고, 어느 쪽이 진짜인지 아무도 말할 수 없게 됩니다.
  다시 재려면 새 스캔을 돌리고 새 리포트 버전을 냅니다.

### 4.3 감사 로그와 답변 저장소

- `audit_logs` 는 지우지 않습니다. 롤백 때문에 지저분해 보여도 지우지 않습니다.
- 답변 저장소(`answer_store`)의 파일은 내용 해시로 봉인되어 있습니다. 고치면
  읽을 때 `AnswerTamperedError` 가 납니다. 잘못된 답변을 "고치는" 방법은 없습니다 —
  새로 수집하는 것뿐입니다.

---

## 5. 롤백 후 확인

```bash
# 1) 코드 버전
curl -s https://<api-host>/api/health | python3 -m json.tool

# 2) 스키마 위치가 코드가 기대하는 곳인가
cd apps/api && ../../.venv/bin/python -m alembic current

# 3) 워커가 API 와 같은 버전인가  (검증 안 됨 — 이 머신에 celery CLI 실행 환경 없음)
celery -A veo_worker.runtime.app:celery_app inspect stats

# 4) 테넌트 격리가 멀쩡한가 — 롤백이 제약을 건드렸을 수 있습니다
psql -d veo -c "SELECT count(*) FROM projects WHERE organization_id IS NULL"
#   반드시 0. 아니면 runbook-incident-response.md §4

# 5) 불변성 트리거가 살아 있는가
psql -d veo -c "\d report_versions" | grep report_versions_are_immutable
#   비어 있으면 트리거가 없는 것입니다. 위험 상태입니다 (§3)
```

`5)` 를 확인하는 더 확실한 방법 — 실제로 거부되는지 봅니다 (읽기 전용 트랜잭션):

```bash
psql -d veo <<'SQL'
BEGIN;
UPDATE report_versions SET version_number = version_number WHERE false;
ROLLBACK;
SQL
```

이건 행을 건드리지 않으므로 안전하고, 트리거의 존재 여부만 확인할 때는
`\d` 쪽이 명확합니다.

---

## 6. 롤백이 답이 아닌 경우

| 증상 | 롤백보다 나은 것 |
|---|---|
| 특정 엔드포인트만 5xx | 그 엔드포인트를 내리고 hotfix |
| 성능만 나쁨 | 동시성·워커 수 조정, 원인 파악 후 앞으로 고치기 |
| 마이그레이션이 데이터를 파괴 | 롤백이 아니라 **복구**. `runbook-backup-restore.md` |
| `TenantIsolationError` | 엔드포인트를 내리고 `runbook-incident-response.md` §4. 롤백은 그 다음 |
| 리포트 숫자가 틀림 | 롤백해도 이미 나간 리포트는 안 바뀝니다. §4.1 대체 |

---

## 7. 에스컬레이션

- `alembic downgrade` 로 **데이터가 지워진 것을 알게 된 경우**: 즉시 멈추고
  인프라 책임자에게 보고. 복구 절차로 넘어갑니다.
- 자격증명 테이블이 사라진 경우 (`9f0c1c619171` 이하로 내려감): 보안 담당자.
  고객 재입력이 필요합니다.
- 이미 고객에게 나간 리포트의 수치가 잘못됐음이 확인된 경우: 서비스 책임자.
  §4.1 의 대체 발행과 고객 커뮤니케이션이 필요합니다.
