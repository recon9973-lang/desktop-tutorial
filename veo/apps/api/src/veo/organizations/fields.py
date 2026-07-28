"""Pydantic field types and validator helpers shared by the resource schemas.

Everything here exists so that four request models cannot drift into four different
opinions about what a slug is, or about whether a PATCH body may set a non-nullable
column to ``null``.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints

#: Requests reject unknown keys. A typo in a field name is a silent no-op otherwise, and
#: a client that thinks it disabled something that is still enabled is worse than an error.
STRICT = ConfigDict(extra="forbid")

#: Lowercase words joined by single hyphens. No leading, trailing or doubled hyphen, so a
#: slug is safe in a URL path and reads the same everywhere it is quoted.
SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"

#: A conservative BCP 47 shape: ``ko``, ``ko-KR``, ``zh-Hant-TW``. The column is 16 chars.
LOCALE_PATTERN = r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"

DisplayName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
ShortLabel = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
FreeNote = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
Slug = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=80, pattern=SLUG_PATTERN),
]
Locale = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=16, pattern=LOCALE_PATTERN),
]
SpecVersion = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
]

JsonSettings = dict[str, Any]


def forbid_nulls(data: Any, *names: str) -> Any:
    """Reject an explicit ``null`` for a column that is ``NOT NULL``.

    Used from a ``mode="before"`` model validator, because that is the only place a
    Pydantic model can still tell "absent" from "present and null" on the raw input.
    """
    if isinstance(data, dict):
        offenders = sorted(name for name in names if name in data and data[name] is None)
        if offenders:
            raise ValueError(f"다음 항목은 값을 비울 수 없습니다: {', '.join(offenders)}")
    return data


def require_any_field(model: BaseModel) -> None:
    """Reject an empty PATCH body.

    An update that changes nothing would still write an audit row claiming somebody
    changed something, which makes the trail lie.
    """
    if not model.model_fields_set:
        raise ValueError("변경할 항목을 하나 이상 지정해야 합니다.")
