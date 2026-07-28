#!/usr/bin/env bash
#
# VEO backup — PostgreSQL plus the raw-answer object store.
#
# What this produces is a *backup set*: a directory that carries not only the data but
# the facts a restore needs in order to prove it worked. A dump on its own cannot be
# verified; a dump next to the alembic head it was taken at and the exact row count of
# every table can be.
#
#   <out-dir>/
#     manifest.json          human- and tool-readable summary of everything below
#     postgres.dump          pg_dump --format=custom  (selective restore stays possible)
#     postgres.dump.sha256   bare hex digest
#     row-counts.json        exact count(*) per public table, as canonical jsonb text
#     meta/…                 one value per file, for restore.sh to read without a parser
#     answers.tar.gz         the filesystem answer store, when --answer-store is given
#     answers.tar.gz.sha256
#
# Refusals, by design:
#   * --database takes a bare name. A URI or conninfo is refused: it can carry a
#     password and it can point somewhere other than the name you typed.
#   * After connecting, current_database() must equal the name you typed.
#   * A database with no alembic_version table is refused unless --allow-unmigrated.
#     Backing up the wrong (empty) database and calling it a VEO backup is a failure
#     that only surfaces during a restore.
#
# The password comes from PGPASSWORD or ~/.pgpass and is never read, echoed, or written
# into any output file by this script.
#
# Usage:
#   infra/backup/backup.sh --database veo --out /var/backups/veo/20260728T0000Z \
#       [--host HOST] [--port PORT] [--user USER] \
#       [--answer-store /var/lib/veo/answers] [--allow-unmigrated]

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/backup/lib.sh
. "$HERE/lib.sh"

DATABASE=""
OUT_DIR=""
ANSWER_STORE=""
ALLOW_UNMIGRATED=0

usage() {
    sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed -e 's/^# \{0,1\}//' -e '/^set -euo/d'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --database)     DATABASE="${2:-}"; shift 2 ;;
        --database=*)   DATABASE="${1#*=}"; shift ;;
        --out)          OUT_DIR="${2:-}"; shift 2 ;;
        --out=*)        OUT_DIR="${1#*=}"; shift ;;
        --host)         PG_HOST="${2:-}"; shift 2 ;;
        --host=*)       PG_HOST="${1#*=}"; shift ;;
        --port)         PG_PORT="${2:-}"; shift 2 ;;
        --port=*)       PG_PORT="${1#*=}"; shift ;;
        --user)         PG_USER="${2:-}"; shift 2 ;;
        --user=*)       PG_USER="${1#*=}"; shift ;;
        --answer-store) ANSWER_STORE="${2:-}"; shift 2 ;;
        --answer-store=*) ANSWER_STORE="${1#*=}"; shift ;;
        --allow-unmigrated) ALLOW_UNMIGRATED=1; shift ;;
        -h|--help)      usage; exit 0 ;;
        *)              die "unknown argument: $1 (try --help)" ;;
    esac
done

assert_plain_database_name "$DATABASE"
[ -n "$OUT_DIR" ] || die "--out is required"

command -v pg_dump >/dev/null 2>&1 || die "pg_dump is not on PATH"
command -v psql    >/dev/null 2>&1 || die "psql is not on PATH"

# --------------------------------------------------------------------------- #
# 1. Confirm we are talking to the database the operator named
# --------------------------------------------------------------------------- #

step "Checking the connection lands on '$DATABASE'"
assert_named_database "$DATABASE"

SERVER_VERSION="$(psql_scalar "$DATABASE" 'SHOW server_version')"
ALEMBIC_HEAD="$(alembic_head "$DATABASE")"
TABLE_COUNT="$(public_table_count "$DATABASE")"

if [ -z "$ALEMBIC_HEAD" ] && [ "$ALLOW_UNMIGRATED" -eq 0 ]; then
    die "'$DATABASE' has no alembic_version row, so it is not a migrated VEO database.
Backing this up would produce a backup set that cannot be verified on restore.
If that is genuinely what you want, pass --allow-unmigrated."
fi

log "  server_version : $SERVER_VERSION"
log "  alembic head   : ${ALEMBIC_HEAD:-<none>}"
log "  public tables  : $TABLE_COUNT"

# --------------------------------------------------------------------------- #
# 2. Record what the data looks like right now
# --------------------------------------------------------------------------- #

mkdir -p "$OUT_DIR"
# The dump is customer data in the clear. Nobody but the operator reads this directory.
chmod 700 "$OUT_DIR"

CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

step "Recording row counts for all $TABLE_COUNT public tables"
psql_scalar "$DATABASE" "$ROW_COUNTS_SQL" > "$OUT_DIR/row-counts.json"
[ -s "$OUT_DIR/row-counts.json" ] || die "row-count query returned nothing; refusing to write a backup set that cannot be verified"

# --------------------------------------------------------------------------- #
# 3. Dump
# --------------------------------------------------------------------------- #

