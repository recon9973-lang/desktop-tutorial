"""Errors raised by the scoring subsystem."""

from __future__ import annotations


class ScoringSpecError(ValueError):
    """A scoring specification, or a set of outcomes offered against it, is invalid.

    Subclasses :class:`ValueError` so that callers that only care about "bad input"
    can catch either.
    """


class SpecNotFoundError(ScoringSpecError):
    """No published specification matches the requested id and version."""
