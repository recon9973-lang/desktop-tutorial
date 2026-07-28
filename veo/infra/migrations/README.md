# 마이그레이션은 여기에 없습니다

VEO 의 Alembic 마이그레이션은 애플리케이션 패키지와 같은 트리에 있습니다.

```
apps/api/alembic.ini            # Alembic 설정
apps/api/alembic/env.py         # 실행 환경 (VEO_DATABASE_URL 을 읽음)
apps/api/alembic/versions/      # 리비전 파일
```

## 왜 infra/ 가 아니라 apps/api/ 인가

마이그레이션은 `veo.db.models` 의 메타데이터를 임포트해야 하고,
`apps/api/tests/db/test_migrations.py` 가 `apps/api/alembic.ini` 경로를 하드코딩해
드리프트 검사(모델과 마이그레이션이 어긋났는지)를 돌립니다.
설정 파일을 둘로 나누면 두 개의 alembic 트리가 서로 다른 head 를 갖게 되고,
그 순간 드리프트 검사는 의미를 잃습니다. 그래서 한 곳으로 통일했습니다.

## 실행 방법

Makefile 을 쓰는 것이 정석입니다(경로와 환경변수를 알아서 맞춰 줍니다).

```bash
make migrate          # alembic upgrade head
make migrate-down     # alembic downgrade -1
make migrate-revision m="add competitor snapshot table"
```

직접 실행할 때는 반드시 `apps/api` 에서 실행하고 `VEO_DATABASE_URL` 을 줍니다.
`alembic.ini` 의 `script_location` 과 `prepend_sys_path` 가 상대경로이기 때문입니다.

```bash
cd apps/api
VEO_DATABASE_URL='postgresql+psycopg://user@localhost:5432/veo' \
  ../../.venv/bin/alembic upgrade head
```

이 디렉터리는 앞으로 DB 운영 보조 스크립트(백업 검증용 SQL 등)를 두는 자리로
남겨 둡니다. 관련 절차는 `docs/operations/runbook-backup-restore.md` 를 보세요.
