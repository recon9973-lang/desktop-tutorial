"""Where a Google credential comes from, and the three ways there is not one.

An empty slot, a slot filled with ``[SENSITIVE]``, and a working key are three different
states with three different remedies. Collapsing the middle one into either neighbour is
the bug this suite exists to prevent: an operator told "no credential" will paste the key
again, while the slot already holds a placeholder that a `vercel env pull` wrote.
"""

from __future__ import annotations

import json
import uuid

import pytest
from google_fixtures import authorized_user_json, service_account_json
from pydantic import SecretStr

from veo.contracts.enums import ProviderState
from veo.core.settings import ProviderCredentials
from veo.credentials.providers import CredentialField, CredentialProvider
from veo.providers.google.credentials import (
    AuthorizedUserCredentials,
    CredentialResolution,
    PageSpeedCredentials,
    ServiceAccountCredentials,
    crux_from_settings,
    pagespeed_from_settings,
    pagespeed_from_vault,
    parse_search_console_credentials,
    search_console_from_settings,
    search_console_from_vault,
)
from veo.providers.google.errors import GoogleCredentialInvalidError

ORGANIZATION = uuid.UUID("00000000-0000-4000-8000-00000000beef")


def settings_with(**values: object) -> ProviderCredentials:
    return ProviderCredentials(**values)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #


def test_a_present_pagespeed_key_resolves_to_an_enabled_credential() -> None:
    resolution = pagespeed_from_settings(
        settings_with(google_pagespeed_api_key=SecretStr("synthetic-pagespeed-key"))
    )
    assert resolution.state is ProviderState.ENABLED
    assert isinstance(resolution.credentials, PageSpeedCredentials)


def test_an_empty_slot_is_no_credential() -> None:
    resolution = pagespeed_from_settings(settings_with(google_pagespeed_api_key=None))
    assert resolution.state is ProviderState.DISABLED_NO_CREDENTIAL
    assert resolution.credentials is None


@pytest.mark.parametrize("placeholder", ["[SENSITIVE]", "sensitive", "changeme", "TODO"])
def test_a_placeholder_is_invalid_and_never_enabled(placeholder: str) -> None:
    resolution = pagespeed_from_settings(
        settings_with(google_pagespeed_api_key=SecretStr(placeholder))
    )
    assert resolution.state is ProviderState.DISABLED_INVALID_CREDENTIAL
    assert resolution.credentials is None


def test_a_placeholder_search_console_credential_is_invalid_not_missing() -> None:
    resolution = search_console_from_settings(
        settings_with(google_search_console_credentials_json=SecretStr("[SENSITIVE]"))
    )
    assert resolution.state is ProviderState.DISABLED_INVALID_CREDENTIAL
    assert resolution.credentials is None


def test_a_service_account_json_resolves_to_service_account_credentials() -> None:
    resolution = search_console_from_settings(
        settings_with(google_search_console_credentials_json=SecretStr(service_account_json()))
    )
    assert resolution.state is ProviderState.ENABLED
    assert isinstance(resolution.credentials, ServiceAccountCredentials)


def test_an_authorized_user_json_resolves_to_authorized_user_credentials() -> None:
    resolution = search_console_from_settings(
        settings_with(google_search_console_credentials_json=SecretStr(authorized_user_json()))
    )
    assert isinstance(resolution.credentials, AuthorizedUserCredentials)


def test_json_that_is_not_a_credential_is_invalid_rather_than_missing() -> None:
    resolution = search_console_from_settings(
        settings_with(google_search_console_credentials_json=SecretStr("{not json at all"))
    )
    assert resolution.state is ProviderState.DISABLED_INVALID_CREDENTIAL
    assert resolution.credentials is None


def test_an_unknown_credential_type_is_rejected_rather_than_guessed() -> None:
    raw = json.dumps({"type": "some_future_type", "client_email": "a@b.example.com"})
    with pytest.raises(GoogleCredentialInvalidError):
        parse_search_console_credentials(SecretStr(raw))


