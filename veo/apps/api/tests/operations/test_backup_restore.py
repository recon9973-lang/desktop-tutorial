"""A real backup and restore round trip against a live PostgreSQL.

A backup that has never been restored is not a backup, and a restore that is checked by
its exit code is not checked. This module therefore does the whole thing: migrate a
throwaway database to head, write rows whose values are known in advance, run
``infra/backup/backup.sh``, destroy the source, run ``infra/backup/restore.sh`` into a
second throwaway database, and then assert against the *content* — the report numbers
come back, the alembic head matches, the stored credential is still there.

Three failure modes get their own tests because they are the ones that actually happen:

* a restore that "succeeded" into a schema that is not the one the code expects,
* a backup file that changed between being written and being restored,
* a restore aimed at the database it was taken from.

Neither of the databases used here is ``veo_test``. Both are created and dropped by this
module; other suites run against the shared one and would lose their tables.

Marked ``requires_postgres``. Skipped without ``VEO_TEST_DATABASE_URL`` — a skip here is a
gap in coverage, not a pass, and CI must set the variable.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from veo.authz import Principal
from veo.contracts.enums import Role
from veo.credentials.cipher import (
    DecryptionError,
    MasterKey,
    build_associated_data,
    select_cipher_backend,
)
from veo.credentials.providers import CredentialField, CredentialProvider
from veo.credentials.vault import CredentialNotFoundError, CredentialVault
from veo.db.models import (
    Organization,
    Project,
    ProviderCredential,
    Report,
    ReportVersion,
    User,
)
from veo.observations.answer_store import AnswerTamperedError, FilesystemAnswerStore
from veo.observations.providers.base import CitationSupport, CostBasis
from veo.observations.providers.storage import AnswerRecordKey, RecordedAnswer

REPO_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(__file__).resolve().parents[2]
BACKUP_SH = REPO_ROOT / "infra" / "backup" / "backup.sh"
RESTORE_SH = REPO_ROOT / "infra" / "backup" / "restore.sh"

SHARED_DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

#: Obviously synthetic key material, matching the credential suite's convention.
MASTER_KEY_B64 = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
OTHER_MASTER_KEY_B64 = "ICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj8="

#: A secret that could not be mistaken for a real credential in a log or a dump.
CREDENTIAL_SECRET = "test-secret-not-a-real-key"

#: The numbers a past report asserted. After a restore these must come back byte for
#: byte, because "the score was 72.5" is the claim a customer paid for.
REPORT_CONTENT = {
    "seo": {"score": 72.5, "band": "NEEDS_WORK"},
    "geo": {"score": 41.0, "band": "AT_RISK"},
    "mentions": 17,
}
REPORT_DISCLOSURES = ["측정 기간 2026-07-01 ~ 2026-07-28", "표본 40개 프롬프트"]

#: The one piece of evidence written to the object store, and looked for after restore.
ANSWER_KEY = AnswerRecordKey(
    prompt_id="ondam-location",
    conditions_fingerprint="ko-KR-seoul-2026-07",
    attempt=1,
)


def _derive(suffix: str) -> str | None:
    if not SHARED_DATABASE_URL:
        return None
    url = make_url(SHARED_DATABASE_URL)
    return str(url.set(database=f"{url.database}{suffix}"))


SOURCE_URL = _derive("_ops_backup_src")
TARGET_URL = _derive("_ops_backup_dst")

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not SHARED_DATABASE_URL,
        reason="set VEO_TEST_DATABASE_URL to run the backup/restore round trip",
    ),
]


# --------------------------------------------------------------------------- #
# Throwaway databases
# --------------------------------------------------------------------------- #


def _url(raw: str) -> URL:
    return make_url(raw)


def _admin_engine(raw: str) -> Engine:
    return create_engine(str(_url(raw).set(database="postgres")), isolation_level="AUTOCOMMIT")


def _recreate(raw: str) -> None:
    admin = _admin_engine(raw)
    name = _url(raw).database
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            connection.execute(
                text(f"CREATE DATABASE \"{name}\" ENCODING 'UTF8' TEMPLATE template0")
            )
    finally:
        admin.dispose()


def _drop(raw: str) -> None:
    admin = _admin_engine(raw)
    name = _url(raw).database
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        admin.dispose()


@pytest.fixture(scope="module")
def source_database() -> Iterator[str]:
    """A migrated database this module owns outright and destroys when it is done."""
    assert SOURCE_URL is not None
    _recreate(SOURCE_URL)
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    previous = os.environ.get("VEO_DATABASE_URL")
    os.environ["VEO_DATABASE_URL"] = SOURCE_URL
    try:
        command.upgrade(config, "head")
        yield SOURCE_URL
    finally:
        if previous is None:
            os.environ.pop("VEO_DATABASE_URL", None)
        else:
            os.environ["VEO_DATABASE_URL"] = previous
        _drop(SOURCE_URL)


@pytest.fixture(scope="module")
def target_database() -> Iterator[str]:
    """The restore target. Created by restore.sh itself, dropped here."""
    assert TARGET_URL is not None
    _drop(TARGET_URL)
    try:
        yield TARGET_URL
    finally:
        _drop(TARGET_URL)


# --------------------------------------------------------------------------- #
# Known content
# --------------------------------------------------------------------------- #


class Seeded:
    """The identifiers and values written before the backup, checked after the restore."""

    def __init__(self) -> None:
        self.organization_id = uuid.uuid4()
        self.slug = f"ops-backup-{uuid.uuid4().hex[:8]}"
        self.user_id = uuid.uuid4()
        self.project_id = uuid.uuid4()
        self.report_id = uuid.uuid4()
        self.report_version_id = uuid.uuid4()
        self.answer_ref = ""
        self.answer_sha = ""


def _seed(database_url: str, answers_root: Path) -> Seeded:
    seeded = Seeded()
    engine = create_engine(database_url, future=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    session = factory()
    try:
        organization = Organization(
            id=seeded.organization_id, slug=seeded.slug, name="백업 훈련 조직",
            is_active=True, settings={},
        )
        session.add(organization)
        # provider_credentials.created_by references users; the vault records who stored
        # the secret, so the row has to exist before the vault is used.
        session.add(
            User(
                id=seeded.user_id,
                email=f"ops-backup-{uuid.uuid4().hex[:10]}@veo.invalid",
                display_name="백업 훈련 담당자",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            Project(
                id=seeded.project_id,
                organization_id=seeded.organization_id,
                slug="clinic",
                name="온담의원",
                locale="ko-KR",
                settings={},
            )
        )
        session.add(
            Report(
                id=seeded.report_id,
                organization_id=seeded.organization_id,
                project_id=seeded.project_id,
                title="2026년 7월 진단 리포트",
                audience="BUSINESS",
            )
        )
        session.add(
            ReportVersion(
                id=seeded.report_version_id,
                organization_id=seeded.organization_id,
                report_id=seeded.report_id,
                version_number=1,
                included_run_ids=[],
                scoring_versions={"seo": "1.2.0", "geo": "0.9.1"},
                content=REPORT_CONTENT,
                disclosures_ko=REPORT_DISCLOSURES,
                export_formats=["pdf"],
            )
        )
        session.commit()

        # A credential, so the restore can be asked what happens to the vault.
        vault = CredentialVault(
            session, master_key=MasterKey.from_base64(MASTER_KEY_B64, version=1)
        )
        principal = Principal(
            user_id=seeded.user_id,
            organization_id=seeded.organization_id,
            roles=frozenset({Role.SUPER_ADMIN}),
            session_id=uuid.uuid4().hex,
        )
        vault.store(
            principal=principal,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
            secret=SecretStr(CREDENTIAL_SECRET),
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    # The evidence behind the report's numbers, in the object store.
    store = FilesystemAnswerStore(
        root=answers_root, organization_id=str(seeded.organization_id)
    )
    stored = store.put(
        ANSWER_KEY,
        RecordedAnswer(
            engine="openai",
            model="gpt-test",
            model_version="test-1",
            text="온담의원은 서울 강남구에 있습니다.",
            citations=("https://example.invalid/ondam",),
            citation_support=CitationSupport.STRUCTURED,
            latency_ms=1234,
            cost_usd=0.0021,
            cost_basis=CostBasis.CALCULATED_FROM_USAGE,
            input_tokens=120,
            output_tokens=48,
            executed_at=datetime(2026, 7, 20, 3, 0, tzinfo=UTC),
        ),
    )
    seeded.answer_ref = stored.ref
    seeded.answer_sha = stored.sha256
    return seeded


# --------------------------------------------------------------------------- #
# Driving the scripts
# --------------------------------------------------------------------------- #


def _pg_flags(database_url: str) -> list[str]:
    url = _url(database_url)
    flags = ["--database", str(url.database)]
    if url.host:
        flags += ["--host", url.host]
    if url.port:
        flags += ["--port", str(url.port)]
    if url.username:
        flags += ["--user", url.username]
    return flags


#: Resolved once. The scripts are bash, and ruff (S607) is right that a bare "bash"
#: would be resolved through PATH at call time.
BASH = shutil.which("bash") or "/bin/bash"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [BASH, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )


def _backup(
    database_url: str, out_dir: Path, answers_root: Path
) -> subprocess.CompletedProcess[str]:
    return _run(
        BACKUP_SH,
        *_pg_flags(database_url),
        "--out", str(out_dir),
        "--answer-store", str(answers_root),
    )


def _restore(
    database_url: str, backup_dir: Path, *extra: str
) -> subprocess.CompletedProcess[str]:
    return _run(RESTORE_SH, "--backup", str(backup_dir), *_pg_flags(database_url), *extra)


@pytest.fixture(scope="module")
def round_trip(
    source_database: str, target_database: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[dict[str, object]]:
    """Seed, back up, destroy the source, restore. Every test below reads the result."""
    workspace = tmp_path_factory.mktemp("backup-round-trip")
    answers_root = workspace / "answers"
    answers_root.mkdir()
    backup_dir = workspace / "set"
    restored_answers = workspace / "answers-restored"

    seeded = _seed(source_database, answers_root)

    backup = _backup(source_database, backup_dir, answers_root)
    assert backup.returncode == 0, backup.stderr

    # Destroy the source before restoring. Without this the restore could be reading
    # rows that never left the original database, and the test would pass on a backup
    # that contains nothing at all.
    _drop(source_database)
    shutil.rmtree(answers_root)

    restore = _restore(
        target_database,
        backup_dir,
        "--create",
        "--answer-store", str(restored_answers),
    )
    assert restore.returncode == 0, restore.stderr

    yield {
        "seeded": seeded,
        "backup_dir": backup_dir,
        "workspace": workspace,
        "restored_answers": restored_answers,
        "backup_stderr": backup.stderr,
        "restore_stderr": restore.stderr,
    }


@pytest.fixture
def restored_session(target_database: str) -> Iterator[Session]:
    engine = create_engine(target_database, future=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# The round trip
# --------------------------------------------------------------------------- #


def test_backup_set_records_what_a_restore_needs_to_verify(
    round_trip: dict[str, object],
) -> None:
    """The manifest carries the head and the per-table counts, not just a file."""
    backup_dir = round_trip["backup_dir"]
    assert isinstance(backup_dir, Path)
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["veo_backup_format"] == 1
    assert manifest["alembic_head"], "backup recorded no alembic head"
    assert manifest["dump_bytes"] > 0
    assert manifest["answers"]["included"] is True
    assert manifest["answers"]["file_count"] == 1

    counts = manifest["row_counts"]
    assert counts["organizations"] == 1
    assert counts["projects"] == 1
    assert counts["report_versions"] == 1
    assert counts["provider_credentials"] == 1


def test_alembic_head_survives_the_restore(
    round_trip: dict[str, object], restored_session: Session
) -> None:
    """A restore into a half-applied schema is the failure that matters most."""
    backup_dir = round_trip["backup_dir"]
    assert isinstance(backup_dir, Path)
    recorded = (backup_dir / "meta" / "alembic_head").read_text(encoding="utf-8").strip()

    restored = (
        restored_session.execute(text("SELECT version_num FROM alembic_version"))
        .scalars()
        .all()
    )
    assert sorted(restored) == sorted(recorded.split(",")), (
        "the restored database is not at the migration the backup was taken at"
    )


def test_the_report_numbers_come_back(
    round_trip: dict[str, object], restored_session: Session
) -> None:
    """The claim a customer paid for reproduces from the restored database."""
    seeded = round_trip["seeded"]
    assert isinstance(seeded, Seeded)

    version = restored_session.execute(
        select(ReportVersion).where(ReportVersion.id == seeded.report_version_id)
    ).scalar_one()

    assert version.content == REPORT_CONTENT
    assert version.content["seo"]["score"] == 72.5
    assert version.content["mentions"] == 17
    assert version.disclosures_ko == REPORT_DISCLOSURES
    assert version.scoring_versions == {"seo": "1.2.0", "geo": "0.9.1"}
    assert version.organization_id == seeded.organization_id


def test_tenant_scoping_survives_the_restore(
    round_trip: dict[str, object], restored_session: Session
) -> None:
    """Every restored row still belongs to an organization.

    A restore that drops a NOT NULL or a foreign key produces rows with no tenant, which
    is how one customer's data ends up in another's report. This is the check the runbook
    tells an operator to run before switching traffic.
    """
    seeded = round_trip["seeded"]
    assert isinstance(seeded, Seeded)

    organization = restored_session.execute(
        select(Organization).where(Organization.id == seeded.organization_id)
    ).scalar_one()
    assert organization.slug == seeded.slug

    orphans = restored_session.execute(
        text(
            """
            SELECT count(*) FROM projects       WHERE organization_id IS NULL
            """
        )
    ).scalar_one()
    assert orphans == 0

    project = restored_session.execute(
        select(Project).where(Project.id == seeded.project_id)
    ).scalar_one()
    assert project.organization_id == seeded.organization_id


def test_report_versions_are_still_append_only_after_a_restore(
    round_trip: dict[str, object], restored_session: Session
) -> None:
    """Triggers are schema objects; a dump that loses them loses the guarantee silently.

    ``report_versions`` refuses UPDATE at the database level. If a restore brought back
    the rows but not the trigger, nothing would fail until someone edited a delivered
    report — so it is checked here rather than trusted.
    """
    seeded = round_trip["seeded"]
    assert isinstance(seeded, Seeded)

    with pytest.raises(Exception, match="append-only"):
        restored_session.execute(
            text("UPDATE report_versions SET version_number = 99 WHERE id = :id"),
            {"id": seeded.report_version_id},
        )
    restored_session.rollback()


def test_answers_come_back_intact(round_trip: dict[str, object]) -> None:
    """The evidence behind the numbers is restored, and still passes its own hash check."""
    seeded = round_trip["seeded"]
    restored_answers = round_trip["restored_answers"]
    assert isinstance(seeded, Seeded)
    assert isinstance(restored_answers, Path)

    store = FilesystemAnswerStore(
        root=restored_answers, organization_id=str(seeded.organization_id)
    )
    found = store.find(ANSWER_KEY)
    assert found is not None, "the restored answer store has no answer at the recorded key"
    assert found.sha256 == seeded.answer_sha

    # read() re-hashes and refuses tampered evidence, so getting a value back at all is
    # the integrity assertion.
    answer = store.read(found.ref)
    assert answer.text == "온담의원은 서울 강남구에 있습니다."
    assert answer.citations == ("https://example.invalid/ondam",)
    assert answer.input_tokens == 120


def test_a_tampered_answer_is_refused_rather_than_returned(
    round_trip: dict[str, object],
) -> None:
    """Restoring evidence is not the same as restoring *trustworthy* evidence."""
    seeded = round_trip["seeded"]
    restored_answers = round_trip["restored_answers"]
    assert isinstance(seeded, Seeded)
    assert isinstance(restored_answers, Path)

    store = FilesystemAnswerStore(
        root=restored_answers, organization_id=str(seeded.organization_id)
    )
    found = store.find(ANSWER_KEY)
    assert found is not None
    path = Path(found.ref.removeprefix("file://"))
    original = path.read_text(encoding="utf-8")
    payload = json.loads(original)
    payload["text"] = "온담의원은 부산 해운대구에 있습니다."
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    try:
        with pytest.raises(AnswerTamperedError):
            store.read(found.ref)
    finally:
        path.write_text(original, encoding="utf-8")


# --------------------------------------------------------------------------- #
# The credential vault does not survive without its master key
# --------------------------------------------------------------------------- #


def test_credential_ciphertext_is_restored(
    round_trip: dict[str, object], restored_session: Session
) -> None:
    seeded = round_trip["seeded"]
    assert isinstance(seeded, Seeded)

    row = restored_session.execute(
        select(ProviderCredential).where(
            ProviderCredential.organization_id == seeded.organization_id
        )
    ).scalar_one()
    assert row.provider == CredentialProvider.OPENAI.value
    assert row.field == CredentialField.API_KEY.value
    assert row.algorithm == "AES-256-GCM"
    assert bytes(row.ciphertext), "the credential row restored with no ciphertext"
    assert CREDENTIAL_SECRET.encode() not in bytes(row.ciphertext)


def test_credential_is_readable_with_the_same_master_key(
    round_trip: dict[str, object], restored_session: Session
) -> None:
    """The other half of the claim: with the key, the restored vault works."""
    seeded = round_trip["seeded"]
    assert isinstance(seeded, Seeded)

    vault = CredentialVault(
        restored_session, master_key=MasterKey.from_base64(MASTER_KEY_B64, version=1)
    )
    recovered = vault.resolve_for_use(
        organization_id=seeded.organization_id,
        provider=CredentialProvider.OPENAI,
        field=CredentialField.API_KEY,
    )
    assert recovered.get_secret_value() == CREDENTIAL_SECRET


def test_credential_is_unreadable_without_the_master_key(
    round_trip: dict[str, object], restored_session: Session
) -> None:
    """Losing VEO_CREDENTIAL_ENCRYPTION_KEY loses the credentials. That is correct.

    A restore onto a host that does not hold the master key the rows were written under
    brings back the ciphertext and nothing else. If this test ever fails, the vault is
    not really encrypting and a stolen dump is a stolen credential set.

    Both layers are asserted, because they say different things:

    * the cipher genuinely refuses — the ciphertext is cryptographically bound to a key
      this host does not have, not merely hidden behind a lookup;
    * the vault surfaces that as ``CredentialNotFoundError``, indistinguishable from
      "there is no such row". That collapse is deliberate (see ``vault.resolve_for_use``)
      and it is why an operator staring at a fresh restore sees "not configured" rather
      than "wrong key" — the runbook has to tell them which one it really is.
    """
    seeded = round_trip["seeded"]
    assert isinstance(seeded, Seeded)

    row = restored_session.execute(
        select(ProviderCredential).where(
            ProviderCredential.organization_id == seeded.organization_id
        )
    ).scalar_one()

    wrong = MasterKey.from_base64(OTHER_MASTER_KEY_B64, version=1)
    backend = select_cipher_backend()
    with pytest.raises(DecryptionError):
        backend.decrypt(
            key=wrong.aes_key,
            nonce=bytes(row.nonce),
            ciphertext=bytes(row.ciphertext),
            associated_data=build_associated_data(
                seeded.organization_id,
                CredentialProvider.OPENAI.value,
                CredentialField.API_KEY.value,
                row.key_version,
            ),
        )

    wrong_vault = CredentialVault(restored_session, master_key=wrong)
    with pytest.raises(CredentialNotFoundError):
        wrong_vault.resolve_for_use(
            organization_id=seeded.organization_id,
            provider=CredentialProvider.OPENAI,
            field=CredentialField.API_KEY,
        )


def test_restore_says_out_loud_that_it_cannot_verify_the_vault(
    round_trip: dict[str, object],
) -> None:
    """An operator who reads only the last screen of output must still learn this."""
    stderr = round_trip["restore_stderr"]
    assert isinstance(stderr, str)
    assert "VEO_CREDENTIAL_ENCRYPTION_KEY" in stderr


def test_scripts_do_not_print_secrets(round_trip: dict[str, object]) -> None:
    """Neither script may echo a credential, and neither writes one into the backup set."""
    backup_stderr = round_trip["backup_stderr"]
    restore_stderr = round_trip["restore_stderr"]
    backup_dir = round_trip["backup_dir"]
    assert isinstance(backup_stderr, str)
    assert isinstance(restore_stderr, str)
    assert isinstance(backup_dir, Path)

    assert CREDENTIAL_SECRET not in backup_stderr
    assert CREDENTIAL_SECRET not in restore_stderr
    assert MASTER_KEY_B64 not in backup_stderr
    assert MASTER_KEY_B64 not in restore_stderr

    manifest = (backup_dir / "manifest.json").read_text(encoding="utf-8")
    assert CREDENTIAL_SECRET not in manifest
    assert "password" not in manifest.lower()


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #


def test_restore_refuses_a_backup_whose_dump_changed(
    round_trip: dict[str, object], target_database: str, tmp_path: Path
) -> None:
    """A silently corrupted backup is the dangerous kind. It must not be restored."""
    backup_dir = round_trip["backup_dir"]
    assert isinstance(backup_dir, Path)
    tampered = tmp_path / "tampered"
    shutil.copytree(backup_dir, tampered)
    with (tampered / "postgres.dump").open("ab") as handle:
        handle.write(b"\x00")

    result = _restore(target_database, tampered, "--drop-existing", "--create")
    assert result.returncode != 0
    assert "checksum mismatch" in result.stderr


def test_restore_refuses_a_content_mismatch_even_when_pg_restore_succeeds(
    round_trip: dict[str, object], target_database: str, tmp_path: Path
) -> None:
    """Exit code 0 from pg_restore is not evidence that the data came back.

    The recorded counts are edited to describe a database with more rows than the dump
    holds. pg_restore still succeeds; the run must still fail.
    """
    backup_dir = round_trip["backup_dir"]
    assert isinstance(backup_dir, Path)
    doctored = tmp_path / "doctored"
    shutil.copytree(backup_dir, doctored)

    counts = json.loads((doctored / "row-counts.json").read_text(encoding="utf-8"))
    counts["report_versions"] = counts["report_versions"] + 5
    (doctored / "row-counts.json").write_text(json.dumps(counts), encoding="utf-8")

    result = _restore(target_database, doctored, "--drop-existing", "--create")
    assert result.returncode != 0
    assert "row counts differ" in result.stderr


def test_restore_refuses_to_overwrite_the_database_it_came_from(
    round_trip: dict[str, object],
) -> None:
    """Building a scratch copy must not be one typo away from overwriting production."""
    backup_dir = round_trip["backup_dir"]
    assert SOURCE_URL is not None
    assert isinstance(backup_dir, Path)

    result = _restore(SOURCE_URL, backup_dir)
    assert result.returncode != 0
    assert "--allow-same-name" in result.stderr


def test_backup_refuses_a_connection_string_as_the_database_name(tmp_path: Path) -> None:
    """A URI can carry a password and can point somewhere other than the name typed."""
    result = _run(
        BACKUP_SH,
        "--database", "postgresql://veo:not-a-real-password@db.invalid/veo",
        "--out", str(tmp_path / "never-written"),
    )
    assert result.returncode != 0
    assert "bare database name" in result.stderr
    assert "not-a-real-password" not in result.stdout
    assert not (tmp_path / "never-written").exists()


def test_backup_refuses_a_database_that_is_not_a_migrated_veo_database(
    tmp_path: Path,
) -> None:
    """Backing up the wrong, empty database is only discovered during a restore."""
    assert TARGET_URL is not None
    scratch = str(make_url(TARGET_URL).set(database="veo_ops_backup_not_veo"))
    _recreate(scratch)
    try:
        result = _backup(scratch, tmp_path / "out", tmp_path)
        assert result.returncode != 0
        assert "alembic_version" in result.stderr
    finally:
        _drop(scratch)
