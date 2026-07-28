"""Where a Google credential comes from, and the three ways there is not one.

Two sources, in the order VEO prefers them — the same order the Naver resolvers use:

* **The vault** — per-organization credentials an agency stored through
  ``/api/credentials``. The real answer for a multi-tenant product: one deployment serves
  many agencies, each with its own Search Console property.
* **Environment settings** — one deployment-wide credential, for a local developer and for
  a single-tenant install.

Where this module differs from :mod:`veo.providers.naver.credentials` is that it does not
return a bare ``None``. Google has *three* unavailable states, not two, and they need
different things from an operator:

===========================  ==================================================
``ENABLED``                  a credential is present and usable-looking
``DISABLED_NO_CREDENTIAL``   the slot is empty — someone needs to add a key
``DISABLED_INVALID_CREDENTIAL``  the slot holds a placeholder — the *import* is
                             broken, and telling this operator "no credential"
                             sends them to paste a key that is already there
===========================  ==================================================

:class:`CredentialResolution` carries the credential and the state together so a caller
cannot accidentally report one without the other.

What counts as a placeholder is decided in exactly one place — ``core.settings`` — and
imported here rather than restated. A second list would drift, and the day it drifts is
the day ``[SENSITIVE]`` is treated as a key.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Protocol, final

from pydantic import SecretStr

from veo.contracts.enums import ProviderState

# Private on purpose in ``core.settings``, and imported anyway: this is the single
# definition of "a value occupying a credential slot without being a credential", and
# copying it here to avoid touching a private name would create the exact drift the
# constant exists to prevent. INTEGRATION_REQUEST.md §2 asks for a public spelling.
from veo.core.settings import (
    ProviderCredentials,
    _is_placeholder,
    get_provider_credentials,
)
from veo.credentials.providers import CredentialField, CredentialProvider
from veo.providers.google.errors import GoogleCredentialInvalidError

__all__ = [
    "AuthorizedUserCredentials",
    "CredentialResolution",
    "PageSpeedCredentials",
    "SearchConsoleCredentials",
    "SecretResolver",
    "ServiceAccountCredentials",
    "crux_from_settings",
    "crux_from_vault",
    "pagespeed_from_settings",
    "pagespeed_from_vault",
    "parse_search_console_credentials",
    "search_console_from_settings",
    "search_console_from_vault",
]

#: The read-only scope every Search Console call in VEO needs. VEO never writes to a
#: customer's property, so the writable scope is not requested and cannot be misused.
SEARCH_CONSOLE_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"  # noqa: S105 - an endpoint URL


class SecretResolver(Protocol):
    """The vault's outbound seam, and nothing else from it."""

    def resolve_for_use(
        self,
        *,
        organization_id: uuid.UUID,
        provider: CredentialProvider,
        field: CredentialField,
    ) -> SecretStr: ...


# --------------------------------------------------------------------------- #
# Credential shapes
# --------------------------------------------------------------------------- #


@final
@dataclass(frozen=True, slots=True)
class PageSpeedCredentials:
    """A Google API key.

    The same key reaches both PageSpeed Insights and the CrUX API, provided both are
    enabled on the Cloud project. VEO therefore has one slot, not two — see
    :func:`crux_from_settings`.
    """

    api_key: SecretStr


@final
@dataclass(frozen=True, slots=True)
class ServiceAccountCredentials:
    """A Google service account, as issued in a downloaded JSON key file.

    The account must additionally be added as a user on the Search Console property.
    Nothing in an API call can arrange that, and a service account that has not been added
    gets a 403 that looks exactly like a missing scope.
    """

    client_email: str
    private_key: SecretStr
    token_uri: str = DEFAULT_TOKEN_URI


@final
@dataclass(frozen=True, slots=True)
class AuthorizedUserCredentials:
    """A user-consented OAuth client, as written by ``gcloud auth application-default``."""

    client_id: str
    client_secret: SecretStr
    refresh_token: SecretStr
    token_uri: str = DEFAULT_TOKEN_URI


