# 런북: 백업과 복구

새벽 3시에, 이걸 만들지 않은 사람이 읽는다고 가정하고 씁니다.
명령은 그대로 복사해서 붙일 수 있어야 하고, 실패했을 때 무엇을 하는지가 적혀 있어야 합니다.

> **검증하지 않은 백업은 백업이 아닙니다.**
> 그리고 **종료코드로 확인한 복구는 확인한 게 아닙니다.** `pg_restore` 는 절반만
> 들어간 데이터베이스에 대고도 0 을 반환합니다. 확인해야 하는 건 내용입니다.

---

## 0. 이 문서에서 검증한 것과 못 한 것

정직하게 먼저 적습니다. 검증하지 않은 절차를 검증한 것처럼 읽히게 두는 것이
"검증 못 했다" 고 적는 것보다 나쁩니다 — 사고 중에 누군가 그걸 그대로 따라갑니다.

| 절차 | 상태 | 근거 |
|---|---|---|
| `backup.sh` 로 실제 덤프 | **검증됨** | PostgreSQL 16.14 (Homebrew), 2026-07-28 |
| `restore.sh` 로 실제 복구 + 내용 검증 | **검증됨** | 아래 §3.3 의 실제 출력 |
| 복구 후 리포트 수치 재현 | **검증됨** | `apps/api/tests/operations/test_backup_restore.py` 17개 통과 |
| 복구 후 alembic head 일치 | **검증됨** | 같은 테스트 |
| 복구 후 `report_versions` 불변 트리거 생존 | **검증됨** | 같은 테스트 |
| 마스터키 없이 자격증명이 안 읽히는 것 | **검증됨** | 같은 테스트 (§5) |
| 답변 객체 저장소 백업·복구 + 무결성 | **검증됨** | 같은 테스트 |
| 손상된 덤프·수치 불일치·원본 덮어쓰기 거부 | **검증됨** | 같은 테스트 |
| **S3 업로드/다운로드 (`aws s3 cp`)** | **검증 안 됨** | 이 머신에 `aws` CLI 가 없습니다 |
| **WAL 아카이빙 / PITR** | **검증 안 됨** | 자체 운영 PostgreSQL 이 없습니다 |
| **컨테이너 환경에서의 실행** | **검증 안 됨** | 이 머신에 Docker 가 없습니다 |
| **관리형 PostgreSQL(RDS 등) 자동백업** | **검증 안 됨** | 해당 환경 없음 |

검증 안 된 줄을 처음 실행하는 사람은, 사고 중이 아니라 **평온한 오후에** 한 번 돌려
보고 이 표를 고쳐 주세요.

---

## 1. 무엇을 지키는가

| 대상 | 손실 시 영향 | RPO | RTO |
|---|---|---|---|
| PostgreSQL | 조직·프로젝트·스캔 결과·점수 이력 전부. 복구 불가 시 서비스 종료 수준 | 15분 | 1시간 |
| 객체 스토리지 (AI 원본 답변) | 보고한 모든 언급의 근거. 점수 재현·감사 근거 상실 | 24시간 | 4시간 |
| Redis | 진행 중인 잡. 재실행하면 됨 | 백업 안 함 | — |

RPO/RTO 는 **목표값** 입니다. §7 훈련에서 실제 측정치를 기록하고, 목표와 벌어지면
목표를 고치거나 절차를 고칩니다. 측정하지 않은 목표는 희망사항입니다.

객체 스토리지가 왜 DB 만큼 중요한지: `veo/observations/answer_store.py` 에 저장된
원본 답변이 VEO 가 보고하는 모든 언급의 근거입니다. DB 만 복구하면 "이 병원이
ChatGPT 답변에 언급됐습니다" 라고 주장하는 행은 살아나지만 그 주장을 확인할 답변은
사라집니다. 아무도 방어할 수 없는 숫자는 측정이 아닙니다.

---

## 2. 백업

### 2.1 명령

