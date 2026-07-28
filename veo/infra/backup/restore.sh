#!/usr/bin/env bash
#
# VEO restore — and, in the same run, proof that the restore actually worked.
#
# The exit code of pg_restore is not evidence. pg_restore exits 0 after restoring into a
# database that ends up missing half its rows, and it exits 0 after restoring a dump that
# never contained the schema in the first place. So this script does not stop at the
# restore: it re-measures the restored database and compares it against what the backup
# recorded at the moment it was taken.
#
#   * alembic head must equal the head recorded in the backup set
#   * every public table's exact row count must equal what was recorded
#   * the public table count must match
#   * when answers are included, the extracted file count must match
#
# Any mismatch is a failure with a non-zero exit, not a warning.
#
# Refusals, by design:
#   * --database takes a bare name (see backup.sh for why), and after connecting,
#     current_database() must equal it.
#   * Restoring into the same database name the backup came from needs --allow-same-name.
#     The single most expensive mistake available here is restoring last night's dump
#     over a live database while trying to build a scratch copy.
#   * A target that already contains tables is refused unless --drop-existing. A restore
#     into a populated database merges two states and produces something that is neither.
#
# The password comes from PGPASSWORD or ~/.pgpass and is never read, echoed, or written
# into any output by this script.
#
# Usage:
#   infra/backup/restore.sh --backup /var/backups/veo/20260728T0000Z \
#       --database veo_restore --create \
#       [--host HOST] [--port PORT] [--user USER] [--jobs N] \
#       [--answer-store /var/lib/veo/answers-restored] [--drop-existing] [--allow-same-name]

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/backup/lib.sh
. "$HERE/lib.sh"

BACKUP_DIR=""
DATABASE=""
ANSWER_STORE=""
CREATE=0
DROP_EXISTING=0
ALLOW_SAME_NAME=0
JOBS=4

usage() {
    sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed -e 's/^# \{0,1\}//' -e '/^set -euo/d'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --backup)         BACKUP_DIR="${2:-}"; shift 2 ;;
        --backup=*)       BACKUP_DIR="${1#*=}"; shift ;;
        --database)       DATABASE="${2:-}"; shift 2 ;;
        --database=*)     DATABASE="${1#*=}"; shift ;;
        --host)           PG_HOST="${2:-}"; shift 2 ;;
        --host=*)         PG_HOST="${1#*=}"; shift ;;
        --port)           PG_PORT="${2:-}"; shift 2 ;;
        --port=*)         PG_PORT="${1#*=}"; shift ;;
        --user)           PG_USER="${2:-}"; shift 2 ;;
        --user=*)         PG_USER="${1#*=}"; shift ;;
        --jobs)           JOBS="${2:-}"; shift 2 ;;
        --jobs=*)         JOBS="${1#*=}"; shift ;;
        --answer-store)   ANSWER_STORE="${2:-}"; shift 2 ;;
        --answer-store=*) ANSWER_STORE="${1#*=}"; shift ;;
        --create)         CREATE=1; shift ;;
        --drop-existing)  DROP_EXISTING=1; shift ;;
        --allow-same-name) ALLOW_SAME_NAME=1; shift ;;
        -h|--help)        usage; exit 0 ;;
        *)                die "unknown argument: $1 (try --help)" ;;
    esac
done

assert_plain_database_name "$DATABASE"
[ -n "$BACKUP_DIR" ] || die "--backup is required"
[ -d "$BACKUP_DIR" ] || die "backup directory not found: $BACKUP_DIR"

case "$JOBS" in
    ''|*[!0-9]*) die "--jobs must be a positive integer" ;;
esac
[ "$JOBS" -ge 1 ] || die "--jobs must be at least 1"

command -v pg_restore >/dev/null 2>&1 || die "pg_restore is not on PATH"
command -v psql       >/dev/null 2>&1 || die "psql is not on PATH"

# --------------------------------------------------------------------------- #
# 1. Read the backup set and check it is intact before touching any database
# --------------------------------------------------------------------------- #

step "Reading backup set $BACKUP_DIR"

