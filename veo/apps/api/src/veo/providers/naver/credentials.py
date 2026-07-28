"""Where a Naver credential comes from, and what happens when there is none.

Two sources, in the order VEO prefers them:

* **The vault** — per-organization credentials an agency stored through
  ``/api/credentials``. This is the real answer for a multi-tenant product: one VEO
  deployment serves many agencies, each with its own Search Ad account.
* **Environment settings** — a single deployment-wide credential, useful for a local
  developer and for a single-tenant install.

Both resolvers return ``None`` rather than raising when nothing is configured. That is the
whole point of :class:`~veo.contracts.enums.ProviderState.DISABLED_NO_CREDENTIAL`: an
absent credential is a state VEO reports, not an exception it has to survive.

The vault resolver is typed against a narrow protocol rather than against
:class:`~veo.credentials.vault.CredentialVault` so that this module does not reach into
the vault's internals. ``resolve_for_use`` is the vault's documented seam for outbound
provider calls, and the secret it returns is passed straight into
:class:`~pydantic.SecretStr`-wrapped fields and unwrapped only inside the signing
function.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from pydantic import SecretStr

from veo.core.settings import ProviderCredentials, get_provider_credentials
from veo.credentials.providers import CredentialField, CredentialProvider
from veo.providers.naver.datalab import DataLabCredentials
from veo.providers.naver.searchad import SearchAdCredentials

__all__ = [
    "SecretResolver",
    "datalab_from_settings",
    "datalab_from_vault",
    "searchad_from_settings",
    "searchad_from_vault",
]


class SecretResolver(Protocol):
    """The vault's outbound seam, and nothing else from it."""

    def resolve_for_use(
        self,
        *,
        organization_id: uuid.UUID,
        provider: CredentialProvider,
        field: CredentialField,
    ) -> SecretStr: ...


def searchad_from_settings(
    settings: ProviderCredentials | None = None,
) -> SearchAdCredentials | None:
    """Deployment-wide Search Ad credentials, or ``None`` when the set is incomplete.

    A partial set is treated as no credential at all. Half a credential produces 401s
    against Naver rather than a working integration, and reporting "configured" for it
    would be worse than reporting nothing.
    """
    resolved = settings or get_provider_credentials()
    api_key = resolved.naver_searchad_api_key
    secret_key = resolved.naver_searchad_secret_key
    customer_id = resolved.naver_searchad_customer_id
    if api_key is None or secret_key is None or not customer_id:
        return None
    return SearchAdCredentials(
        api_key=api_key, secret_key=secret_key, customer_id=customer_id
    )


def datalab_from_settings(
    settings: ProviderCredentials | None = None,
) -> DataLabCredentials | None:
    resolved = settings or get_provider_credentials()
    client_id = resolved.naver_datalab_client_id
    client_secret = resolved.naver_datalab_client_secret
    if client_id is None or client_secret is None:
        return None
    return DataLabCredentials(client_id=client_id, client_secret=client_secret)


def searchad_from_vault(
    resolver: SecretResolver, *, organization_id: uuid.UUID
) -> SearchAdCredentials | None:
    """One organization's stored Search Ad credentials, or ``None``.

    Every vault failure — nothing stored, deactivated, undecryptable, or belonging to
    another organization — is indistinguishable here on purpose, and all of them mean the
    same thing to a caller: the provider is disabled for this organization.
    """
    try:
        api_key = resolver.resolve_for_use(
            organization_id=organization_id,
            provider=CredentialProvider.NAVER_SEARCH_AD,
            field=CredentialField.API_KEY,
        )
        secret_key = resolver.resolve_for_use(
            organization_id=organization_id,
            provider=CredentialProvider.NAVER_SEARCH_AD,
            field=CredentialField.SECRET_KEY,
        )
        customer_id = resolver.resolve_for_use(
            organization_id=organization_id,
            provider=CredentialProvider.NAVER_SEARCH_AD,
            field=CredentialField.CUSTOMER_ID,
        )
    except Exception:
        # The vault raises a not-found for every unusable state, and a broad catch keeps
        # a future vault error from turning "disabled" into a 500.
        return None
    return SearchAdCredentials(
        api_key=api_key,
        secret_key=secret_key,
        customer_id=customer_id.get_secret_value(),
    )


def datalab_from_vault(
    resolver: SecretResolver, *, organization_id: uuid.UUID
) -> DataLabCredentials | None:
    try:
        client_id = resolver.resolve_for_use(
            organization_id=organization_id,
            provider=CredentialProvider.NAVER_DATALAB,
            field=CredentialField.CLIENT_ID,
        )
        client_secret = resolver.resolve_for_use(
            organization_id=organization_id,
            provider=CredentialProvider.NAVER_DATALAB,
            field=CredentialField.CLIENT_SECRET,
        )
    except Exception:
        return None
    return DataLabCredentials(client_id=client_id, client_secret=client_secret)