```bash
export PGPASSWORD='<보관소에서 조회>'          # 화면에 찍지 마세요
TS=$(date -u +%Y%m%dT%H%M%SZ)

infra/backup/backup.sh \
  --database veo \
  --host "$PGHOST" --port 5432 --user veo \
  --answer-store /var/lib/veo/answers \
  --out "/var/backups/veo/${TS}"

unset PGPASSWORD
```

스크립트가 만드는 것 — 이건 덤프 파일 하나가 아니라 **백업 세트** 입니다:

```
/var/backups/veo/<TS>/
  manifest.json          사람과 도구가 읽는 요약
  postgres.dump          pg_dump --format=custom (선택 복구 가능)
  postgres.dump.sha256   체크섬
  row-counts.json        public 스키마 모든 테이블의 정확한 행 수
  meta/…                 restore.sh 가 파서 없이 읽는 값들
  answers.tar.gz         답변 저장소
  answers.tar.gz.sha256
```

`row-counts.json` 과 `meta/alembic_head` 가 핵심입니다. 이게 없으면 복구를
**검증할 수 없고**, 검증할 수 없는 복구는 희망입니다.

### 2.2 스크립트가 거부하는 것

| 거부 | 이유 |
|---|---|
| `--database` 에 URI/conninfo | 비밀번호가 셸 히스토리·프로세스 목록·스크립트 출력에 남습니다. 그리고 입력한 이름과 다른 서버를 가리킬 수 있습니다 |
| `alembic_version` 이 없는 DB | 마이그레이션 안 된 (= 엉뚱한) DB 를 백업하면, 그 사실은 복구 때 알게 됩니다. 최악의 타이밍입니다. 정말 원하면 `--allow-unmigrated` |
| 연결이 다른 DB 에 붙은 경우 | `current_database()` 로 확인합니다 |

**비밀번호는 이 스크립트가 읽지도, 찍지도, 파일에 쓰지도 않습니다.** `PGPASSWORD`
또는 `~/.pgpass` 에서 libpq 가 직접 가져갑니다.

### 2.3 실제 실행 출력 (2026-07-28 검증)

```
==> Checking the connection lands on 'veo_backup_smoke'
  server_version : 16.14 (Homebrew)
  alembic head   : deadbeef1234
  public tables  : 2

==> Recording row counts for all 2 public tables

==> Dumping 'veo_backup_smoke'
  postgres.dump  : 2468 bytes
  sha256         : bc3bf5fa6788f87a04aeecb8c196a664c58760c7ef068c9f8bacc225a3d619a0

==> Archiving the answer store at .../answers
  answer files   : 1
  sha256         : b03d747a131b4d07c1a8fa59d1c254ddd9c8fe341801db8fdc81ccc3c74ee391

==> Backup set written to .../bk1
```

### 2.4 오프사이트로 옮기기 — **이 절은 검증되지 않았습니다**

이 머신에는 `aws` CLI 가 없어 아래 명령을 실행해 보지 못했습니다.
처음 쓰는 사람은 사고 중이 아닐 때 한 번 돌려 보고 이 문장을 지워 주세요.

```bash
aws s3 sync "/var/backups/veo/${TS}" "s3://veo-backups/postgres/${TS}/" --sse AES256
```

옮긴 뒤 로컬 사본을 지웁니다.

```bash
rm -rf "/var/backups/veo/${TS}"
```

> 예전 판에는 `shred -u` 가 적혀 있었습니다. **macOS 에는 `shred` 가 없습니다**
> (이 머신에서 확인). 리눅스 서버에서만 쓰세요. macOS 에서는 `rm -P`.
> 그리고 SSD·저널링 파일시스템에서는 어느 쪽도 덮어쓰기를 보장하지 않습니다.
> 진짜 방어선은 디스크 전체 암호화이지, 지우는 명령의 종류가 아닙니다.

> 덤프에는 고객 데이터 전체가 평문으로 들어 있습니다. 개발자 노트북에 남기지 마세요.

### 2.5 시점 복구 (PITR) — **검증되지 않았습니다**

RPO 15분은 일 1회 덤프로 달성할 수 없습니다. 운영에서는 WAL 아카이빙을 켭니다.

