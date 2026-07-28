"""Failures the service layer reports, with no HTTP in them.

A service says *what* went wrong; the router decides which status code says it. Keeping
the two apart is what lets the same service be called from a worker or a management
command without dragging FastAPI along.

Every message is Korean and safe to show a caller: it names the kind of thing that was
missing, never the id that was probed for and never the row that does exist somewhere
else. ``ReferenceNotFoundError`` in particular is raised when a foreign key points at
another organization's row, and it must read exactly like the row simply not existing.
"""

from __future__ import annotations


class ResourceError(Exception):
    """Base class. ``message_ko`` is safe to return to the caller verbatim."""

    def __init__(self, message_ko: str) -> None:
        self.message_ko = message_ko
        super().__init__(message_ko)


class ReferenceNotFoundError(ResourceError):
    """A referenced row is absent from the caller's organization.

    Raised both for an id that exists nowhere and for one that belongs to another tenant.
    The two cases are deliberately indistinguishable — a distinct error for the second
    would turn a rejected write into a working existence oracle.
    """


class DuplicateResourceError(ResourceError):
    """A uniqueness constraint would be violated (project slug, site origin)."""


class UndeletableResourceError(ResourceError):
    """The row has no soft-delete column and immutable history depends on it.

    Projects and sites carry no ``is_active``, and scans, evidence, score results and
    reports all cascade off them. Deleting the parent would erase run history that a
    published report still cites, so the endpoint refuses instead.
    """
