"""Organizations, users, roles, customers, projects, sites and competitors."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from veo.db.base import (
    Base,
    ImmutableMixin,
    JsonObject,
    OrganizationScopedMixin,
    TimestampMixin,
    json_column,
    uuid_pk,
)


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    settings: Mapped[JsonObject] = json_column()


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Argon2 hash. The plaintext password never exists server-side beyond the request.
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RoleAssignment(Base, OrganizationScopedMixin, TimestampMixin):
    """A user's role inside one organization. Deny by default: no row means no access."""

    __tablename__ = "role_assignments"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "role"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class UserInvitation(Base, OrganizationScopedMixin, TimestampMixin):
    """A one-time link letting a new colleague set their own password.

    An administrator creates the account but never chooses the password — they would
    otherwise know a credential belonging to someone else, and every later action by that
    person would be deniable. The invitation carries the right to set one, once.

    Only the SHA-256 of the token is stored. The link is shown to the administrator at
    creation and is not recoverable afterwards, so a stolen database yields no usable
    invitations.
    """

    __tablename__ = "user_invitations"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Customer(Base, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Project(Base, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("organization_id", "slug"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="ko-KR")
    default_seo_spec_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_geo_spec_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    settings: Mapped[JsonObject] = json_column()


class Site(Base, OrganizationScopedMixin, TimestampMixin):
    __tablename__ = "sites"
    __table_args__ = (UniqueConstraint("project_id", "origin"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    crawl_settings: Mapped[JsonObject] = json_column()


class URLRecord(Base, OrganizationScopedMixin, TimestampMixin):
    """A canonical URL known to VEO, with the importance class used as a score denominator."""

    __tablename__ = "url_records"
    __table_args__ = (UniqueConstraint("site_id", "normalized_url"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(
        String(32), nullable=False, default="CONTENT_OR_PRODUCT"
    )
    importance_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="DEFAULT",
        comment="DEFAULT | SITEMAP | INTERNAL_LINKS | TRAFFIC | USER_OVERRIDE",
    )
    click_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_intentional_noindex: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Competitor(Base, OrganizationScopedMixin, TimestampMixin):
    """A comparison target.

    ``selection_source`` matters: share-of-voice changes with the competitor set, so VEO
    always shows whether the customer chose the set or VEO suggested it.
    """

    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("project_id", "origin"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand_aliases: Mapped[JsonObject] = json_column()
    selection_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="CUSTOMER_SPECIFIED",
        comment="CUSTOMER_SPECIFIED | VEO_SUGGESTED",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AuditLog(Base, ImmutableMixin):
    """Append-only record of who did what. Never carries secrets or raw customer content."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="USER")
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_ip_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Hashed, never the raw address."
    )
    detail: Mapped[JsonObject] = json_column()