SOURCE_DATABASE="$(meta_read "$BACKUP_DIR" database)"
EXPECTED_HEAD="$(meta_read_optional "$BACKUP_DIR" alembic_head "")"
EXPECTED_TABLES="$(meta_read "$BACKUP_DIR" table_count)"
EXPECTED_DUMP_SHA="$(meta_read "$BACKUP_DIR" dump_sha256)"
ANSWERS_INCLUDED="$(meta_read_optional "$BACKUP_DIR" answers_included false)"
EXPECTED_ANSWER_FILES="$(meta_read_optional "$BACKUP_DIR" answers_files 0)"
CREATED_AT="$(meta_read_optional "$BACKUP_DIR" created_at unknown)"

[ -f "$BACKUP_DIR/row-counts.json" ] \
    || die "backup set has no row-counts.json; it cannot be verified and will not be restored"

log "  taken from     : $SOURCE_DATABASE"
log "  taken at       : $CREATED_AT"
log "  alembic head   : ${EXPECTED_HEAD:-<none>}"
log "  public tables  : $EXPECTED_TABLES"

step "Verifying the dump's checksum"
verify_sha256 "$BACKUP_DIR/postgres.dump" "$EXPECTED_DUMP_SHA"
log "  ok: $EXPECTED_DUMP_SHA"

if [ "$ANSWERS_INCLUDED" = "true" ]; then
    step "Verifying the answer archive's checksum"
    verify_sha256 "$BACKUP_DIR/answers.tar.gz" "$(meta_read "$BACKUP_DIR" answers_sha256)"
    log "  ok ($EXPECTED_ANSWER_FILES files)"
fi

# --------------------------------------------------------------------------- #
# 2. Refuse the dangerous targets
# --------------------------------------------------------------------------- #

if [ "$DATABASE" = "$SOURCE_DATABASE" ] && [ "$ALLOW_SAME_NAME" -eq 0 ]; then
    die "this backup was taken from '$SOURCE_DATABASE' and you are restoring into the same name.
If you meant to overwrite the source, pass --allow-same-name and be certain the
application is stopped. If you meant to build a copy, name a different target — e.g.
--database ${SOURCE_DATABASE}_restore --create."
fi

if database_exists "$DATABASE"; then
    if [ "$DROP_EXISTING" -eq 1 ]; then
        step "Dropping the existing '$DATABASE'"
        psql_exec postgres "DROP DATABASE \"$DATABASE\" WITH (FORCE)"
        CREATE=1
    else
        assert_named_database "$DATABASE"
        existing_tables="$(public_table_count "$DATABASE")"
        if [ "$existing_tables" != "0" ]; then
            die "'$DATABASE' already contains $existing_tables tables.
Restoring on top of them would merge two different states into one database that is
neither. Pass --drop-existing to replace it, or name an empty target."
        fi
    fi
else
    [ "$CREATE" -eq 1 ] || die "'$DATABASE' does not exist. Pass --create to create it."
fi

if [ "$CREATE" -eq 1 ] && ! database_exists "$DATABASE"; then
    step "Creating '$DATABASE'"
    # template0 + explicit UTF8: template1 may carry local objects and a different
    # encoding, which restores as mojibake rather than as an error.
    psql_exec postgres "CREATE DATABASE \"$DATABASE\" ENCODING 'UTF8' TEMPLATE template0"
fi

assert_named_database "$DATABASE"

# --------------------------------------------------------------------------- #
# 3. Restore
# --------------------------------------------------------------------------- #

step "Restoring into '$DATABASE'"
RESTORE_ARGS=()
while IFS= read -r flag; do
    [ -n "$flag" ] && RESTORE_ARGS=(${RESTORE_ARGS[@]+"${RESTORE_ARGS[@]}"} "$flag")
done <<EOF
$(conn_args)
EOF

STARTED_AT="$(date -u +%s)"

# --exit-on-error is deliberate. The default is to log errors and carry on, which is how
# a restore reports success while having skipped tables. Verification below would catch
# it anyway, but failing at the point of damage gives a far more useful error.
pg_restore ${RESTORE_ARGS[@]+"${RESTORE_ARGS[@]}"} \
    --dbname="$DATABASE" \
    --no-owner --no-privileges \
    --jobs="$JOBS" \
    --exit-on-error \
    "$BACKUP_DIR/postgres.dump"

ELAPSED=$(( $(date -u +%s) - STARTED_AT ))
log "  pg_restore finished in ${ELAPSED}s"

# --------------------------------------------------------------------------- #
# 4. Verify by content. This is the part that makes it a restore rather than a hope.
# --------------------------------------------------------------------------- #