```
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://veo-backups/wal/%f --sse AES256'
archive_timeout = 900        # 15분. 트래픽이 없어도 이 주기로 WAL 을 끊는다.
```

관리형 PostgreSQL(RDS·Cloud SQL 등)이면 그쪽 자동 백업과 PITR 을 켜고 보존 기간만
확인하면 됩니다. 이 절의 수동 설정은 자체 운영일 때만 필요합니다.

### 2.6 보존 정책

| 종류 | 보존 |
|---|---|
| 일간 백업 세트 | 30일 |
| 주간 (일요일) | 12주 |
| 월간 (1일) | 12개월 |
| WAL 아카이브 | 35일 |
| 객체 버전 | 90일 |

보존 기간을 늘리는 것은 공짜가 아닙니다. 개인정보를 필요 이상으로 오래 들고 있는
것은 그 자체로 위험이며, 유출 시 피해 범위를 키웁니다.

---

## 3. 복구

### 3.1 시작 전 — 순서대로

1. **애플리케이션 트래픽을 먼저 끊습니다.** 복구 중인 DB 에 쓰기가 들어가면 복구본과
   실서비스 상태가 뒤섞여 무엇이 진실인지 알 수 없게 됩니다.
2. **현재 상태를 먼저 백업합니다.** 망가진 DB 라도 뜹니다. 복구가 더 나쁜 결과를
   낳았을 때 돌아올 지점이 필요합니다.
   ```bash
   infra/backup/backup.sh --database veo --out /var/backups/veo/pre-restore-$(date -u +%Y%m%dT%H%M%SZ) --allow-unmigrated
   ```
3. **복구 시작 시각과 담당자를 기록합니다.** 사고 기록의 시작점입니다.

### 3.2 복구본 만들기

**운영 DB 이름으로 바로 복구하지 마세요.** 새 이름으로 복구하고, 검증하고, 이름을
바꿔 전환합니다. 스크립트는 원본과 같은 이름으로의 복구를 기본적으로 거부합니다.

```bash
export PGPASSWORD='<보관소에서 조회>'

infra/backup/restore.sh \
  --backup "/var/backups/veo/${TS}" \
  --database veo_restore --create \
  --host "$PGHOST" --port 5432 --user veo \
  --answer-store /var/lib/veo/answers-restored \
  --jobs 4

unset PGPASSWORD
```

스크립트가 순서대로 하는 일:

1. 백업 세트를 읽고 **DB 를 건드리기 전에** 체크섬을 검증합니다. 안 맞으면 거기서 중단.
2. 위험한 표적을 거부합니다 (§3.4).
3. `pg_restore --exit-on-error` 로 복구합니다. (기본값은 오류를 로그만 찍고 계속하는
   것인데, 그게 테이블을 건너뛰고도 성공을 보고하는 경로입니다.)
4. **복구본을 다시 재서 백업 세트와 비교합니다** — alembic head, public 테이블 수,
   테이블별 정확한 행 수, 답변 파일 수. 하나라도 어긋나면 종료코드 2.

### 3.3 실제 실행 출력 (2026-07-28 검증)

```
==> Reading backup set .../bk1
  taken from     : veo_backup_smoke
  taken at       : 2026-07-28T07:48:42Z
  alembic head   : deadbeef1234
  public tables  : 2

==> Verifying the dump's checksum
  ok: bc3bf5fa6788f87a04aeecb8c196a664c58760c7ef068c9f8bacc225a3d619a0

==> Verifying the answer archive's checksum
  ok (1 files)

==> Creating 'veo_backup_smoke_restore'

==> Restoring into 'veo_backup_smoke_restore'
  pg_restore finished in 1s

==> Verifying the restored database
  alembic head   : deadbeef1234  (matches)
  public tables  : 2  (matches)
  row counts     : all 2 tables match

==> Restoring the answer store into .../answers-restored
  answer files   : 1  (matches)

==> Restore verified
```

**행 수가 안 맞을 때 실제로 나오는 출력** (일부러 어긋나게 만들어 확인):

