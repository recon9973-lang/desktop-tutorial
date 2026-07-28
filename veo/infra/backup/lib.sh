#!/usr/bin/env bash
# Shared helpers for backup.sh and restore.sh.
#
# Sourced, never executed. Two properties every function here preserves:
#
#   * No credential is ever printed. Nothing echoes the environment, nothing echoes a
#     connection string, and no argument is allowed to *be* a connection string —
#     `--database` takes a bare name, which is also what makes the "is this really the
#     database the operator named?" check meaningful rather than tautological.
#   * Every failure is loud and non-zero. A backup or restore that half-worked and
#     exited 0 is the failure mode these scripts exist to prevent.
#
# Written for bash 3.2 (the macOS system bash): no associative arrays, no mapfile.

# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

log()  { printf '%s\n' "$*" >&2; }
step() { printf '\n==> %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 2; }

# --------------------------------------------------------------------------- #
# Checksums
# --------------------------------------------------------------------------- #

# sha256_of FILE -> lowercase hex digest on stdout.
# Tool availability differs per platform; every branch prints the digest alone.
sha256_of() {
    local file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$file" | awk '{print $1}'
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 "$file" | awk '{print $NF}'
    else
        die "no sha256 tool found (sha256sum, shasum or openssl required)"
    fi
}

# verify_sha256 FILE EXPECTED -> 0 when equal, dies otherwise.
verify_sha256() {
    local file="$1" expected="$2" actual
    [ -f "$file" ] || die "missing file: $file"
    actual="$(sha256_of "$file")"
    if [ "$actual" != "$expected" ]; then
        die "checksum mismatch for $file
  expected $expected
  actual   $actual
A backup that does not hash to what was recorded is corrupt. Do not restore it — use
another backup and treat the backup pipeline itself as an incident."
    fi
}

# --------------------------------------------------------------------------- #
# Names
# --------------------------------------------------------------------------- #

#: A database name this tooling accepts: a bare identifier, nothing else.
#: A URI or a key=value conninfo is refused because it can carry a password (which would
#: then end up in the shell history, the process table, and this script's own output)
#: and because it can silently point somewhere other than the name the operator typed.
assert_plain_database_name() {
    local name="$1"
    case "$name" in
        "")            die "--database is required" ;;
        *://*|*=*|*\ *|*$'\t'*)
            die "--database takes a bare database name, not a connection string.
A URI or conninfo can carry a password and can point at a different server than the one
you named. Pass --host/--port/--user separately and put the password in PGPASSWORD." ;;
    esac
    case "$name" in
        [A-Za-z_]*) ;;
        *) die "--database must start with a letter or underscore: $name" ;;
    esac
    if printf '%s' "$name" | LC_ALL=C grep -q '[^A-Za-z0-9_]'; then
        die "--database may contain only letters, digits and underscores: $name"
    fi
    if [ "${#name}" -gt 63 ]; then
        die "--database is longer than PostgreSQL's 63-byte identifier limit: $name"
    fi
}

# --------------------------------------------------------------------------- #
# Connection
# --------------------------------------------------------------------------- #

# Populated by parse_connection_flags; consumed by psql_conn / pg_conn_args.
PG_HOST=""
PG_PORT=""
PG_USER=""

# conn_args -> the shared --host/--port/--username flags, printed one per line so the
# caller can read them into an array without word-splitting surprises.
conn_args() {
    [ -n "$PG_HOST" ] && printf -- '--host=%s\n' "$PG_HOST"
    [ -n "$PG_PORT" ] && printf -- '--port=%s\n' "$PG_PORT"
    [ -n "$PG_USER" ] && printf -- '--username=%s\n' "$PG_USER"
    return 0
}

# psql_scalar DBNAME SQL -> the single value the query produced, trimmed.
# ON_ERROR_STOP makes a failed statement a failed command instead of an empty string
# that the caller would go on to compare against something.
psql_scalar() {
    local dbname="$1" sql="$2"
    local args
    args=()
    while IFS= read -r flag; do
        [ -n "$flag" ] && args=(${args[@]+"${args[@]}"} "$flag")
    done <<EOF
$(conn_args)
EOF
    psql ${args[@]+"${args[@]}"} --dbname="$dbname" \
        --no-psqlrc --quiet --tuples-only --no-align \
        --set=ON_ERROR_STOP=1 --command="$sql"
}

# psql_exec DBNAME SQL -> run a statement for effect.
psql_exec() {
    local dbname="$1" sql="$2"
    local args
    args=()
    while IFS= read -r flag; do
        [ -n "$flag" ] && args=(${args[@]+"${args[@]}"} "$flag")
    done <<EOF
$(conn_args)
EOF
    psql ${args[@]+"${args[@]}"} --dbname="$dbname" \
        --no-psqlrc --quiet --set=ON_ERROR_STOP=1 --command="$sql" >/dev/null
}

