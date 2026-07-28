"""Loading, validating and checksumming VEO scoring specifications.

A specification is data, never code. It is validated against
``packages/scoring-specs/schema/scoring-spec.schema.json`` and then frozen with a
SHA-256 checksum so a published version can never drift silently.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from veo.scoring.errors import ScoringSpecError, SpecNotFoundError
from veo.scoring.models import ScoringSpec

_SPECS_DIR_ENV = "VEO_SCORING_SPECS_DIR"
_PACKAGE_RELATIVE = Path("packages") / "scoring-specs"


def find_specs_root() -> Path:
    """Locate ``packages/scoring-specs``.

    Resolution order: ``VEO_SCORING_SPECS_DIR`` env var, then the nearest ancestor of
    this file that contains ``packages/scoring-specs``.
    """
    override = os.environ.get(_SPECS_DIR_ENV)
    if override:
        root = Path(override).expanduser().resolve()
        if not root.is_dir():
            raise SpecNotFoundError(f"{_SPECS_DIR_ENV}={override} is not a directory")
        return root

    for parent in Path(__file__).resolve().parents:
        candidate = parent / _PACKAGE_RELATIVE
        if candidate.is_dir():
            return candidate

    raise SpecNotFoundError(
        "could not locate packages/scoring-specs; set "
        f"{_SPECS_DIR_ENV} to the specification directory"
    )


@functools.lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    schema_path = find_specs_root() / "schema" / "scoring-spec.schema.json"
    if not schema_path.is_file():
        raise SpecNotFoundError(f"scoring spec schema not found at {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def canonical_json(document: Any) -> str:
    """Stable JSON encoding used for checksums, so the same spec always hashes alike."""
    return json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_checksum(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(document).encode("utf-8")).hexdigest()


def build_spec(document: dict[str, Any], *, validate_schema: bool = True) -> ScoringSpec:
    """Validate a raw specification document and freeze it into a :class:`ScoringSpec`."""
    if not isinstance(document, dict):
        raise ScoringSpecError("scoring specification must be a mapping")

    if validate_schema:
        errors = sorted(_schema_validator().iter_errors(document), key=lambda e: list(e.path))
        if errors:
            first = errors[0]
            location = "/".join(str(p) for p in first.path) or "<root>"
            raise ScoringSpecError(
                f"scoring specification failed schema validation at {location}: {first.message}"
            )

    checksum = compute_checksum(document)

    try:
        spec = ScoringSpec.model_validate({**document, "checksum": checksum})
    except ValidationError as exc:  # pragma: no cover - schema catches most of these
        raise ScoringSpecError(f"scoring specification is not well formed: {exc}") from exc

    _validate_internal_consistency(spec)
    return spec


def _validate_internal_consistency(spec: ScoringSpec) -> None:
    seen: set[str] = set()
    for category in spec.categories:
        for check in category.checks:
            if check.id in seen:
                raise ScoringSpecError(
                    f"duplicate check id '{check.id}' — a check may appear in one category only"
                )
            seen.add(check.id)

    category_ids = [c.id for c in spec.categories]
    if len(set(category_ids)) != len(category_ids):
        raise ScoringSpecError("duplicate category id in specification")

    for cap in spec.caps:
        for condition in cap.trigger.any_of:
            if condition.check_id not in seen:
                raise ScoringSpecError(
                    f"cap '{cap.id}' references check '{condition.check_id}' "
                    "which is not defined in this specification"
                )

    for gate in spec.gates:
        for condition in gate.trigger.any_of:
            if condition.check_id not in seen:
                raise ScoringSpecError(
                    f"gate '{gate.id}' references check '{condition.check_id}' "
                    "which is not defined in this specification"
                )

    for band in spec.bands:
        if band.min > band.max:
            raise ScoringSpecError(f"band '{band.id}' has min greater than max")


#: Parsed specifications, keyed by the file's identity *and* its modification stamp.
#: See :func:`load_spec_file` for why the stamp is part of the key.
_SPEC_CACHE: dict[tuple[str, int, int], ScoringSpec] = {}


def clear_spec_cache() -> None:
    """Forget every parsed specification.

    Needed by tests that write a spec, read it, rewrite it and read again inside one
    filesystem timestamp tick — the one case the modification stamp cannot catch.
    """
    _SPEC_CACHE.clear()


def load_spec_file(path: str | Path) -> ScoringSpec:
    """Load a single specification from a YAML or JSON file.

    Parsed specifications are cached, because they are immutable once published and
    re-reading them is expensive: a load is a file read, a YAML parse and a full JSON
    Schema validation. Measured under load, the uncached version made the scoring
    endpoints roughly a hundred times slower than a trivial route — 32 requests per
    second, with the database sitting idle. The work was the same document, parsed again
    for every caller.

    The key includes the file's size and modification time, not just its path. A plain
    path key would be wrong in the way that matters most: publishing a new version of a
    specification, or a test pointing the specs root somewhere else, would keep serving
    the document this process happened to read first. Scores are supposed to be traceable
    to a versioned, checksummed spec, and a stale cache would break exactly that promise
    while still returning a confident number.
    """
    path = Path(path)
    if not path.is_file():
        raise SpecNotFoundError(f"scoring specification not found: {path}")

    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    cached = _SPEC_CACHE.get(key)
    if cached is not None:
        return cached

    raw = path.read_text(encoding="utf-8")
    document = yaml.safe_load(raw) if path.suffix in {".yaml", ".yml"} else json.loads(raw)
    spec = build_spec(document)
    _SPEC_CACHE[key] = spec
    return spec


def load_spec(spec_id: str, version: str) -> ScoringSpec:
    """Load a published specification by id and semantic version."""
    directory = find_specs_root() / "specs" / spec_id
    for suffix in (".yaml", ".yml", ".json"):
        candidate = directory / f"{version}{suffix}"
        if candidate.is_file():
            return load_spec_file(candidate)
    raise SpecNotFoundError(f"no specification {spec_id} at version {version} under {directory}")


def available_specs() -> dict[str, list[str]]:
    """Map every specification id to the versions present on disk, newest last."""
    root = find_specs_root() / "specs"
    if not root.is_dir():
        return {}
    found: dict[str, list[str]] = {}
    for spec_dir in sorted(root.iterdir()):
        if not spec_dir.is_dir():
            continue
        versions = sorted(
            {p.stem for p in spec_dir.iterdir() if p.suffix in {".yaml", ".yml", ".json"}},
            key=_version_key,
        )
        if versions:
            found[spec_dir.name] = versions
    return found


def _version_key(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return (0,)


def latest_published(spec_id: str) -> ScoringSpec:
    """Return the highest-versioned PUBLISHED specification for ``spec_id``."""
    versions = available_specs().get(spec_id)
    if not versions:
        raise SpecNotFoundError(f"no specifications on disk for {spec_id}")
    for version in reversed(versions):
        spec = load_spec(spec_id, version)
        if spec.status == "PUBLISHED":
            return spec
    raise SpecNotFoundError(f"no PUBLISHED specification for {spec_id}")