step "Dumping '$DATABASE'"
DUMP_ARGS=()
while IFS= read -r flag; do
    [ -n "$flag" ] && DUMP_ARGS=(${DUMP_ARGS[@]+"${DUMP_ARGS[@]}"} "$flag")
done <<EOF
$(conn_args)
EOF

# --format=custom keeps selective restore (pg_restore --table) possible; plain SQL does
# not. --no-owner/--no-privileges let the set restore onto a host whose roles differ,
# which is the normal case in a disaster.
pg_dump ${DUMP_ARGS[@]+"${DUMP_ARGS[@]}"} \
    --dbname="$DATABASE" \
    --format=custom --compress=9 \
    --no-owner --no-privileges \
    --file="$OUT_DIR/postgres.dump"

chmod 600 "$OUT_DIR/postgres.dump"
DUMP_SHA="$(sha256_of "$OUT_DIR/postgres.dump")"
printf '%s\n' "$DUMP_SHA" > "$OUT_DIR/postgres.dump.sha256"
DUMP_BYTES="$(wc -c < "$OUT_DIR/postgres.dump" | tr -d ' ')"
log "  postgres.dump  : $DUMP_BYTES bytes"
log "  sha256         : $DUMP_SHA"

# --------------------------------------------------------------------------- #
# 4. Object storage — the raw AI answers
# --------------------------------------------------------------------------- #
#
# veo/observations/answer_store.py is a filesystem store today. Every mention VEO
# reports points at an answer here; a database restored without them leaves rows
# asserting a measurement with nothing left to check it against.

ANSWERS_INCLUDED="false"
ANSWERS_SHA=""
ANSWERS_FILES="0"

if [ -n "$ANSWER_STORE" ]; then
    [ -d "$ANSWER_STORE" ] || die "--answer-store is not a directory: $ANSWER_STORE"
    step "Archiving the answer store at $ANSWER_STORE"
    ANSWERS_FILES="$(find "$ANSWER_STORE" -type f | wc -l | tr -d ' ')"
    tar -czf "$OUT_DIR/answers.tar.gz" -C "$ANSWER_STORE" .
    chmod 600 "$OUT_DIR/answers.tar.gz"
    ANSWERS_SHA="$(sha256_of "$OUT_DIR/answers.tar.gz")"
    printf '%s\n' "$ANSWERS_SHA" > "$OUT_DIR/answers.tar.gz.sha256"
    ANSWERS_INCLUDED="true"
    log "  answer files   : $ANSWERS_FILES"
    log "  sha256         : $ANSWERS_SHA"
else
    log "  answer store   : not included (--answer-store was not given)"
fi

# --------------------------------------------------------------------------- #
# 5. Metadata
# --------------------------------------------------------------------------- #

meta_write "$OUT_DIR" database          "$DATABASE"
meta_write "$OUT_DIR" created_at        "$CREATED_AT"
meta_write "$OUT_DIR" alembic_head      "$ALEMBIC_HEAD"
meta_write "$OUT_DIR" postgres_version  "$SERVER_VERSION"
meta_write "$OUT_DIR" table_count       "$TABLE_COUNT"
meta_write "$OUT_DIR" dump_sha256       "$DUMP_SHA"
meta_write "$OUT_DIR" answers_included  "$ANSWERS_INCLUDED"
meta_write "$OUT_DIR" answers_sha256    "$ANSWERS_SHA"
meta_write "$OUT_DIR" answers_files     "$ANSWERS_FILES"

{
    printf '{\n'
    printf '  "veo_backup_format": 1,\n'
    printf '  "created_at": "%s",\n'        "$(json_escape "$CREATED_AT")"
    printf '  "database": "%s",\n'          "$(json_escape "$DATABASE")"
    printf '  "host": "%s",\n'              "$(json_escape "${PG_HOST:-<default>}")"
    printf '  "port": "%s",\n'              "$(json_escape "${PG_PORT:-5432}")"
    printf '  "postgres_version": "%s",\n'  "$(json_escape "$SERVER_VERSION")"
    printf '  "alembic_head": "%s",\n'      "$(json_escape "$ALEMBIC_HEAD")"
    printf '  "table_count": %s,\n'         "$TABLE_COUNT"
    printf '  "dump_sha256": "%s",\n'       "$(json_escape "$DUMP_SHA")"
    printf '  "dump_bytes": %s,\n'          "$DUMP_BYTES"
    printf '  "answers": {"included": %s, "sha256": "%s", "file_count": %s},\n' \
        "$ANSWERS_INCLUDED" "$(json_escape "$ANSWERS_SHA")" "$ANSWERS_FILES"
    printf '  "row_counts": %s\n'           "$(cat "$OUT_DIR/row-counts.json")"
    printf '}\n'
} > "$OUT_DIR/manifest.json"

step "Backup set written to $OUT_DIR"
log ""
log "This is not yet a backup. Verify it by restoring it:"
log "  infra/backup/restore.sh --backup $OUT_DIR --database ${DATABASE}_restore --create"
log ""
log "The dump contains every customer's data in the clear. Do not leave it on a laptop;"
log "move it to encrypted storage and remove the local copy when you are done."