```
VERIFY FAIL: row counts differ between the backup and the restored database.

  recorded at backup time:
    {"t": 9, "alembic_version": 1}
  measured after restore:
    {"t": 7, "alembic_version": 1}

ERROR: 1 verification check(s) failed. 'veo_partial_target' holds a restore that does not
match the backup it came from. Do not switch traffic to it.
```

이때 `pg_restore` 자체는 성공했습니다. 종료코드만 봤으면 통과했을 상황입니다.

### 3.4 스크립트가 거부하는 것 (전부 실제로 확인)

| 거부 | 실제 메시지 | 우회 |
|---|---|---|
| 체크섬 불일치 | `checksum mismatch for …/postgres.dump` | 없음. 다른 백업을 쓰고 백업 파이프라인을 사고로 처리 |
| 원본과 같은 DB 이름 | `this backup was taken from 'veo' and you are restoring into the same name.` | `--allow-same-name` (앱이 멈춰 있는지 확인하고) |
| 표적에 이미 테이블이 있음 | `'veo_restore' already contains 41 tables.` | `--drop-existing` |
| 표적 DB 가 없음 | `'veo_restore' does not exist. Pass --create` | `--create` |
| 답변 디렉터리가 비어 있지 않음 | `… is not empty.` | 빈 디렉터리를 지정 |
| 복구 후 내용 불일치 | `N verification check(s) failed` | **없음. 전환하지 마세요.** |

### 3.5 사람이 직접 하는 추가 확인 — 전환 전에

스크립트가 재는 건 구조와 개수입니다. 사람이 봐야 하는 건 **최신성** 과 **격리** 입니다.

```bash
psql -d veo_restore -c "SELECT max(created_at) FROM scan_runs"
```

이 값이 이번 사고의 **실제 RPO** 입니다. 목표(15분)와 비교해 기록하세요.

```bash
psql -d veo_restore -c "SELECT count(*) FROM projects WHERE organization_id IS NULL"
```

**반드시 0.** 0 이 아니면 전환하지 말고 즉시 에스컬레이션 (§8). 복구 과정에서 제약이
빠지면 조직 간 데이터가 섞이는, 복구 실패보다 훨씬 나쁜 사고가 됩니다.

리포트 수치가 재현되는지 (자동 테스트가 검증하는 것과 같은 성질):

```bash
psql -d veo_restore -c "SELECT report_id, version_number, content->'seo'->>'score' FROM report_versions ORDER BY created_at DESC LIMIT 5"
```

고객이 받아 간 리포트의 숫자가 복구 후에도 같아야 합니다. 다르면 전환하지 마세요.

### 3.6 전환

검증을 전부 통과한 뒤에만.

```bash
psql -h "$PGHOST" -U veo -d postgres <<'SQL'
ALTER DATABASE veo RENAME TO veo_broken_20260728;
ALTER DATABASE veo_restore RENAME TO veo;
SQL
```

이름을 바꾸는 방식이라 되돌리기가 쉽고, 망가진 원본이 조사용으로 남습니다.
**`DROP DATABASE` 를 쓰지 마세요.** 원인 분석 자료가 사라집니다.

답변 저장소도 같이 전환합니다. DB 만 바꾸면 복구된 행이 옛 답변을 가리킵니다.

```bash
mv /var/lib/veo/answers /var/lib/veo/answers-broken-20260728
mv /var/lib/veo/answers-restored /var/lib/veo/answers
```

이후 애플리케이션을 올리고 `GET /api/health` 와 주요 화면을 확인합니다.
**그리고 §5 를 읽으세요 — 자격증명 금고는 아직 확인 안 된 상태입니다.**

---

## 4. 답변 저장소 (객체 스토리지)

오늘은 파일시스템 구현입니다 (`veo/observations/answer_store.py`).
S3/MinIO 로 바뀌어도 `backup.sh --answer-store` 대신 버킷 복제를 쓰는 것뿐,
"DB 와 짝을 맞춰 복구해야 한다" 는 성질은 같습니다.