SearchConsoleCredentials = ServiceAccountCredentials | AuthorizedUserCredentials


@final
@dataclass(frozen=True, slots=True)
class CredentialResolution[T]:
    """A credential, or the state that explains why there is not one.

    Validated against itself on construction. A resolution that claims ``ENABLED`` while
    holding nothing — or holds a credential while claiming to be disabled — is a bug that
    would otherwise surface as a provider that reports healthy and answers nothing.
    """

    credentials: T | None
    state: ProviderState

    def __post_init__(self) -> None:
        if self.credentials is None and self.state is ProviderState.ENABLED:
            raise ValueError("a resolution cannot be ENABLED with no credential in it")
        if self.credentials is not None and self.state is not ProviderState.ENABLED:
            raise ValueError(
                f"a resolution holding a credential must be ENABLED, not {self.state}"
            )

    @property
    def is_enabled(self) -> bool:
        return self.state is ProviderState.ENABLED


def _disabled[T](state: ProviderState) -> CredentialResolution[T]:
    return CredentialResolution[T](credentials=None, state=state)


def _state_for(value: SecretStr | str | None) -> ProviderState:
    """The state a single credential value implies, placeholder rules included."""
    if value is None:
        return ProviderState.DISABLED_NO_CREDENTIAL
    raw = value.get_secret_value() if isinstance(value, SecretStr) else value
    if _is_placeholder(value):
        return ProviderState.DISABLED_INVALID_CREDENTIAL
    if not raw.strip():
        return ProviderState.DISABLED_NO_CREDENTIAL
    return ProviderState.ENABLED


# --------------------------------------------------------------------------- #
# PageSpeed / CrUX
# --------------------------------------------------------------------------- #


def pagespeed_from_settings(
    settings: ProviderCredentials | None = None,
) -> CredentialResolution[PageSpeedCredentials]:
    """The deployment-wide PageSpeed key, or the state explaining its absence."""
    resolved = settings if settings is not None else get_provider_credentials()
    return _pagespeed_resolution(resolved.google_pagespeed_api_key)


def crux_from_settings(
    settings: ProviderCredentials | None = None,
) -> CredentialResolution[PageSpeedCredentials]:
    """The CrUX key — which is the PageSpeed key.

    Both APIs authenticate with the same kind of Google API key and VEO stores one slot.
    Inventing a second setting would suggest two credentials exist to configure when only
    one does; what the operator actually has to do is enable the Chrome UX Report API on
    the same Cloud project. ``INTEGRATION_REQUEST.md`` §3 asks for a dedicated slot for the
    deployments that want to separate the quotas.
    """
    return pagespeed_from_settings(settings)


def pagespeed_from_vault(
    resolver: SecretResolver, *, organization_id: uuid.UUID
) -> CredentialResolution[PageSpeedCredentials]:
    """One organization's stored PageSpeed key.

    Every vault failure — nothing stored, deactivated, undecryptable, belonging to another
    organization — is deliberately indistinguishable here, and all of them mean the same
    thing to a caller: the provider is disabled for this organization.
    """
    try:
        api_key = resolver.resolve_for_use(
            organization_id=organization_id,
            provider=CredentialProvider.GOOGLE_PAGESPEED,
            field=CredentialField.API_KEY,
        )
    except Exception:
        return _disabled(ProviderState.DISABLED_NO_CREDENTIAL)
    return _pagespeed_resolution(api_key)


def crux_from_vault(
    resolver: SecretResolver, *, organization_id: uuid.UUID
) -> CredentialResolution[PageSpeedCredentials]:
    return pagespeed_from_vault(resolver, organization_id=organization_id)