# assert_named_database DBNAME
#
# Confirm that the connection we just opened really landed on the database whose name the
# operator typed, and do it before spending twenty minutes on a dump that was never going
# to work.
#
# Honest scope, because an overclaimed safety check is worse than none: an explicit
# --dbname overrides PGDATABASE, and it overrides a `dbname` in a PGSERVICE entry too —
# this was checked against PostgreSQL 16.14 with a service file that named a different
# database, and the connection still landed on the one passed to --dbname. So this
# equality test is close to tautological *for the database name*. What it does buy is
# real: it fails here, cheaply and with a clear message, when the server is unreachable,
# the credentials are wrong, or the database does not exist.
#
# The check that actually catches "you named the wrong thing" is the alembic_version
# guard in backup.sh (this is not a migrated VEO database) and the source-name and
# empty-target guards in restore.sh. Neither of those can be satisfied by accident.
#
# What none of this can catch is a PGSERVICE or PGHOST that points at a *different
# server* holding a database of the same name. Pass --host explicitly in any automated
# job so the target is stated rather than inherited.
assert_named_database() {
    local dbname="$1" actual
    actual="$(psql_scalar "$dbname" 'SELECT current_database()')" \
        || die "cannot connect to database '$dbname' on ${PG_HOST:-<default host>}:${PG_PORT:-5432}"
    if [ "$actual" != "$dbname" ]; then
        die "connected to database '$actual' but you named '$dbname'.
Refusing to continue. Check PGDATABASE, PGSERVICE and ~/.pg_service.conf."
    fi
}

# database_exists DBNAME -> 0/1 via exit status. Asked from the maintenance database.
database_exists() {
    local dbname="$1" found
    found="$(psql_scalar postgres \
        "SELECT 1 FROM pg_database WHERE datname = '$(sql_quote "$dbname")'")"
    [ "$found" = "1" ]
}

# sql_quote VALUE -> the value with single quotes doubled, for embedding in a literal.
sql_quote() { printf '%s' "$1" | sed "s/'/''/g"; }

# --------------------------------------------------------------------------- #
# Content fingerprint — what makes a restore verifiable
# --------------------------------------------------------------------------- #

#: Exact row counts for every ordinary table in the public schema, as a JSON object.
#: query_to_xml is the standard way to run a count against a dynamically named table
#: from plain SQL; it keeps this in one round trip and needs no server-side function.
ROW_COUNTS_SQL="
SELECT coalesce(jsonb_object_agg(t.table_name, t.n)::text, '{}')
FROM (
    SELECT c.relname AS table_name,
           (xpath(
               '/row/c/text()',
               query_to_xml(
                   format('SELECT count(*) AS c FROM public.%I', c.relname),
                   false, true, ''
               )
           ))[1]::text::bigint AS n
    FROM pg_class c
    JOIN pg_namespace ns ON ns.oid = c.relnamespace
    WHERE ns.nspname = 'public' AND c.relkind = 'r'
) t
"

#: Every alembic head the database currently reports, comma-joined and sorted.
#: Empty string means the table is absent or empty — an unmigrated database.
ALEMBIC_HEAD_SQL="
SELECT coalesce(
    (SELECT string_agg(version_num, ',' ORDER BY version_num) FROM alembic_version),
    ''
)
"

# alembic_head DBNAME -> the head, or the empty string when there is no alembic_version.
alembic_head() {
    local dbname="$1" has_table
    has_table="$(psql_scalar "$dbname" "SELECT to_regclass('public.alembic_version') IS NOT NULL")"
    if [ "$has_table" != "t" ]; then
        printf ''
        return 0
    fi
    psql_scalar "$dbname" "$ALEMBIC_HEAD_SQL"
}

# public_table_count DBNAME -> how many ordinary tables the public schema holds.
public_table_count() {
    psql_scalar "$1" "
        SELECT count(*)
        FROM pg_class c JOIN pg_namespace ns ON ns.oid = c.relnamespace
        WHERE ns.nspname = 'public' AND c.relkind = 'r'
    "
}

# --------------------------------------------------------------------------- #
# JSON
# --------------------------------------------------------------------------- #

# json_escape VALUE -> the value with backslashes and double quotes escaped.
# The values written here are identifiers, hostnames, hex digests, integers and ISO
# timestamps; this covers every character any of them can contain.
json_escape() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

# --------------------------------------------------------------------------- #
# Backup metadata
# --------------------------------------------------------------------------- #
#
# manifest.json is written for people and for tooling that has a JSON parser. restore.sh
# does not parse it: every value restore.sh needs also lands in <backup>/meta/<key> as a
# single line of plain text. Shell-parsing JSON is how a restore ends up comparing an
# empty string to an empty string and declaring success.

# meta_write DIR KEY VALUE
meta_write() {
    local dir="$1" key="$2" value="$3"
    mkdir -p "$dir/meta"
    printf '%s\n' "$value" > "$dir/meta/$key"
}

# meta_read DIR KEY -> the stored value. Dies when the key is absent, because a missing
# metadata file means the backup set is incomplete and must not be treated as usable.
meta_read() {
    local dir="$1" key="$2"
    [ -f "$dir/meta/$key" ] \
        || die "backup set is missing meta/$key — it is incomplete and will not be restored: $dir"
    head -n 1 "$dir/meta/$key"
}

# meta_read_optional DIR KEY [DEFAULT]
meta_read_optional() {
    local dir="$1" key="$2" fallback="${3:-}"
    if [ -f "$dir/meta/$key" ]; then head -n 1 "$dir/meta/$key"; else printf '%s' "$fallback"; fi
}
