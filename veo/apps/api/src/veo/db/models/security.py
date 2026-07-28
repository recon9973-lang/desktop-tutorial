"""Sessions and stored provider credentials.

Two rules shape this module:

* A refresh token is never stored. Only its hash is, so a database dump does not hand
  someone a working session. Tokens rotate on every refresh and carry a family id, so
  replaying an already-rotated token reveals theft and burns the whole family.
* A provider secret goes in and is used. It never comes back out. There is no plaintext
  column, no decrypt-and-return path, and no permission that would allow one.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from veo.db.base import (
    Base,
    JsonObject,
    OrganizationScopedMixin,
    TimestampMixin,
    json_column,
    uuid_pk,
)


class UserSession(Base, OrganizationScopedMixin, TimestampMixin):
    """One refresh-token lineage, scoped to a single organization.

    A user who belongs to two organizations gets two sessions, never one session that
    can see both. The organization is fixed at sign-in and cannot be switched by
    changing a header.
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        UniqueConstraint("refresh_token_hash", name="uq_user_sessions_refresh_token_hash"),
        Index("ix_user_sessions_user_org", "user_id", "organization_id"),
        Index("ix_user_sessions_family_id", "family_id"),
        Index("ix_user_sessions_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # SHA-256 of the refresh token. The token itself exists only in the client's cookie.
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # All rotations of one sign-in share a family. Reusing a rotated token is theft;
    # the response is to revoke the entire family, not just that token.
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rotated_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    rotation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(
        String(48),
        nullable=True,
        comment="LOGOUT | ROTATED | REUSE_DETECTED | ADMIN_REVOKED | PASSWORD_CHANGED | EXPIRED",
    )

    # Client fingerprints are hashed. VEO does not keep raw IP addresses or user agents.
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class ProviderCredential(Base, OrganizationScopedMixin, TimestampMixin):
    """An external provider secret, encrypted at rest and write-only.

    ``fingerprint`` lets an operator answer "did the key change?" without anyone ever
    seeing the key. ``last_verification_error_code`` records why a check failed without
    storing the provider's error text, which routinely echoes the credential back.
    """

    __tablename__ = "provider_credentials"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider", "field", name="uq_provider_credential"),
        Index("ix_provider_credentials_org_provider", "organization_id", "provider"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        comment="NAVER_SEARCH_AD | NAVER_DATALAB | OPENAI | GOOGLE_SEARCH_CONSOLE | ...",
    )
    field: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="api_key | secret_key | customer_id | client_secret"
    )

    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False, default="AES-256-GCM")
    key_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Which master key encrypted this row."
    )

    # Non-reversible: identifies the value without revealing it.
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    # Safe to show an operator, e.g. the last 4 characters.
    display_hint: Mapped[str | None] = mapped_column(String(16), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_verification_error_code: Mapped[str | None] = mapped_column(
        String(48),
        nullable=True,
        comment="Machine code only. Provider error text often contains the credential.",
    )
    metadata_json: Mapped[JsonObject] = json_column()

    def __repr__(self) -> str:
        """Redacted by construction: a stray log line cannot print the secret."""
        return (
            f"<ProviderCredential provider={self.provider} field={self.field} "
            f"fingerprint={self.fingerprint[:8]}… REDACTED>"
        )


class LoginAttempt(Base, TimestampMixin):
    """Throttling and lockout state. Keyed by hashed identifiers only."""

    __tablename__ = "login_attempts"
    __table_args__ = (
        UniqueConstraint("identifier_hash", name="uq_login_attempts_identifier_hash"),
        Index("ix_login_attempts_locked_until", "locked_until"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    identifier_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="SHA-256 of the lowercased email, never the email."
    )
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
