"""Router plumbing shared by organizations, customers, projects and sites.

Three things live here.

**Permission guard.** :func:`guard` delegates to :func:`veo.authz.require` — the
permission matrix is still the single source of truth — and translates the resulting
:class:`~veo.authz.errors.PermissionDeniedError` into a 403 carrying the standard
:class:`~veo.contracts.envelope.ApiError`. Without the translation an authorization
failure would leave the router as an unhandled exception and surface as a 500, which is
both wrong and, on a write endpoint, easy to mistake for a bug in the write itself. See
``INTEGRATION_REQUEST.md``: once the integrator registers an application-wide handler for
``AuthorizationError`` this wrapper becomes a thin pass-through.

**Error shapes.** :func:`not_found` and :func:`conflict` build the same envelope every
time. The 404 message is deliberately generic per resource: a row belonging to another
organization and a row that does not exist anywhere must produce byte-identical
responses, or the 404 becomes an existence oracle.

**Pagination.** One ``page`` / ``page_size`` pair, bounded at 200, for every list route.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Query, status

from veo.api.deps import build_meta
from veo.authz import Permission, Principal, require
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiError, PagedResponse, PageInfo

#: Matches ``PageInfo.page_size``. A larger page is a denial-of-service lever, not a feature.
MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 20


def api_error(status_code: int, code: ErrorCode, message_ko: str) -> HTTPException:
    """An ``HTTPException`` whose detail is already a serialised :class:`ApiError`.

    ``veo.api.app`` recognises that shape and passes it through untouched, so the body a
    caller sees is the same envelope a success would have used.
    """
    return HTTPException(
        status_code=status_code,
        detail=ApiError.of(code, message_ko).model_dump(mode="json"),
    )


def not_found(message_ko: str) -> HTTPException:
    return api_error(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, message_ko)


def conflict(message_ko: str) -> HTTPException:
    return api_error(status.HTTP_409_CONFLICT, ErrorCode.CONFLICT, message_ko)


def guard(*permissions: Permission) -> Callable[[Principal], Principal]:
    """Demand every listed permission, answering 403 when the caller lacks one.

    Declared as a route dependency rather than called inside the handler, so the check
    runs before the body is read and before any row is looked up. That ordering is what
    keeps a read-only caller from telling a missing row apart from a forbidden one.
    """
    # `veo.api.app` registers an application-wide handler that turns
    # PermissionDeniedError into the standard 403 envelope, so this no longer catches
    # and re-raises. Translating it a second time here would give the codebase two
    # definitions of what a 403 looks like, and they would drift.
    return require(*permissions)


@dataclass(frozen=True, slots=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination_params(
    page: Annotated[int, Query(ge=1, description="1부터 시작하는 페이지 번호입니다.")] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_PAGE_SIZE,
            description=f"한 페이지에 담을 항목 수입니다. 최대 {MAX_PAGE_SIZE}개입니다.",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


PageParams = Annotated[Pagination, Depends(pagination_params)]


def paged[T](
    items: list[T], request_id: str, *, pagination: Pagination, total_items: int
) -> PagedResponse[T]:
    return PagedResponse[T](
        data=items,
        error=None,
        page_info=PageInfo.build(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total_items,
        ),
        meta=build_meta(request_id),
    )


def changed_fields(instance: Any, changes: dict[str, Any]) -> list[str]:
    """Names whose new value differs from what is already stored, sorted.

    Values are never returned — the audit trail records that a field moved, not what it
    moved to, so a contact note or a customer name never reaches the log.
    """
    return sorted(name for name, value in changes.items() if getattr(instance, name) != value)
