#!/usr/bin/env bash
# 클립보드에 있는 Neon 연결 문자열을 veo/.env 에 넣는다.
#
# 값을 화면에 출력하지 않는다. 연결 문자열에는 비밀번호가 들어 있고, 터미널에 한 번
# 찍히면 스크롤 기록에도 남고 화면 공유에도 딸려 나간다. 확인은 가려진 형태로만 한다.
#
# 사용법:  bash infra/scripts/set-database-url.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/.env"

# 값은 화면에 표시되지 않는 프롬프트로 받는다.
#
# 처음에는 클립보드에서 읽었는데, 이 스크립트를 실행하려면 실행 명령을 복사해야 하고
# 그 순간 클립보드의 연결 문자열이 지워진다. 붙여넣을 것을 요구하면서 붙여넣기 버퍼를
# 쓰는 설계였다. 프롬프트는 그 순서 문제가 없다.
echo "Neon 연결 문자열을 붙여넣고 Enter 를 누르십시오."
echo "입력한 내용은 화면에 표시되지 않습니다. (붙여넣기: ⌘V)"
printf '> '
IFS= read -rs RAW
echo

RAW="$(printf '%s' "$RAW" | tr -d '\n\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

if [ -z "$RAW" ]; then
  echo "아무것도 입력되지 않았습니다." >&2
  exit 1
fi

# 붙여넣기가 화면에 보이지 않으므로, 안 된 줄 알고 한 번 더 붙여넣기 쉽다. 그러면 두
# 값이 한 줄로 이어붙는데, 호스트와 DB 이름을 뽑는 정규식은 뒤쪽 복사본에서도 같은 답을
# 내놓기 때문에 화면 출력은 멀쩡해 보인다. 실제로 걸리는 시점은 서버가 뜨지 않을 때다.
COUNT="$(printf '%s' "$RAW" | grep -oE "postgres(ql)?://" | wc -l | tr -d ' ')"
if [ "$COUNT" -gt 1 ]; then
  echo "연결 문자열이 ${COUNT}개 들어왔습니다. 두 번 붙여넣으신 것 같습니다." >&2
  echo "붙여넣기는 화면에 보이지 않는 것이 정상입니다. 한 번만 붙여넣고 Enter 를 눌러 주십시오." >&2
  exit 1
fi

# psql 예시문을 통째로 복사한 경우가 흔하다. URL 부분만 꺼낸다.
URL="$(printf '%s' "$RAW" | grep -oE "postgres(ql)?://[^'\"[:space:]]+" | head -1 || true)"

if [ -z "$URL" ]; then
  echo "연결 문자열을 찾지 못했습니다." >&2
  echo "postgresql:// 로 시작하는 값을 붙여넣었는지 확인해 주십시오." >&2
  exit 1
fi

# 데이터베이스 이름이 veo 인지 확인한다. flowlens 를 그대로 복사해 오는 것이
# 이 단계에서 가장 흔한 실수이고, 알아채는 시점은 두 제품의 표가 한 곳에 섞인 뒤다.
DB_NAME="$(printf '%s' "$URL" | sed -E 's|.*/([^/?]+)(\?.*)?$|\1|')"
if [ "$DB_NAME" != "veo" ]; then
  echo "이 연결 문자열은 '$DB_NAME' 데이터베이스를 가리킵니다. 'veo' 여야 합니다." >&2
  echo "Neon 의 Connect 창에서 Database 를 veo 로 바꾼 뒤 다시 복사해 주십시오." >&2
  exit 1
fi

# 풀링 주소는 마이그레이션에서 실패한다. 여기서 막지 않으면 나중에
# "테이블이 안 생긴다" 로 나타나고, 원인을 찾기 어렵다.
if printf '%s' "$URL" | grep -q -- "-pooler\."; then
  echo "이 주소는 connection pooling 용입니다(-pooler)." >&2
  echo "Neon 의 Connect 창에서 Connection pooling 을 끈 뒤 다시 복사해 주십시오." >&2
  exit 1
fi

# SQLAlchemy 는 드라이버를 스킴으로 고른다. postgresql:// 만으로는 psycopg 를 쓰지 않는다.
URL="$(printf '%s' "$URL" | sed -E 's|^postgres(ql)?://|postgresql+psycopg://|')"

touch "$ENV_FILE"
chmod 600 "$ENV_FILE"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
chmod 600 "$TMP"

# 기존 줄은 지우고 새로 넣는다. 다른 항목은 그대로 둔다.
grep -v '^VEO_DATABASE_URL=' "$ENV_FILE" > "$TMP" || true
printf 'VEO_DATABASE_URL=%s\n' "$URL" >> "$TMP"
cat "$TMP" > "$ENV_FILE"

HOST="$(printf '%s' "$URL" | sed -E 's|.*@([^/]+)/.*|\1|')"
echo "저장했습니다."
echo "  파일      $ENV_FILE (권한 600)"
echo "  호스트    $HOST"
echo "  데이터베이스  $DB_NAME"
echo "  비밀번호  가려짐 — 화면에 출력하지 않습니다"
echo

# 저장한 것과 연결되는 것은 다른 사실이다. 앞 판에서는 값이 두 번 이어붙어 망가졌는데도
# "저장했습니다" 가 나왔다. 확인 없는 성공 메시지는 없느니만 못하다.
echo "실제로 연결되는지 확인합니다..."
if [ -x "$ROOT/.venv/bin/python" ]; then
  if VEO_CHECK_URL="$URL" "$ROOT/.venv/bin/python" - <<'PY'
import os, sys
try:
    import psycopg
except ModuleNotFoundError:
    print("  건너뜀 — psycopg 가 설치되어 있지 않습니다.")
    sys.exit(0)

url = os.environ["VEO_CHECK_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
try:
    with psycopg.connect(url, connect_timeout=15) as conn, conn.cursor() as cur:
        cur.execute("select current_database(), version()")
        row = cur.fetchone()
        assert row is not None
        print(f"  연결됨 — 데이터베이스 {row[0]}, {row[1].split(',')[0]}")
except Exception as exc:  # noqa: BLE001 - the message is for a person, not a handler
    print(f"  연결하지 못했습니다: {type(exc).__name__}", file=sys.stderr)
    print(f"  {exc}", file=sys.stderr)
    sys.exit(1)
PY
  then
    echo
    echo "다음 단계로 넘어가셔도 됩니다."
  else
    echo >&2
    echo "값은 저장했지만 연결에 실패했습니다. 위 메시지를 그대로 알려 주십시오." >&2
    exit 1
  fi
else
  echo "  건너뜀 — 파이썬 환경을 찾지 못했습니다($ROOT/.venv)."
fi
