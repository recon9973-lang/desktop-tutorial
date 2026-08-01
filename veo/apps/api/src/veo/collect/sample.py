"""표본이 사이트 전체인가 — ``해당 없음`` 과 ``측정 불가`` 를 가르는 하나의 질문.

## 왜 이것이 한 곳에 있어야 하나

두 상태는 점수에서 **정반대로** 움직인다.

* ``해당 없음`` — 이 대상에 그 항목이 존재하지 않는다. 분모에서 빠진다.
* ``측정 불가`` — 우리가 재지 못했다. 분모에 남고 0점이다.

그래서 근거 없이 앞을 고르면 **덜 재는 편이 유리해진다.** 진단 도구가 만들면 안 되는
유인이고, SEO 수집기에서 실제로 그렇게 되어 있었다(1장 52.23점 → 25장 50.11점).

그때 SEO 쪽에만 고쳤다. GEO 수집기 두 곳은 같은 실수를 그대로 갖고 있었다 — 규칙이
`seo/collectors/base.py` 안에 있어서 GEO 를 쓰는 사람 눈에 띄지 않았기 때문이다.
그래서 규칙과 **문구까지** 여기로 옮긴다. 호출자는 사실 두 개만 넘긴다.

## "전부" 라고 말하려면 두 가지가 필요하다

1. 발견 크롤이 상한·예산에 걸리지 않고 가져올 주소를 다 가져왔다.
2. 그 크롤이 실제로 작동했다는 증거. 페이지를 둘 이상 가져왔다면 링크 추적이 동작한
   것이고, 한 장뿐이라면 사이트가 스스로 sitemap 으로 "페이지가 하나다" 라고 선언해
   주어야 한다.

두 번째가 필요한 이유는 메뉴를 자바스크립트로만 그리는 사이트다. 원본 HTML 에 링크가
없으니 크롤은 "더 볼 것이 없다" 고 판단하지만 실제로는 페이지가 많다. 그때 해당 없음으로
접으면 **링크를 숨긴 사이트가 유리해진다.**
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from veo.collect.contract import not_applicable_outcome, unknown_outcome
from veo.scoring import CheckOutcome


@final
@dataclass(frozen=True, slots=True)
class SampleScope:
    """이번 수집이 사이트의 전부인지 판단하는 데 필요한 사실들."""

    #: 크롤이 상한·예산이 아니라 **더 찾을 것이 없어서** 멈췄는가.
    crawl_is_exhaustive: bool
    #: 실제로 가져온 페이지 수.
    page_count: int
    #: sitemap 이 **선언한** 주소 수. 가져온 sitemap 파일 수가 아니다.
    declared_url_count: int

    @property
    def is_whole_site(self) -> bool:
        if not self.crawl_is_exhaustive:
            return False
        if self.page_count >= 2:
            return True
        return self.declared_url_count == 1


def single_page_outcome(scope: SampleScope, check_id: str, *, subject_ko: str) -> CheckOutcome:
    """페이지가 한 장뿐일 때, 페이지 간 비교 검사가 내놓아야 하는 답.

    사유에 무엇을 하면 판정되는지 함께 적는다 — "측정 불가" 만 띄우면 고장으로 읽힌다.
    """
    if scope.is_whole_site:
        return not_applicable_outcome(
            check_id,
            f"사이트 전체를 수집했고 sitemap도 페이지가 하나임을 확인해 주므로, "
            f"{subject_ko}가 성립하지 않습니다.",
        )
    if scope.crawl_is_exhaustive:
        return unknown_outcome(
            check_id,
            f"수집한 페이지가 하나뿐이어서 {subject_ko}을 판단할 수 없습니다. "
            "링크를 따라가 봤지만 다른 페이지를 찾지 못했습니다 — 메뉴가 자바스크립트로만 "
            "그려지는 경우가 흔합니다. sitemap을 두시면 한 장짜리 사이트임을 확인할 수 "
            "있고, 그때 이 항목은 배점에서 빠집니다.",
        )
    return unknown_outcome(
        check_id,
        f"수집한 페이지가 하나뿐이어서 {subject_ko}을 판단할 수 없습니다. "
        "사이트 전체 진단으로 다시 재면 판정됩니다.",
    )


def absent_in_sample_outcome(
    scope: SampleScope, check_id: str, *, absent_ko: str, subject_ko: str
) -> CheckOutcome:
    """수집한 페이지 중에 검사 대상이 하나도 없을 때의 답.

    사이트 전체를 봤다면 "이 사이트에는 그것이 없다" 가 사실이고 해당 없음이 맞다.
    일부만 봤다면 그것은 **표본에 대한 사실**일 뿐이므로 측정 불가다.
    """
    if scope.is_whole_site:
        return not_applicable_outcome(check_id, absent_ko)
    return unknown_outcome(
        check_id,
        f"수집한 페이지 중에는 {subject_ko}이 없었습니다. 다만 사이트 전체를 본 것이 "
        "아니므로 다른 페이지에 있는지는 확인하지 못했습니다. 사이트 전체 진단으로 다시 "
        "재면 판정됩니다.",
    )


def unproven_absence_outcome(
    scope: SampleScope, check_id: str, *, subject_ko: str, seen_pages: int
) -> CheckOutcome | None:
    """부재를 주장하기 직전에 묻는다 — 이 표본으로 "없다" 를 말할 수 있는가.

    위반이 **발견**됐다면 이 함수를 부를 일이 없다. 존재는 표본으로도 증명된다.
    위반이 없을 때만 갈림길이 생긴다:

    * 사이트 전체를 봤다 → ``None``. 부재가 실제로 증명됐으니 PASS 를 내면 된다.
    * 일부만 봤다 → **측정 불가.** 본 것에 없었다는 사실은 표본에 대한 사실이지
      사이트에 대한 사실이 아니다.

    2026-08-01 실측에서 이 질문이 빠진 채 도메인 8개 전부가 잘린 크롤(100장 상한)로
    "깨진 내부 링크 없음" 을 단정했다(0-A 위반). 측정 불가는 분모에 남아 0점이므로
    (ADR 0016) 이 경로에서는 **덜 재서 점수가 오르지 않는다** — 1장 52.23 > 25장
    50.11 이 나오던 바로 그 구멍이다.
    """
    if scope.is_whole_site:
        return None
    return unknown_outcome(
        check_id,
        f"수집한 {seen_pages}장 중에는 {subject_ko}이(가) 없었습니다. 다만 사이트 "
        "전체를 본 것이 아니므로 나머지 페이지는 확인하지 못했습니다. 크롤 범위를 "
        "넓혀 전체를 재면 판정됩니다.",
    )


__all__ = [
    "SampleScope",
    "absent_in_sample_outcome",
    "single_page_outcome",
    "unproven_absence_outcome",
]
