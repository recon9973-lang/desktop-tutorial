"""Lead capture, kept to what a callback actually needs.

A diagnosis that ends in "전화 주세요" needs a name and one way to reach the person. That
is the whole record. Everything else a marketing form usually asks for — birth date,
resident registration number, clinic size, budget band — is data VEO would then be
responsible for protecting, in exchange for nothing the first phone call cannot
establish. The request schema forbids unknown fields, so the minimisation is enforced by
the type rather than by whoever reviews the next pull request.

The response says what was stored, in Korean, field by field. Somebody who has just
typed their phone number into a stranger's website is entitled to read back exactly what
that stranger now has.

**Consent is deliberately not modelled here.** Korea's 개인정보 보호법 and 정보통신망법
distinguish collection consent from marketing-communication consent, require the
purpose, the retention period and the consequence of refusal to be stated separately,
and treat a pre-ticked box as no consent at all. Inventing a checkbox and a Korean
sentence to sit beside it would produce something that *looks* compliant, which is worse
than nothing. So this module records a lead as a service enquiry, states that no
marketing consent was taken, and the consent flow is filed as a contract request for
somebody with the legal text in front of them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, final, runtime_checkable

from veo.public.schemas import PublicLeadPayload, PublicLeadRequest

__all__ = [
    "CONSENT_NOTE_KO",
    "RETENTION_NOTE_KO",
    "InMemoryLeadStore",
    "LeadStore",
    "StoredLead",
    "capture_lead",
]

RETENTION_NOTE_KO = (
    "이 정보는 요청하신 무료 진단 상담 회신에만 사용합니다. 상담이 끝나면 파기하며, "
    "회신을 원하지 않으시면 같은 연락처로 삭제를 요청하실 수 있습니다."
)

CONSENT_NOTE_KO = (
    "광고·마케팅 수신 동의는 받지 않았고 저장하지도 않았습니다. 남겨 주신 연락처는 이번 "
    "진단 상담 회신 외의 목적으로 사용하지 않습니다."
)

#: The Korean label for each field that can end up in a record. Nothing outside this map
#: is storable, which is the point.
_FIELD_LABELS_KO: dict[str, str] = {
    "name": "이름",
    "phone": "전화번호",
    "email": "이메일",
    "site_url": "홈페이지 주소",
    "received_at": "접수 시각",
}


@final
@dataclass(frozen=True, slots=True)
class StoredLead:
    """One callback request. Five fields, and no sixth."""

    lead_id: uuid.UUID
    received_at: datetime
    name: str
    phone: str | None = None
    email: str | None = None
    site_url: str | None = None

    def stored_field_labels_ko(self) -> list[str]:
        """The Korean names of the fields that actually hold something."""
        present = ["name"]
        if self.phone:
            present.append("phone")
        if self.email:
            present.append("email")
        if self.site_url:
            present.append("site_url")
        present.append("received_at")
        return [_FIELD_LABELS_KO[name] for name in present]


@runtime_checkable
class LeadStore(Protocol):
    """Where a lead goes. Not a tenant table — a lead has no organization yet."""

    def add(self, lead: StoredLead) -> None: ...


@final
class InMemoryLeadStore:
    """Leads held in this process.

    **Limitation, stated plainly:** a restart loses every lead, and several API
    processes each keep their own. That is unacceptable for a sales pipeline and it is
    the honest state of this module — durable lead storage needs a table this worker
    does not own, and it is filed as a contract request. Anything durable built here
    would be a schema the integrator did not agree to.
    """

    __slots__ = ("_leads",)

    def __init__(self) -> None:
        self._leads: list[StoredLead] = []

    def add(self, lead: StoredLead) -> None:
        self._leads.append(lead)

    def all_leads(self) -> tuple[StoredLead, ...]:
        return tuple(self._leads)


def capture_lead(
    request: PublicLeadRequest,
    *,
    store: LeadStore,
    now: datetime | None = None,
) -> PublicLeadPayload:
    """Write down the callback request and report back what was written."""
    received_at = now or datetime.now(UTC)
    lead = StoredLead(
        lead_id=uuid.uuid4(),
        received_at=received_at,
        name=request.name.strip(),
        phone=request.phone.strip() if request.phone else None,
        email=request.email.strip() if request.email else None,
        site_url=request.site_url.strip() if request.site_url else None,
    )
    store.add(lead)
    return PublicLeadPayload(
        lead_id=str(lead.lead_id),
        received_at=lead.received_at,
        stored_fields_ko=lead.stored_field_labels_ko(),
        retention_note_ko=RETENTION_NOTE_KO,
        consent_note_ko=CONSENT_NOTE_KO,
    )