def _pagespeed_resolution(
    api_key: SecretStr | None,
) -> CredentialResolution[PageSpeedCredentials]:
    state = _state_for(api_key)
    if state is not ProviderState.ENABLED or api_key is None:
        return _disabled(state)
    return CredentialResolution(credentials=PageSpeedCredentials(api_key=api_key), state=state)


# --------------------------------------------------------------------------- #
# Search Console
# --------------------------------------------------------------------------- #


def parse_search_console_credentials(raw: SecretStr) -> SearchConsoleCredentials:
    """Read a Google credentials JSON document.

    Raises :class:`~veo.providers.google.errors.GoogleCredentialInvalidError` rather than
    filling in what is missing. A service account with no ``private_key`` cannot sign an
    assertion, and a half-built credential produces a 401 that reads like a revoked key.
    """
    try:
        document = json.loads(raw.get_secret_value())
    except ValueError as exc:
        raise GoogleCredentialInvalidError(f"not JSON: {type(exc).__name__}") from None
    if not isinstance(document, dict):
        raise GoogleCredentialInvalidError("credential document is not a JSON object")

    kind = str(document.get("type", ""))
    if kind == "service_account":
        return _service_account(document)
    if kind == "authorized_user":
        return _authorized_user(document)
    # A type VEO has not seen. Guessing at its fields would build a credential that fails
    # at the first call with a message nobody can act on.
    raise GoogleCredentialInvalidError(f"unsupported credential type: {kind or 'absent'}")


def _service_account(document: dict[str, Any]) -> ServiceAccountCredentials:
    client_email = str(document.get("client_email", "")).strip()
    private_key = str(document.get("private_key", "")).strip()
    if not client_email or not private_key:
        raise GoogleCredentialInvalidError("service account is missing client_email/private_key")
    return ServiceAccountCredentials(
        client_email=client_email,
        private_key=SecretStr(private_key),
        token_uri=str(document.get("token_uri") or DEFAULT_TOKEN_URI),
    )


def _authorized_user(document: dict[str, Any]) -> AuthorizedUserCredentials:
    client_id = str(document.get("client_id", "")).strip()
    client_secret = str(document.get("client_secret", "")).strip()
    refresh_token = str(document.get("refresh_token", "")).strip()
    if not client_id or not client_secret or not refresh_token:
        raise GoogleCredentialInvalidError("authorized user credential is incomplete")
    return AuthorizedUserCredentials(
        client_id=client_id,
        client_secret=SecretStr(client_secret),
        refresh_token=SecretStr(refresh_token),
        token_uri=str(document.get("token_uri") or DEFAULT_TOKEN_URI),
    )


def search_console_from_settings(
    settings: ProviderCredentials | None = None,
) -> CredentialResolution[SearchConsoleCredentials]:
    resolved = settings if settings is not None else get_provider_credentials()
    return _search_console_resolution(resolved.google_search_console_credentials_json)


def search_console_from_vault(
    resolver: SecretResolver, *, organization_id: uuid.UUID
) -> CredentialResolution[SearchConsoleCredentials]:
    try:
        document = resolver.resolve_for_use(
            organization_id=organization_id,
            provider=CredentialProvider.GOOGLE_SEARCH_CONSOLE,
            field=CredentialField.CREDENTIALS_JSON,
        )
    except Exception:
        return _disabled(ProviderState.DISABLED_NO_CREDENTIAL)
    return _search_console_resolution(document)


def _search_console_resolution(
    document: SecretStr | None,
) -> CredentialResolution[SearchConsoleCredentials]:
    state = _state_for(document)
    if state is not ProviderState.ENABLED or document is None:
        return _disabled(state)
    try:
        credentials = parse_search_console_credentials(document)
    except GoogleCredentialInvalidError:
        # Something is stored, so this is not "no credential" — it is a credential that
        # cannot be used, which is the same remedy as a placeholder: fix what was saved.
        return _disabled(ProviderState.DISABLED_INVALID_CREDENTIAL)
    return CredentialResolution(credentials=credentials, state=state)
