"""홈페이지에서 식별 정보를 **읽어 후보로 내놓는다.** 저장하지는 않는다.

## 왜 후보인가 — 자동으로 채우면 안 되는 이유

브랜드 식별은 "이 언급이 우리 고객의 것인가" 를 가르는 자리다. 그래서 값이 하나 더
들어가면 확신도가 올라가고, 확신도가 확정선(0.75)을 넘으면 **사람 검수를 건너뛴다**
(`detection/disambiguation.py`). 즉 **틀린 값을 자동으로 채우는 것은 틀린 판정을
검수 없이 확정시키는 일**이다. 오인을 막으려고 만든 기능이 오인을 만든다.

그럴 위험이 실제로 있다. 등록된 거래처 홈페이지 5곳에서 재봤다(2026-08-09):

* 소재지 후보로 ``변경시 반드시 사전동`` 이 나왔다 — 개인정보처리방침의
  "…변경시 반드시 사전 동의…" 가 주소 모양에 걸린 것이다.
* 전화 후보에 대표번호와 함께 담당자 휴대폰 두 개가 같이 나왔다.
* 대표자 후보에 ``원장`` ``소개`` ``정회원`` 같은 말이 섞였다.

그래서 이 모듈은 **고르기만 한다.** 사람이 눌러야 들어간다.

## 근거를 함께 낸다

후보마다 어디서 나왔는지(:class:`CandidateSource`)를 붙인다. 사이트가 구조화 데이터로
**스스로 선언한** 값과, 본문 글자 모양으로 **우리가 찾아낸** 값은 믿을 만한 정도가
다르다. 전자만 미리 체크해 두고(:attr:`IdentityCandidate.preselected`), 후자는 사람이
직접 누르게 한다.

## 왜 이 항목들인가

AI 답변이 근거로 드는 글은 홈페이지만이 아니다. 기사·블로그·카페 글에는 전화번호도
홈페이지 주소도 없는 경우가 흔하다. 그런 글에서 우리 고객을 가려내는 것은 **대표자
성함** 쪽이다. 판별기를 실제로 돌려 본 값(전화번호가 본문에 없는 블로그 모양 글):

===============================  ==========  =========
선언한 것                          확신도       결과
===============================  ==========  =========
이름만                             0.40        검수 대기
+ 소재지                           0.60        검수 대기
+ 소재지 + 전화번호                  0.60        검수 대기
+ 소재지 + 대표자 성함               0.75        확정
===============================  ==========  =========

전화번호는 글에 없으면 아무 일도 하지 않는다. 그래서 한 항목만 잘 뽑는 것이 아니라
**상호·도메인·전화·소재지·대표자**를 함께 뽑는다.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlsplit

from veo.geo.entity_graph import EntityNode, build_entity_graph
from veo.geo.parsing import PageDocument, normalise, parse_html
from veo.observations.brand_identity import normalise_phone
from veo.observations.detection.disambiguation import KOREAN_LOCALITY_TERMS

__all__ = [
    "CandidateSource",
    "IdentityCandidate",
    "IdentityField",
    "SiteIdentityDraft",
    "read_identity_draft",
]

#: 한 항목에서 사람에게 보여 줄 후보의 최대 개수. 목록이 길면 고르지 않고 넘긴다.
MAX_PER_FIELD = 5


class IdentityField(StrEnum):
    """브랜드 식별 폼의 어느 칸에 들어갈 후보인가."""

    DISPLAY_NAME = "DISPLAY_NAME"
    OWN_DOMAIN = "OWN_DOMAIN"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    REPRESENTATIVE = "REPRESENTATIVE"
    BUSINESS_NUMBER = "BUSINESS_NUMBER"


class CandidateSource(StrEnum):
    """이 값을 어디서 얻었는가. 믿을 만한 정도가 달라 화면에서 갈라 보여 준다."""

    #: 사이트가 구조화 데이터(JSON-LD)로 스스로 선언한 값.
    DECLARED = "DECLARED"
    #: 본문 글자에서 모양으로 찾아낸 값. 틀린 것이 섞인다.
    FOUND_IN_TEXT = "FOUND_IN_TEXT"
    #: 등록한 주소 자체에서 나온 값.
    FROM_URL = "FROM_URL"


_SOURCE_NOTE_KO = {
    CandidateSource.DECLARED: "사이트가 구조화 데이터로 선언한 값입니다.",
    CandidateSource.FOUND_IN_TEXT: "본문에서 찾은 값입니다. 맞는지 확인하십시오.",
    CandidateSource.FROM_URL: "등록한 홈페이지 주소에서 가져왔습니다.",
}


@dataclass(frozen=True, slots=True)
class IdentityCandidate:
    """사람이 누르면 들어갈 값 하나."""

    field: IdentityField
    value: str
    source: CandidateSource

    @property
    def preselected(self) -> bool:
        """미리 체크해 둘 것인가.

        본문에서 찾은 값은 **절대 미리 체크하지 않는다.** 실측에서 틀린 후보가 나왔고,
        미리 체크된 것은 사람이 그냥 저장한다.
        """
        return self.source is not CandidateSource.FOUND_IN_TEXT

    @property
    def note_ko(self) -> str:
        return _SOURCE_NOTE_KO[self.source]


@dataclass(frozen=True, slots=True)
class SiteIdentityDraft:
    """한 사이트에서 읽어 낸 후보 전부. 저장된 것은 하나도 없다."""

    url: str
    candidates: tuple[IdentityCandidate, ...] = ()
    notes_ko: tuple[str, ...] = field(default=())

    def of(self, wanted: IdentityField) -> tuple[IdentityCandidate, ...]:
        return tuple(one for one in self.candidates if one.field is wanted)

    @property
    def found_nothing(self) -> bool:
        return not self.candidates


# --------------------------------------------------------------------------- #
# 글자 모양
# --------------------------------------------------------------------------- #

#: 한국 유선·이동·대표번호. 앞자리를 열거해 **아무 숫자열이나 걸리지 않게** 한다.
#: 실측 2026-08-09: 앞자리 제한이 없으면 사업자등록번호(10자리)가 전화번호로 걸렸다.
_PHONE_RE = re.compile(
    r"0(?:2|[3-6][1-5]|70|1[016-9])[-.\s]?\d{3,4}[-.\s]?\d{4}"  # 지역·휴대폰
    r"|1[5-9]\d{2}[-.\s]?\d{4}"  # 1544·1661 같은 대표번호
)

#: 도로명·지번 주소. 시/군/구 다음에 로·길·동·읍·면이 오는 모양만 본다.
_ADDRESS_RE = re.compile(
    r"[가-힣]{2,10}(?:특별시|광역시|특별자치시|특별자치도|도)?\s*"
    r"[가-힣]{1,10}(?:시|군|구)\s+"
    r"[가-힣0-9]{1,20}(?:로|길|동|읍|면)\s*[0-9-]{0,10}"
)

# 콜론을 두 벌 넣는다. 한국 홈페이지 바닥글은 전각 콜론(U+FF1A)을 실제로 쓰고,
# 반각으로만 찾으면 그런 줄을 통째로 놓친다.
_BUSINESS_NUMBER_RE = re.compile(
    r"(?:사업자\s*등록\s*번호|사업자\s*번호)\s*[:：]?\s*(\d{3}-?\d{2}-?\d{5})"  # noqa: RUF001
)

#: "대표원장 홍길동" 과 "홍길동 원장" 두 모양. 전각 콜론을 넣는 이유는 위와 같다.
_REPRESENTATIVE_RE = (
    re.compile(r"(?:대표원장|대표이사|대표자|대표)\s*[:：]?\s*([가-힣]{2,4})(?![가-힣])"),  # noqa: RUF001
    re.compile(r"([가-힣]{2,4})\s*(?:대표원장|원장|대표이사)(?![가-힣])"),
)

#: 사람 이름 자리에 걸리지만 이름이 아닌 말. 실측에서 실제로 나온 것들이다.
_NOT_A_NAME = frozenset(
    {
        "원장", "원장이", "대표", "대표님", "소개", "진료", "전화", "정회원", "회원",
        "병원", "의원", "한의원", "치과", "센터", "클리닉", "고객", "정보", "내용",
        "서비스", "이용", "회사", "당사", "본원", "저희", "기타", "예약", "상담",
        "문의", "위치", "시간", "안내", "인사말", "의료진", "우리", "모든", "각종",
        "약속", "믿음", "정성", "진심", "최고", "함께", "언제나", "항상",
    }
)

#: 성씨 한 글자. 이름 후보가 이것으로 시작하지 않으면 사람 이름이 아니라고 본다.
#:
#: 목록을 늘리는 것이 목적이 아니다 — **줄이는 것**이 목적이다. 여기 없는 희성은
#: 후보에서 빠지지만, 그때 사람이 직접 입력하면 된다. 반대로 목록을 넓게 잡으면
#: ``약속`` ``정성`` 같은 말이 그대로 통과한다.
_SURNAMES = frozenset(
    "김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구"
    "민진지엄채원천방공현함변염여추도소석선설마길연위표명기반라왕금옥육인맹제모탁국"
    "여진어은편용"
)

#: 주소 후보가 진짜 주소이려면 아는 지역명이 하나는 들어 있어야 한다.
#:
#: 실측 2026-08-09 — 이 검사가 없을 때 개인정보처리방침의 "…변경시 반드시 사전 동의…"
#: 가 ``변경시 반드시 사전동`` 이라는 주소 후보로 나왔다.
_LOCALITY_LOOKUP = frozenset(KOREAN_LOCALITY_TERMS)

#: 도로명 + 번지. 지역명이 없어도 이 모양이면 주소로 본다.
_STREET_NUMBER_RE = re.compile(r"[가-힣0-9]+(?:로|길)\s*\d")


def _phone_key(value: str) -> str | None:
    """비교용 숫자열. 전화번호가 아니면 ``None``."""
    return normalise_phone(value)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


# --------------------------------------------------------------------------- #
# 읽기
# --------------------------------------------------------------------------- #


def read_identity_draft(html: str, *, url: str) -> SiteIdentityDraft:
    """한 페이지에서 식별 후보를 읽는다. 아무것도 저장하지 않는다.

    HTML 이 깨져 있어도 예외를 내지 않는다 — 파싱 실패는 사이트에 대한 사실이지
    진단의 고장이 아니다(`geo/parsing.parse_html` 과 같은 태도).
    """
    page = parse_html(html)
    graph = build_entity_graph(page)
    organization = graph.primary_organization()
    text = page.visible_text

    business_numbers = tuple(
        dict.fromkeys(normalise(one) for one in _BUSINESS_NUMBER_RE.findall(text))
    )

    found: list[IdentityCandidate] = []
    found.extend(_names(page, organization))
    found.extend(_domains(url))
    found.extend(_phones(text, organization, business_numbers))
    found.extend(_addresses(text, organization))
    found.extend(_representatives(text))
    found.extend(
        IdentityCandidate(IdentityField.BUSINESS_NUMBER, one, CandidateSource.FOUND_IN_TEXT)
        for one in business_numbers[:MAX_PER_FIELD]
    )

    notes: list[str] = []
    if not page.json_ld_blocks:
        notes.append(
            "이 사이트에는 구조화 데이터가 없어 본문 글자에서 찾았습니다. "
            "값이 맞는지 하나씩 확인하십시오."
        )
    if not found:
        notes.append("읽을 수 있는 식별 정보를 찾지 못했습니다. 직접 입력하십시오.")

    return SiteIdentityDraft(url=url, candidates=tuple(found), notes_ko=tuple(notes))


def _names(page: PageDocument, organization: EntityNode | None) -> Iterator[IdentityCandidate]:
    """상호 후보. 구조화 데이터의 이름과 ``og:site_name`` — 흔히 같으므로 한 번만 낸다."""
    seen: set[str] = set()
    declared = (
        normalise(organization.name) if organization is not None else "",
        normalise(page.meta_properties.get("og:site_name", "")),
    )
    for name in declared:
        if name and name not in seen:
            seen.add(name)
            yield IdentityCandidate(
                IdentityField.DISPLAY_NAME, name, CandidateSource.DECLARED
            )


def _domains(url: str) -> Iterator[IdentityCandidate]:
    host = (urlsplit(url).hostname or "").lower()
    if host:
        yield IdentityCandidate(IdentityField.OWN_DOMAIN, host, CandidateSource.FROM_URL)


def _phones(
    text: str, organization: EntityNode | None, business_numbers: Sequence[str]
) -> Iterator[IdentityCandidate]:
    """전화번호 후보.

    사업자등록번호를 **명시적으로 제외한다.** 10자리라 전화번호 자릿수 검사를 통과하고,
    한 번 들어가면 그 숫자가 답변에 나올 때마다 오인을 만든다.
    """
    banned = {_digits(one) for one in business_numbers}
    seen: set[str] = set()

    declared = normalise(organization.telephone) if organization else ""
    if declared:
        key = _phone_key(declared)
        if key and key not in banned:
            seen.add(key)
            yield IdentityCandidate(IdentityField.PHONE, declared, CandidateSource.DECLARED)

    for raw in _capped(_PHONE_RE.findall(text), seen, key=_phone_key, banned=banned):
        yield IdentityCandidate(IdentityField.PHONE, raw, CandidateSource.FOUND_IN_TEXT)


def _addresses(text: str, organization: EntityNode | None) -> Iterator[IdentityCandidate]:
    seen: set[str] = set()

    declared = normalise(organization.address_text) if organization else ""
    if declared:
        seen.add(declared)
        yield IdentityCandidate(IdentityField.ADDRESS, declared, CandidateSource.DECLARED)

    candidates = (
        normalise(one) for one in _ADDRESS_RE.findall(text) if _looks_like_address(one)
    )
    for raw in _capped(candidates, seen, key=lambda one: one):
        yield IdentityCandidate(IdentityField.ADDRESS, raw, CandidateSource.FOUND_IN_TEXT)


def _looks_like_address(value: str) -> bool:
    """주소 모양에 걸렸다고 다 주소는 아니다 — 아는 지역명이나 도로명+번지를 요구한다."""
    if _STREET_NUMBER_RE.search(value):
        return True
    return any(term in value for term in _LOCALITY_LOOKUP)


def _representatives(text: str) -> Iterator[IdentityCandidate]:
    """대표자 성함 후보.

    구조화 데이터에는 거의 없어 본문에서만 찾는다. 그래서 **하나도 미리 체크되지
    않는다** — ``원장`` ``소개`` 같은 말이 같은 모양으로 걸리기 때문이다.

    거르는 것은 두 겹이다: 이름이 아닌 말 목록(:data:`_NOT_A_NAME`)과 첫 글자
    성씨 검사(:data:`_SURNAMES`). 거래처 5곳 실측(2026-08-09) — 원시 후보 12개 중
    실명 3개만 남고 ``원장`` ``소개`` ``정회원`` ``약속`` ``진료`` ``전화`` 는 전부
    걸러졌다. 오검출 0건.
    """
    names: list[str] = []
    for pattern in _REPRESENTATIVE_RE:
        for hit in pattern.findall(text):
            cleaned = normalise(hit)
            if not cleaned or cleaned in _NOT_A_NAME or cleaned in names:
                continue
            if cleaned[0] not in _SURNAMES:
                continue
            names.append(cleaned)

    for one in names[:MAX_PER_FIELD]:
        yield IdentityCandidate(
            IdentityField.REPRESENTATIVE, one, CandidateSource.FOUND_IN_TEXT
        )


def _capped(
    values: Iterable[str],
    seen: set[str],
    *,
    key: Callable[[str], str | None],
    banned: frozenset[str] | set[str] = frozenset(),
) -> Iterator[str]:
    """중복과 제외 대상을 걸러 :data:`MAX_PER_FIELD` 개까지만 낸다."""
    taken = 0
    for raw in values:
        cleaned = normalise(raw)
        if not cleaned:
            continue
        identity = key(cleaned)
        if identity is None or identity in seen or identity in banned:
            continue
        seen.add(identity)
        taken += 1
        yield cleaned
        if taken >= MAX_PER_FIELD:
            return