저장소는 읽을 때마다 기록된 SHA-256 과 비교합니다. 수집 이후 내용이 바뀐 답변은
반환되지 않고 `AnswerTamperedError` 로 거부됩니다. 복구본에서 이 예외가 나온다면
**복구가 파일을 손상시킨 것** 이므로 다른 백업 세트를 쓰세요.

버킷을 쓰는 환경이라면 버저닝을 켭니다 — 실수로 지웠을 때 되살릴 유일한 수단입니다.
(아래 명령은 이 머신에서 **검증되지 않았습니다.**)

```bash
aws s3api put-bucket-versioning --bucket veo-artifacts \
  --versioning-configuration Status=Enabled
```

---

## 5. 자격증명 금고 — 마스터키가 없으면 복구되지 않습니다. 그게 맞습니다.

**여기가 새벽 3시에 사람이 가장 많이 헤매는 지점입니다.**

`provider_credentials` 테이블의 비밀값은 AES-256-GCM 으로 암호화되어 있고,
키는 `VEO_CREDENTIAL_ENCRYPTION_KEY` 에서만 옵니다. 데이터베이스 안에도, 백업 안에도
키는 없습니다.

따라서:

- 백업을 복구하면 **암호문은 돌아옵니다.** 행은 그대로 있습니다.
- 그 호스트에 **같은 마스터키가 없으면 아무것도 복호화되지 않습니다.**
- **키를 잃어버리면 저장된 제공자 자격증명은 영구히 사라집니다.** 복구할 방법은
  없습니다. 고객에게 다시 받아 다시 입력하는 것뿐입니다.

이건 결함이 아니라 설계입니다. 백업 파일이 통째로 유출돼도 자격증명은 같이 새지
않는다는 뜻이고, 그 대가가 이것입니다.

`apps/api/tests/operations/test_backup_restore.py` 가 양쪽을 다 검증합니다:
같은 키로는 복호화되고, 다른 키로는 암호 계층에서 `DecryptionError` 가 납니다.

### 5.1 증상이 헷갈리는 이유

금고는 "키가 틀렸다" 와 "그런 자격증명이 없다" 를 **일부러 구분하지 않습니다**
(`vault.resolve_for_use`). 그래서 마스터키가 없는 호스트에서 복구하면 콘솔에는
**"자격증명 미설정"** 처럼 보입니다. 키 문제라고 알려 주지 않습니다.

복구 직후 "왜 갑자기 전부 미설정이지?" 가 보이면 **먼저 키를 의심하세요.**

### 5.2 확인 절차

```bash
# 1) 암호문 행 자체는 돌아왔는가
psql -d veo_restore -c "SELECT organization_id, provider, field, key_version, length(ciphertext) FROM provider_credentials ORDER BY provider"
```

행이 있는데 콘솔이 미설정으로 보인다 → 키 문제입니다.
행 자체가 없다 → 백업 시점에 정말 없었던 것입니다.

```bash
# 2) 이 호스트의 키 버전이 행의 key_version 과 맞는가
psql -d veo_restore -c "SELECT DISTINCT key_version FROM provider_credentials"
# 이 값이 VEO_CREDENTIAL_KEY_VERSION 과 같아야 하고,
# 그 버전의 키가 VEO_CREDENTIAL_ENCRYPTION_KEY 또는
# VEO_CREDENTIAL_PREVIOUS_ENCRYPTION_KEYS 에 있어야 합니다.
```

키 자체는 **절대 화면에 찍지 마세요.** 값을 비교할 일이 있으면 지문으로 비교합니다.

### 5.3 키를 잃어버렸을 때

1. 복구는 계속 진행합니다. 나머지 데이터는 멀쩡합니다.
2. `provider_credentials` 를 비활성화하고 고객별로 재입력을 요청합니다.
3. 재입력 절차는 `runbook-provider-credentials.md`.
4. 사후: 마스터키가 DB 백업과 **다른 곳** 에, 그리고 최소 두 곳에 있는지 확인합니다.
   백업과 키가 같은 금고에 있으면 그 금고를 잃는 순간 둘 다 잃습니다.

