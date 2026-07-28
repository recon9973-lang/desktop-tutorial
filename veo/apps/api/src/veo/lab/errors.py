"""Failures the VEO-LAB workflow reports, with no HTTP in them.

Every message is Korean and safe to show a caller. They name specification ids, versions
and fixture names — all of which are VEO-LAB's own methodology metadata, not customer
data — because a reviewer who is told only "거부되었습니다" has to go and read the YAML,
which is exactly what this module exists to make unnecessary.
"""

from __future__ import annotations


class LabError(Exception):
    """Base class. ``message_ko`` is safe to return to the caller verbatim."""

    def __init__(self, message_ko: str) -> None:
        self.message_ko = message_ko
        super().__init__(message_ko)


class IllegalTransitionError(LabError):
    """The requested status change is not in the transition table."""


class ImmutableVersionError(LabError):
    """A write was attempted against a row that may no longer change.

    A ``PUBLISHED`` row is not "shouldn't be edited" — it cannot be. Every score VEO has
    ever shown cites a version and a checksum; if the specification behind one of those
    checksums could move, every historical report becomes unfalsifiable.
    """


class ChecksumMismatchError(LabError):
    """A stored specification does not hash to its recorded checksum.

    Refused, never repaired. Recomputing the checksum to make the row consistent again
    would erase the only evidence that something changed underneath a published number.
    """


class GoldenFixtureError(LabError):
    """The golden fixtures were not run, did not pass, or were run against other bytes."""


class SpecificationRejectedError(LabError):
    """A candidate specification failed validation."""

    def __init__(self, message_ko: str, *, reasons_ko: tuple[str, ...] = ()) -> None:
        self.reasons_ko = reasons_ko
        super().__init__(message_ko)


class DuplicateVersionError(LabError):
    """A specification family already carries this semantic version."""


class VersionNotFoundError(LabError):
    """No scoring version with that id."""
