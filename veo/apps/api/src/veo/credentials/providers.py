"""Which providers take credentials, which fields they need, and how a check can fail.

:class:`veo.contracts.enums.DataSource` answers "where did this number come from?" and is
not the right vocabulary here — ``OPENAI`` is not a data source (an AI answer is recorded
as ``AI_ENGINE_OBSERVATION``), and ``CALCULATED`` and ``VEO_CRAWLER`` obviously hold no
secret. So this module names the credential-holding providers separately, using the
**exact same strings** as ``GET /api/providers`` in ``api/routes/meta.py``: the two
endpoints report the same providers, one from environment settings and one from stored
credentials, and an operator comparing them must not have to translate names. Keeping
that set aligned is the one maintenance obligation this module carries — see
``INTEGRATION_REQUEST.md`` for the proposal to move it into ``contracts``.

The field names are a closed set on purpose. They are embedded in the associated data
that binds a ciphertext to its row, so an arbitrary string there would be an injection
point as well as a typo waiting to split one credential across two rows.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

__all__ = [
    "CREDENTIAL_PROVIDERS",
    "PROVIDER_FIELDS",
    "CredentialField",
    "CredentialProvider",
    "VerificationErrorCode",
    "fields_for",
    "is_credential_provider",
]


class CredentialProvider(StrEnum):
    """An external provider VEO stores a secret for.

    Names that appear here match ``ProviderCredentials.states()`` in ``core/settings.py``
    exactly, so ``/api/providers`` and ``/api/credentials`` never disagree about what a
    provider is *called*.

    **They are not the same set.** ``states()`` knows eight providers; this enum has
    five. ``GOOGLE_GEMINI``, ``PERPLEXITY`` and ``ANTHROPIC`` — the AI answer engines —
    have settings fields and no vault slot, so their keys can only come from deployment
    environment variables today. Adding them here is item ② of the sequence recorded in
    ``docs/audit/2026-08-08-server-ui-gap.md`` §A-2; item ① (should outbound calls read
    the vault at all?) is an open decision that changes boot conditions.

    The docstring used to claim the two sets matched "one for one". They did when it was
    written. Checked 2026-08-08: they do not.
    """

    NAVER_SEARCH_AD = "NAVER_SEARCH_AD"
    NAVER_DATALAB = "NAVER_DATALAB"
    OPENAI = "OPENAI"
    GOOGLE_PAGESPEED = "GOOGLE_PAGESPEED"
    GOOGLE_SEARCH_CONSOLE = "GOOGLE_SEARCH_CONSOLE"


class CredentialField(StrEnum):
    """A single named slot inside one provider's credential set.

    ``customer_id`` and ``client_id`` are not secret in the way an API key is, but they
    are stored exactly the same way. Treating half a credential set as public is how the
    other half ends up in a log line next to it.
    """

    API_KEY = "api_key"
    SECRET_KEY = "secret_key"  # noqa: S105 - a field name, not a value
    CUSTOMER_ID = "customer_id"
    CLIENT_ID = "client_id"
    CLIENT_SECRET = "client_secret"  # noqa: S105 - a field name, not a value
    CREDENTIALS_JSON = "credentials_json"


class VerificationErrorCode(StrEnum):
    """Why a verification failed — a machine code, and nothing else.

    A provider's own error text routinely quotes the credential back at you, so it is
    never persisted and never returned. The operator gets a code; the details, already
    redacted, go to the server log.
    """

    MISSING_FIELDS = "MISSING_FIELDS"
    DECRYPT_FAILED = "DECRYPT_FAILED"
    PROVIDER_UNAUTHORIZED = "PROVIDER_UNAUTHORIZED"
    PROVIDER_FORBIDDEN = "PROVIDER_FORBIDDEN"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


#: Every field a provider needs before VEO will call it. Order is the display order.
#: These mirror the credential sets already declared in ``ProviderCredentials``.
PROVIDER_FIELDS: Mapping[CredentialProvider, tuple[CredentialField, ...]] = (
    MappingProxyType(
        {
            CredentialProvider.NAVER_SEARCH_AD: (
                CredentialField.API_KEY,
                CredentialField.SECRET_KEY,
                CredentialField.CUSTOMER_ID,
            ),
            CredentialProvider.NAVER_DATALAB: (
                CredentialField.CLIENT_ID,
                CredentialField.CLIENT_SECRET,
            ),
            CredentialProvider.OPENAI: (CredentialField.API_KEY,),
            CredentialProvider.GOOGLE_PAGESPEED: (CredentialField.API_KEY,),
            CredentialProvider.GOOGLE_SEARCH_CONSOLE: (
                CredentialField.CREDENTIALS_JSON,
            ),
        }
    )
)

#: Providers with at least one field to store. Every enum member qualifies today; the
#: distinction is kept so adding a credential-free provider cannot silently create a
#: storable one with an empty field set.
CREDENTIAL_PROVIDERS: frozenset[CredentialProvider] = frozenset(
    provider for provider, fields in PROVIDER_FIELDS.items() if fields
)


def is_credential_provider(provider: CredentialProvider) -> bool:
    return provider in CREDENTIAL_PROVIDERS


def fields_for(provider: CredentialProvider) -> tuple[CredentialField, ...]:
    """The fields ``provider`` needs, or an empty tuple if it stores nothing."""
    return PROVIDER_FIELDS.get(provider, ())
