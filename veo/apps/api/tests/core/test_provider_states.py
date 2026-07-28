"""A credential that is present but not usable must not read as ENABLED.

Found the hard way. `vercel env pull` replaces any variable marked "Sensitive" with the
literal string ``[SENSITIVE]``, so an import can fill every slot with placeholders and
leave the product convinced it is configured. VEO then made a real call and got a 403.

A decoy credential is worse than no credential. With none, VEO reports 측정 불가 and says
why. With a decoy it reports ENABLED, opens connections, collects authentication failures
against someone else's API, and tells the operator nothing useful.
"""

from __future__ import annotations

import pytest

from veo.contracts.enums import ProviderState
from veo.core.settings import ProviderCredentials

REAL_KEY = "0100000000ab1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f"


def credentials(**overrides: str | None) -> ProviderCredentials:
    # `_env_file=None` keeps the developer's real .env out of these assertions. Without
    # it the "unset" cases silently pick up whatever is configured on this machine, and
    # the test that matters most — unset differs from decoy — passes or fails depending
    # on who runs it.
    return ProviderCredentials(_env_file=None, **overrides)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Placeholders every tool we might import from is known to emit
# --------------------------------------------------------------------------- #

PLACEHOLDERS = [
    "[SENSITIVE]",  # vercel env pull, for variables marked Sensitive
    "[REDACTED]",
    "***",
    "changeme",
    "your-api-key-here",
    "xxxxxxxx",
    "TODO",
    "<your key>",
    "-",
    "null",
    "None",
]


@pytest.mark.parametrize("placeholder", PLACEHOLDERS)
def test_a_placeholder_is_not_a_credential(placeholder: str) -> None:
    state = credentials(
        naver_searchad_api_key=placeholder,
        naver_searchad_secret_key=placeholder,
        naver_searchad_customer_id=placeholder,
    ).naver_searchad_state()

    assert state is not ProviderState.ENABLED, (
        f"{placeholder!r} was accepted as a working credential"
    )


@pytest.mark.parametrize("placeholder", PLACEHOLDERS)
def test_placeholder_detection_ignores_case_and_padding(placeholder: str) -> None:
    state = credentials(
        naver_datalab_client_id=f"  {placeholder.upper()}  ",
        naver_datalab_client_secret=f"  {placeholder.lower()}  ",
    ).naver_datalab_state()
    assert state is not ProviderState.ENABLED


def test_a_placeholder_reports_its_own_state_not_merely_disabled() -> None:
    """The operator needs to know the difference between 'unset' and 'filled with junk'."""
    unset = credentials().naver_searchad_state()
    decoy = credentials(
        naver_searchad_api_key="[SENSITIVE]",
        naver_searchad_secret_key="[SENSITIVE]",
        naver_searchad_customer_id="[SENSITIVE]",
    ).naver_searchad_state()

    assert unset is ProviderState.DISABLED_NO_CREDENTIAL
    assert decoy is ProviderState.DISABLED_INVALID_CREDENTIAL
    assert decoy is not unset


def test_one_placeholder_among_real_values_still_disables_the_provider() -> None:
    """Naver Search Ad needs all three. Two real and one decoy is not two thirds working."""
    state = credentials(
        naver_searchad_api_key=REAL_KEY,
        naver_searchad_secret_key=REAL_KEY,
        naver_searchad_customer_id="[SENSITIVE]",
    ).naver_searchad_state()
    assert state is ProviderState.DISABLED_INVALID_CREDENTIAL


# --------------------------------------------------------------------------- #
# Real values still work
# --------------------------------------------------------------------------- #


def test_real_looking_values_are_enabled() -> None:
    state = credentials(
        naver_searchad_api_key=REAL_KEY,
        naver_searchad_secret_key=REAL_KEY,
        naver_searchad_customer_id="1234567",
    ).naver_searchad_state()
    assert state is ProviderState.ENABLED


def test_a_short_but_genuine_customer_id_is_not_mistaken_for_a_placeholder() -> None:
    """Customer ids are short numbers; a length rule alone would reject them."""
    state = credentials(
        naver_searchad_api_key=REAL_KEY,
        naver_searchad_secret_key=REAL_KEY,
        naver_searchad_customer_id="70123",
    ).naver_searchad_state()
    assert state is ProviderState.ENABLED


def test_an_empty_value_is_unset_not_invalid() -> None:
    assert credentials(openai_api_key="").openai_state() is ProviderState.DISABLED_NO_CREDENTIAL
    assert credentials(openai_api_key="   ").openai_state() is (
        ProviderState.DISABLED_NO_CREDENTIAL
    )


def test_every_provider_screens_for_placeholders() -> None:
    """Whatever we add later must be screened too, not just the ones that bit us.

    The field list is derived from the model rather than written out here. An earlier
    version spelled the fields by hand and so failed to notice three new answer-engine
    credentials the moment they were added — a test that claims to cover "whatever we add
    later" has to find the new fields by itself, or it only covers what it was told about.
    """
    decoy = "[SENSITIVE]"
    every_credential_field = {
        name: decoy
        for name, info in ProviderCredentials.model_fields.items()
        if name != "model_config"
    }
    states = credentials(**every_credential_field).states()

    assert states, "no providers were reported at all"
    assert set(states.values()) == {ProviderState.DISABLED_INVALID_CREDENTIAL}, states


def test_the_placeholder_screen_covers_every_declared_provider() -> None:
    """states() must report on every provider, so none can skip the screen silently."""
    reported = set(credentials().states())
    assert len(reported) >= 8, f"only {len(reported)} providers reported: {sorted(reported)}"
    for expected in ("OPENAI", "GOOGLE_GEMINI", "NAVER_SEARCH_AD", "NAVER_DATALAB"):
        assert expected in reported


def test_states_never_reports_enabled_for_a_provider_it_cannot_use() -> None:
    mixed = credentials(
        naver_searchad_api_key=REAL_KEY,
        naver_searchad_secret_key=REAL_KEY,
        naver_searchad_customer_id="1234567",
        openai_api_key="[SENSITIVE]",
    ).states()

    assert mixed["NAVER_SEARCH_AD"] is ProviderState.ENABLED
    assert mixed["OPENAI"] is ProviderState.DISABLED_INVALID_CREDENTIAL