FAILURES=0
fail() { printf 'VERIFY FAIL: %s\n' "$*" >&2; FAILURES=$(( FAILURES + 1 )); }

step "Verifying the restored database"

ACTUAL_HEAD="$(alembic_head "$DATABASE")"
if [ "$ACTUAL_HEAD" = "$EXPECTED_HEAD" ]; then
    log "  alembic head   : ${ACTUAL_HEAD:-<none>}  (matches)"
else
    fail "alembic head is '${ACTUAL_HEAD:-<none>}' but the backup was taken at '${EXPECTED_HEAD:-<none>}'.
       The application expects the schema the code was built against. Do not point the
       application at this database."
fi

ACTUAL_TABLES="$(public_table_count "$DATABASE")"
if [ "$ACTUAL_TABLES" = "$EXPECTED_TABLES" ]; then
    log "  public tables  : $ACTUAL_TABLES  (matches)"
else
    fail "restored database has $ACTUAL_TABLES public tables, the backup recorded $EXPECTED_TABLES."
fi

ACTUAL_COUNTS_FILE="$(mktemp -t veo-restore-counts)"
trap 'rm -f "$ACTUAL_COUNTS_FILE"' EXIT
psql_scalar "$DATABASE" "$ROW_COUNTS_SQL" > "$ACTUAL_COUNTS_FILE"

if diff -q "$BACKUP_DIR/row-counts.json" "$ACTUAL_COUNTS_FILE" >/dev/null 2>&1; then
    log "  row counts     : all $ACTUAL_TABLES tables match"
else
    fail "row counts differ between the backup and the restored database."
    log ""
    log "  recorded at backup time:"
    log "    $(cat "$BACKUP_DIR/row-counts.json")"
    log "  measured after restore:"
    log "    $(cat "$ACTUAL_COUNTS_FILE")"
    log ""
fi

# --------------------------------------------------------------------------- #
# 5. Answers
# --------------------------------------------------------------------------- #

if [ -n "$ANSWER_STORE" ]; then
    if [ "$ANSWERS_INCLUDED" != "true" ]; then
        die "--answer-store was given but this backup set contains no answer archive.
Restoring the database without the answers leaves every recorded mention pointing at
evidence that is not there. Find a backup set taken with --answer-store."
    fi
    step "Restoring the answer store into $ANSWER_STORE"
    if [ -d "$ANSWER_STORE" ] && [ -n "$(ls -A "$ANSWER_STORE" 2>/dev/null)" ]; then
        die "$ANSWER_STORE is not empty. Extracting over it would mix restored evidence
with whatever is already there. Point --answer-store at an empty or new directory."
    fi
    mkdir -p "$ANSWER_STORE"
    chmod 700 "$ANSWER_STORE"
    tar -xzf "$BACKUP_DIR/answers.tar.gz" -C "$ANSWER_STORE"
    actual_files="$(find "$ANSWER_STORE" -type f | wc -l | tr -d ' ')"
    if [ "$actual_files" = "$EXPECTED_ANSWER_FILES" ]; then
        log "  answer files   : $actual_files  (matches)"
    else
        fail "extracted $actual_files answer files, the backup recorded $EXPECTED_ANSWER_FILES."
    fi
elif [ "$ANSWERS_INCLUDED" = "true" ]; then
    log "  answer store   : archive present but not restored (--answer-store not given)"
fi

# --------------------------------------------------------------------------- #
# 6. Verdict
# --------------------------------------------------------------------------- #

if [ "$FAILURES" -ne 0 ]; then
    printf '\n' >&2
    die "$FAILURES verification check(s) failed. '$DATABASE' holds a restore that does not
match the backup it came from. Do not switch traffic to it. Try another backup set and
treat this as an incident — see docs/operations/runbook-backup-restore.md §6."
fi

step "Restore verified"
log ""
log "  database  : $DATABASE"
log "  from      : $BACKUP_DIR (taken $CREATED_AT from '$SOURCE_DATABASE')"
log "  restore   : ${ELAPSED}s for pg_restore"
log ""
log "The provider-credential vault is NOT verified by this script and cannot be."
log "Stored credentials decrypt only with VEO_CREDENTIAL_ENCRYPTION_KEY. If this host"
log "does not have the same master key the rows were written under, the ciphertext is"
log "restored but unreadable — by design. Confirm the key before declaring recovery"
log "complete. See docs/operations/runbook-backup-restore.md §5."