---

## 6. 자주 막히는 지점

| 증상 | 원인 | 조치 |
|---|---|---|
| `checksum mismatch` | 전송 중 손상 또는 백업 자체 손상 | 다시 내려받고, 또 실패하면 이전 백업으로. 백업 파이프라인을 사고로 다룬다 |
| `pg_restore` role 오류 | 대상에 역할이 없음 | 스크립트는 `--no-owner --no-privileges` 를 씁니다. 직접 `pg_restore` 를 돌렸다면 그 플래그를 넣으세요 |
| `alembic head is '' but the backup was taken at '…'` | 스키마가 복구되지 않음 | `--data-only` 로 뜬 덤프이거나 덤프가 손상됐습니다. 다른 백업 세트로 |
| `row counts differ` | 복구가 절반만 들어감 | 전환 금지. 다른 백업 세트로. §8 에스컬레이션 |
| 복구는 됐는데 앱이 못 붙음 | `VEO_DATABASE_URL` 이 옛 DB 를 가리킴 | 전환 후 설정과 재시작 여부 확인 |
| 복구 후 한글 깨짐 | 템플릿 인코딩 불일치 | 스크립트는 `TEMPLATE template0` + `ENCODING 'UTF8'` 로 만듭니다. 수동 생성했다면 다시 만드세요 |
| 자격증명이 전부 "미설정" | 마스터키 없음/불일치 | §5 |
| 언급은 있는데 근거 답변이 없음 | 답변 저장소를 같이 복구하지 않음 | `--answer-store` 로 다시 복구하고 §3.6 처럼 함께 전환 |
| `shred: command not found` | macOS 에는 `shred` 가 없음 | `rm -P`. 리눅스 서버에서만 `shred` |

---

## 7. 복구 훈련 (분기 1회, 필수)

백업이 살아 있는지 확인하는 유일한 방법은 실제로 복구해 보는 것입니다.

1. 운영과 격리된 환경에 최신 백업으로 §3.2 를 수행합니다.
2. §3.5 의 사람 확인까지 전부 실행합니다.
3. **소요 시간을 측정해 기록합니다.** 이게 실제 RTO 입니다.
4. 목표(1시간)와 벌어졌으면 절차를 고치거나 목표를 현실화합니다.
5. §0 표에서 "검증 안 됨" 인 줄을 하나씩 줄여 나갑니다.
6. 훈련이 끝나면 복구본을 **완전히 폐기합니다.** 고객 데이터 사본이 훈련 환경에
   남는 것 자체가 위험입니다.

기록할 것: 훈련 날짜, 사용한 백업 세트, 소요 시간, 실패한 단계, 조치.

CI 에서 회귀를 잡는 방법 (실제로 통과하는 명령):

```bash
VEO_TEST_DATABASE_URL="postgresql+psycopg://localhost:5432/veo_test" \
  .venv/bin/python -m pytest apps/api/tests/operations
```

이 스위트는 `veo_test` 를 **건드리지 않습니다.** 자기 전용 데이터베이스
(`veo_test_ops_backup_src`, `veo_test_ops_backup_dst`)를 만들고 끝나면 지웁니다.

---

## 8. 에스컬레이션

- 복구본 검증에서 **테넌트 격리 위반**(`organization_id IS NULL` 이 0 이 아님)이
  나오면: 전환하지 말고 즉시 보고. 조직 간 데이터 유출은 복구 실패보다 훨씬 심각합니다.
  `runbook-incident-response.md` §4.
- **행 수 불일치**로 `restore.sh` 가 실패하면: 다른 백업 세트로 다시 시도하고,
  두 번 연속 실패하면 백업 파이프라인 자체를 장애로 처리합니다.
- 백업 무결성 검사가 **연속 2회** 실패하면: 같음.
- 데이터 손실이 RPO 를 넘으면: 영향 범위(조직·기간)를 특정해 고지 여부를 판단합니다.
- **마스터키 분실**: 보안 담당자에게 즉시 보고. 고객 대상 재입력 요청이 필요합니다.
