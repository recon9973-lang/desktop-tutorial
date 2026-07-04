"""프로젝트 ② — GA 고객정보 입력 화면 필드 자동 기입 (Playwright).

입력 대상: 이름 · 전화번호 · 주소 · 주민등록번호
원칙(기획안_2 §2, §5):
- 주민번호는 메모리에서만, 입력 직후 폐기. 로그 금지.
- HTML 셀렉터 우선. 입력 후 값 재확인(검증).
- ★ 제출은 사용자가 최종 확인한 뒤에만(자동 제출 금지, 1차).
"""
from __future__ import annotations

from dataclasses import dataclass

# TODO(캘리브레이션): 실제 고객등록/계약입력 화면 셀렉터 확정.
FIELD_SELECTORS = {
    "name": "input[name='custName']",
    "phone": "input[name='mobile']",
    "zipcode": "input[name='zipcode']",
    "address": "input[name='addr1']",
    "address_detail": "input[name='addr2']",
    "rrn_front": "input[name='juminFront']",   # 앞 6자리
    "rrn_back": "input[name='juminBack']",     # 뒤 7자리(민감)
}
SUBMIT_SELECTOR = "button:has-text('저장')"


@dataclass
class EntryData:
    name: str
    phone: str
    zipcode: str | None
    address: str | None
    address_detail: str | None
    rrn: str            # 13자리(민감) — 입력 후 즉시 폐기


class GAEntryForm:
    def __init__(self, page):
        self.page = page

    def fill(self, data: EntryData) -> None:
        p = self.page
        p.fill(FIELD_SELECTORS["name"], data.name)
        p.fill(FIELD_SELECTORS["phone"], data.phone)
        if data.zipcode:
            p.fill(FIELD_SELECTORS["zipcode"], data.zipcode)
        if data.address:
            p.fill(FIELD_SELECTORS["address"], data.address)
        if data.address_detail:
            p.fill(FIELD_SELECTORS["address_detail"], data.address_detail)
        rrn = "".join(ch for ch in data.rrn if ch.isdigit())
        p.fill(FIELD_SELECTORS["rrn_front"], rrn[:6])
        p.fill(FIELD_SELECTORS["rrn_back"], rrn[6:])

    def verify_written(self, data: EntryData) -> list[str]:
        """입력 후 화면 값 재확인(주민번호 뒷자리는 대조하지 않고 형식만)."""
        problems = []
        if self.page.input_value(FIELD_SELECTORS["name"]) != data.name:
            problems.append("이름 입력값 불일치")
        return problems

    def submit_after_human_confirm(self, confirmed: bool) -> bool:
        """★ 반드시 사용자 최종 확인(confirmed=True) 후에만 제출."""
        if not confirmed:
            return False
        self.page.click(SUBMIT_SELECTOR)
        return True