def test_a_service_account_missing_its_private_key_is_rejected() -> None:
    raw = json.dumps({"type": "service_account", "client_email": "a@b.example.com"})
    with pytest.raises(GoogleCredentialInvalidError):
        parse_search_console_credentials(SecretStr(raw))


def test_crux_reads_the_same_key_as_pagespeed_and_says_so() -> None:
    """One Google API key covers both APIs; VEO does not pretend to a second slot."""
    settings = settings_with(google_pagespeed_api_key=SecretStr("synthetic-pagespeed-key"))
    assert crux_from_settings(settings).state is ProviderState.ENABLED
    assert crux_from_settings(settings).credentials == pagespeed_from_settings(settings).credentials


# --------------------------------------------------------------------------- #
# Vault
# --------------------------------------------------------------------------- #


class StubVault:
    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self.values = values
        self.calls: list[tuple[str, str]] = []

    def resolve_for_use(
        self,
        *,
        organization_id: uuid.UUID,
        provider: CredentialProvider,
        field: CredentialField,
    ) -> SecretStr:
        key = (str(provider), str(field))
        self.calls.append(key)
        if key not in self.values:
            raise LookupError("nothing stored")
        return SecretStr(self.values[key])


def test_a_stored_pagespeed_key_is_resolved_for_the_organization() -> None:
    vault = StubVault({("GOOGLE_PAGESPEED", "api_key"): "synthetic-stored-key"})
    resolution = pagespeed_from_vault(vault, organization_id=ORGANIZATION)
    assert resolution.state is ProviderState.ENABLED
    assert resolution.credentials is not None


def test_an_empty_vault_disables_rather_than_raises() -> None:
    resolution = pagespeed_from_vault(StubVault({}), organization_id=ORGANIZATION)
    assert resolution.state is ProviderState.DISABLED_NO_CREDENTIAL
    assert resolution.credentials is None


def test_a_placeholder_stored_in_the_vault_is_still_a_placeholder() -> None:
    vault = StubVault({("GOOGLE_PAGESPEED", "api_key"): "[SENSITIVE]"})
    resolution = pagespeed_from_vault(vault, organization_id=ORGANIZATION)
    assert resolution.state is ProviderState.DISABLED_INVALID_CREDENTIAL


def test_a_stored_service_account_is_parsed() -> None:
    vault = StubVault({("GOOGLE_SEARCH_CONSOLE", "credentials_json"): service_account_json()})
    resolution = search_console_from_vault(vault, organization_id=ORGANIZATION)
    assert isinstance(resolution.credentials, ServiceAccountCredentials)


def test_unparseable_vault_content_disables_instead_of_exploding() -> None:
    vault = StubVault({("GOOGLE_SEARCH_CONSOLE", "credentials_json"): "not json"})
    resolution = search_console_from_vault(vault, organization_id=ORGANIZATION)
    assert resolution.state is ProviderState.DISABLED_INVALID_CREDENTIAL
    assert resolution.credentials is None


# --------------------------------------------------------------------------- #
# The resolution object cannot lie
# --------------------------------------------------------------------------- #


def test_a_resolution_cannot_be_enabled_with_nothing_in_it() -> None:
    with pytest.raises(ValueError, match="ENABLED"):
        CredentialResolution(credentials=None, state=ProviderState.ENABLED)


def test_a_resolution_cannot_hold_a_credential_and_claim_to_be_disabled() -> None:
    with pytest.raises(ValueError, match="ENABLED"):
        CredentialResolution(
            credentials=PageSpeedCredentials(api_key=SecretStr("synthetic")),
            state=ProviderState.DISABLED_NO_CREDENTIAL,
        )


def test_a_secret_never_renders_in_a_repr() -> None:
    resolution = pagespeed_from_settings(
        settings_with(google_pagespeed_api_key=SecretStr("synthetic-pagespeed-key"))
    )
    assert "synthetic-pagespeed-key" not in repr(resolution)
