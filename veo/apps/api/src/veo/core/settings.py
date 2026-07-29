"""Runtime configuration.

External providers are disabled unless a credential is present. A disabled provider makes
VEO report ``UNKNOWN`` with a reason — it never causes VEO to invent a plausible value.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from veo.contracts.enums import ProviderState

# The repository root, resolved from this file rather than from the working directory:
# the API, the worker and the test runner all start from different places, and an
# env_file resolved relative to cwd silently loads nothing for two of the three.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_ENV_FILE = _REPO_ROOT / ".env"



#: Strings that occupy a credential slot without being a credential.
#:
#: `vercel env pull` writes "[SENSITIVE]" for any variable marked Sensitive, so an
#: import can fill every slot and leave VEO convinced it is configured. The others are
#: the usual scaffolding people leave in a .env.example and then copy.
_PLACEHOLDER_VALUES = frozenset(
    {
        "[sensitive]",
        # Without the brackets too: stripping wrapper characters off a pasted value is a
        # normal repair, and it must not quietly turn a placeholder into a credential.
        "sensitive",
        "[redacted]",
        "redacted",
        "***",
        "****",
        "xxxx",
        "xxxxxxxx",
        "changeme",
        "change-me",
        "your-api-key-here",
        "your_api_key_here",
        "<your key>",
        "<your-key>",
        "todo",
        "tbd",
        "-",
        "null",
        "none",
        "undefined",
        "placeholder",
    }
)


def _is_placeholder(value: SecretStr | str | None) -> bool:
    """Whether a present value is scaffolding rather than a secret."""
    if value is None:
        return False
    raw = value.get_secret_value() if isinstance(value, SecretStr) else value
    return raw.strip().lower() in _PLACEHOLDER_VALUES


def _is_present(value: SecretStr | str | None) -> bool:
    if value is None:
        return False
    raw = value.get_secret_value() if isinstance(value, SecretStr) else value
    return bool(raw.strip())


def _state_of(*values: SecretStr | str | None) -> ProviderState:
    """Resolve a provider's state from the values it needs.

    Order matters. A placeholder anywhere wins over "everything is present", because a
    provider that is two-thirds configured is not two-thirds working — it fails every
    call, and the operator needs to be told which kind of failure they have.
    """
    if any(_is_placeholder(value) for value in values):
        return ProviderState.DISABLED_INVALID_CREDENTIAL
    if all(_is_present(value) for value in values):
        return ProviderState.ENABLED
    return ProviderState.DISABLED_NO_CREDENTIAL


class ProviderCredentials(BaseSettings):
    """Credentials for external data sources. Empty means disabled, not broken."""

    model_config = SettingsConfigDict(
        env_prefix="VEO_",
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    naver_searchad_api_key: SecretStr | None = None
    naver_searchad_secret_key: SecretStr | None = None
    naver_searchad_customer_id: str | None = None

    naver_datalab_client_id: SecretStr | None = None
    naver_datalab_client_secret: SecretStr | None = None

    # AI answer engines observed by the GEO observation engine. Each is independent:
    # a brand's visibility in Gemini and in ChatGPT are different measurements and are
    # never pooled without saying so (ADR 0014).
    openai_api_key: SecretStr | None = None
    google_gemini_api_key: SecretStr | None = None
    perplexity_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    google_pagespeed_api_key: SecretStr | None = None
    google_search_console_credentials_json: SecretStr | None = None

    def naver_searchad_state(self) -> ProviderState:
        return _state_of(
            self.naver_searchad_api_key,
            self.naver_searchad_secret_key,
            self.naver_searchad_customer_id,
        )

    def naver_datalab_state(self) -> ProviderState:
        return _state_of(self.naver_datalab_client_id, self.naver_datalab_client_secret)

    def openai_state(self) -> ProviderState:
        return _state_of(self.openai_api_key)

    def gemini_state(self) -> ProviderState:
        return _state_of(self.google_gemini_api_key)

    def perplexity_state(self) -> ProviderState:
        return _state_of(self.perplexity_api_key)

    def anthropic_state(self) -> ProviderState:
        return _state_of(self.anthropic_api_key)

    def pagespeed_state(self) -> ProviderState:
        return _state_of(self.google_pagespeed_api_key)

    def search_console_state(self) -> ProviderState:
        return _state_of(self.google_search_console_credentials_json)

    def states(self) -> dict[str, ProviderState]:
        return {
            "NAVER_SEARCH_AD": self.naver_searchad_state(),
            "NAVER_DATALAB": self.naver_datalab_state(),
            "OPENAI": self.openai_state(),
            "GOOGLE_GEMINI": self.gemini_state(),
            "PERPLEXITY": self.perplexity_state(),
            "ANTHROPIC": self.anthropic_state(),
            "GOOGLE_PAGESPEED": self.pagespeed_state(),
            "GOOGLE_SEARCH_CONSOLE": self.search_console_state(),
        }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VEO_",
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False

    app_name: str = "VEO"
    app_tagline: str = "SEO · GEO · Naver Keyword Intelligence Platform"
    developed_by: str = "VENOM"
    methodology_by: str = "VEO-LAB"

    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://localhost:5432/veo"
    redis_url: str = "redis://localhost:6379/0"

    # Secrets. Absent in local/test; required at startup in staging and production.
    jwt_secret: SecretStr | None = None
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 14

    # Master key for the provider-credential vault, base64-encoded 32 bytes.
    # Rotating it means re-encrypting rows under a new key_version, never decrypting
    # them into the application response.
    credential_encryption_key: SecretStr | None = None
    credential_key_version: int = 1
    # Retired master keys, newest first, as "version:base64key" entries. Rotation needs
    # them to read rows still encrypted under an older version; without them a rotation
    # would silently strand every existing credential.
    credential_previous_encryption_keys: list[str] = Field(default_factory=list)

    # Sign-in throttling. Lockout is per hashed identifier, so it cannot be used to
    # enumerate which addresses have accounts.
    login_max_failed_attempts: int = 8
    login_lockout_seconds: int = 900
    login_failure_window_seconds: int = 900

    public_result_ttl_seconds: int = 60 * 60 * 24 * 7
    #: Per caller — one unit per *scan*, counted against their address and their session.
    public_rate_limit_per_hour: int = 10
    public_max_urls_per_scan: int = 1

    #: 콘솔 진단이 한 번에 가져오는 페이지 수. 공개 진단이 1인 것은 남용을 막기 위해서고,
    #: 그 값으로는 사이트 전체를 봐야 판정되는 항목이 전부 UNKNOWN 으로 남는다.
    console_max_urls_per_scan: int = 20
    #: 콘솔 진단이 한 대상 호스트에 시간당 보낼 수 있는 요청 수. 로그인 여부와 무관하게
    #: VEO 가 남의 서버를 두드리는 도구가 되지 않도록 가드 안에서 부과한다.
    console_target_host_limit_per_hour: int = 300
    #: Per target host — one unit per *outbound HTTP request*, counted across the whole
    #: public surface, whoever asks. This is the control that stops VEO being pointed at
    #: a third party, and it deliberately has its own number rather than sharing the
    #: caller's.
    #:
    #: The two buckets count different things, which is exactly why one setting could not
    #: serve both. A scan costs at least two requests — the page and ``robots.txt`` — so
    #: reusing the caller's figure of 10 would have meant five scans per hour for any one
    #: site *in total*, and the site most often re-scanned is the owner's own, right after
    #: they have fixed something. Tightening the amplification cap must not be the same
    #: act as turning away an honest customer.
    #:
    #: 60 allows roughly 30 scans of one site per hour from everyone combined: generous
    #: for a clinic owner iterating on their homepage, and far below the volume that would
    #: make VEO worth using as a weapon.
    public_target_host_limit_per_hour: int = 60

    default_seo_spec_id: str = "veo.seo.readiness"
    default_geo_spec_id: str = "veo.geo.readiness"

    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _accept_plain_origins(cls, value: object) -> object:
        """`https://veo.seokorea.org` 처럼 사람이 실제로 쓰는 형태를 받아 준다.

        pydantic-settings 는 목록형 필드의 환경변수 값을 JSON 으로 읽으므로, 대괄호 없는
        주소 하나는 `SettingsError` 가 되고 **앱이 시작하지 못한다.** 배포 플랫폼에서는
        이것이 "빌드 성공 · 배포 성공 · 헬스체크 실패" 로만 보여서 네트워크 문제처럼
        읽히고, 옛 배포가 계속 서비스되기 때문에 "배포했는데 코드가 안 바뀐다" 가 된다.

        형식만 관대하게 받을 뿐, 목록을 넓히지는 않는다. 빈 값은 기본값으로 되돌리지
        않고 거부한다 — 조용히 되돌리면 운영 환경에 localhost 가 남는다.
        """
        if not isinstance(value, str):
            return value

        text = value.strip()
        if text.startswith("["):
            # 이미 JSON 으로 넣어 둔 배포를 깨뜨리지 않는다. 환경변수 경로에서는
            # pydantic 이 먼저 파싱해 주지만, 코드에서 직접 넘길 때는 여기서 읽는다.
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                raise ValueError(f"목록으로 읽을 수 없는 값입니다: {text!r}") from None

        entries = [entry.strip() for entry in text.split(",") if entry.strip()]
        if not entries:
            # 빈 값을 기본값으로 되돌리면 운영 환경에 localhost 가 남는다.
            raise ValueError("빈 값입니다. 허용할 출처를 적거나 변수를 지우십시오.")
        return entries

    #: Where the console is served from — the origin an invitation link points at.
    #: Deliberately its own setting rather than derived from ``cors_allowed_origins``:
    #: that list is a security boundary and may hold several entries, and picking one of
    #: them to build a link would make a change to CORS silently rewrite every invitation
    #: an administrator sends. Set this to the address staff actually type.
    console_base_url: str = "http://localhost:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def branding_block(self) -> str:
        return (
            f"{self.app_name}\n{self.app_tagline}\n\n"
            f"Developed by {self.developed_by}\n"
            f"Research & Methodology by {self.methodology_by}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_provider_credentials() -> ProviderCredentials:
    return ProviderCredentials()
