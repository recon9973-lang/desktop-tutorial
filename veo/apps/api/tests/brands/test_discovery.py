"""홈페이지에서 읽어 낸 것은 **후보**다 — 저장이 아니다.

이 시험이 지키는 것은 하나로 요약된다: **틀릴 수 있는 값이 사람 손을 거치지 않고
들어가지 않는다.** 브랜드 식별 값 하나가 확신도를 확정선 위로 올리고, 확정된 판정은
검수를 건너뛴다. 그래서 자동으로 채우는 것과 후보로 내놓는 것은 편의의 차이가 아니라
**틀린 판정이 사람 눈에 걸리느냐 마느냐**의 차이다.

여기 쓰인 HTML 조각은 거래처 5곳에서 실제로 나온 모양을 줄인 것이다(2026-08-09).
"""

from __future__ import annotations

import pytest

from veo.brands.discovery import (
    MAX_PER_FIELD,
    CandidateSource,
    IdentityField,
    read_identity_draft,
)

JSON_LD = """
<html><head>
<meta property="og:site_name" content="더바른한의원 침산">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"MedicalClinic",
 "name":"더바른한의원 침산","telephone":"+82-53-355-0000",
 "address":{"@type":"PostalAddress","streetAddress":"옥산로 95 3층",
            "addressLocality":"북구","addressRegion":"대구광역시"}}
</script></head><body><p>대표원장 권영재 원장이 진료합니다.</p></body></html>
"""

NO_JSON_LD = """
<html><body>
  <p>코리아H병원 대표전화 1533-1077</p>
  <p>대구광역시 수성구 동대구로 31</p>
  <p>제현태 원장</p>
  <p>사업자등록번호 : 509-04-96020</p>
</body></html>
"""


def values(draft, field: IdentityField) -> list[str]:
    return [one.value for one in draft.of(field)]


class TestWhatItReads:
    def test_구조화_데이터에서_상호_전화_소재지를_읽는다(self) -> None:
        draft = read_identity_draft(JSON_LD, url="https://example.kr")

        assert values(draft, IdentityField.DISPLAY_NAME) == ["더바른한의원 침산"]
        assert "+82-53-355-0000" in values(draft, IdentityField.PHONE)
        assert any("옥산로 95" in one for one in values(draft, IdentityField.ADDRESS))

    def test_구조화_데이터가_없어도_본문에서_읽는다(self) -> None:
        draft = read_identity_draft(NO_JSON_LD, url="https://example.kr")

        assert "1533-1077" in values(draft, IdentityField.PHONE)
        assert "대구광역시 수성구 동대구로 31" in values(draft, IdentityField.ADDRESS)
        assert "제현태" in values(draft, IdentityField.REPRESENTATIVE)

    def test_대표자_성함을_읽는다(self) -> None:
        """전화번호가 없는 기사·블로그에서 이 고객을 가려내는 것은 이 값이다.

        판별기 실측: 소재지만 있으면 0.60(검수 대기), 대표자 성함이 더해지면
        0.75(확정)로 넘어간다.
        """
        draft = read_identity_draft(JSON_LD, url="https://example.kr")

        assert values(draft, IdentityField.REPRESENTATIVE) == ["권영재"]

    def test_등록한_주소에서_도메인을_가져온다(self) -> None:
        draft = read_identity_draft(NO_JSON_LD, url="https://www.example.kr/about")

        assert values(draft, IdentityField.OWN_DOMAIN) == ["www.example.kr"]

    def test_같은_상호가_두_곳에_적혀_있어도_한_번만_낸다(self) -> None:
        markup = (
            '<html><head><meta property="og:site_name" content="베놈애드">'
            '<script type="application/ld+json">'
            '{"@type":"Organization","name":"베놈애드"}</script></head><body></body></html>'
        )

        draft = read_identity_draft(markup, url="https://a.kr")

        assert values(draft, IdentityField.DISPLAY_NAME) == ["베놈애드"]


class TestWhatItRefusesToGuess:
    """실측에서 실제로 나온 오검출들. 하나씩 막는다."""

    def test_사업자등록번호를_전화번호로_내놓지_않는다(self) -> None:
        """10자리라 전화번호 자릿수 검사를 통과한다 — 앞자리로 걸러야 한다.

        들어가면 그 숫자가 답변에 보일 때마다 없는 언급이 우리 것으로 잡힌다.
        """
        draft = read_identity_draft(NO_JSON_LD, url="https://example.kr")

        phones = values(draft, IdentityField.PHONE)
        digits = ["".join(c for c in one if c.isdigit()) for one in phones]
        assert "5090496020" not in digits

    def test_문장_토막을_소재지로_내놓지_않는다(self) -> None:
        """'…변경시 반드시 사전 동의…' 가 주소 모양에 걸렸던 실측 사례."""
        markup = "<html><body><p>내용 변경시 반드시 사전 동의를 받습니다.</p></body></html>"

        draft = read_identity_draft(markup, url="https://a.kr")

        assert values(draft, IdentityField.ADDRESS) == []

    @pytest.mark.parametrize("word", ["약속", "소개", "정회원", "진료", "전화"])
    def test_이름이_아닌_말을_대표자로_내놓지_않는다(self, word: str) -> None:
        markup = f"<html><body><p>{word} 원장</p></body></html>"

        draft = read_identity_draft(markup, url="https://a.kr")

        assert values(draft, IdentityField.REPRESENTATIVE) == []

    def test_한_항목의_후보_개수를_제한한다(self) -> None:
        """목록이 길면 사람이 고르지 않고 넘긴다 — 고르게 하는 것이 이 기능의 전부다."""
        lines = "".join(f"<p>02-1234-{n:04d}</p>" for n in range(20))
        draft = read_identity_draft(f"<html><body>{lines}</body></html>", url="https://a.kr")

        assert len(draft.of(IdentityField.PHONE)) <= MAX_PER_FIELD

    def test_아무것도_못_찾으면_지어내지_않는다(self) -> None:
        draft = read_identity_draft("<html><body><p>안녕하세요</p></body></html>", url="")

        assert draft.of(IdentityField.PHONE) == ()
        assert draft.of(IdentityField.ADDRESS) == ()
        assert draft.found_nothing
        assert any("직접 입력" in note for note in draft.notes_ko)

    def test_깨진_HTML_에도_예외를_내지_않는다(self) -> None:
        """파싱 실패는 사이트에 대한 사실이지 진단의 고장이 아니다."""
        draft = read_identity_draft("<html><body><p>02-1234-5678</div></p", url="https://a.kr")

        assert "02-1234-5678" in values(draft, IdentityField.PHONE)


class TestNothingIsPreselectedUnlessTheSiteSaidIt:
    def test_사이트가_선언한_값만_미리_체크된다(self) -> None:
        draft = read_identity_draft(JSON_LD, url="https://example.kr")
        declared = [one for one in draft.candidates if one.source is CandidateSource.DECLARED]

        assert declared
        assert all(one.preselected for one in declared)

    def test_본문에서_찾은_값은_절대_미리_체크되지_않는다(self) -> None:
        """실측에서 틀린 후보가 나왔고, 미리 체크된 것은 사람이 그냥 저장한다."""
        draft = read_identity_draft(NO_JSON_LD, url="https://example.kr")
        found = [one for one in draft.candidates if one.source is CandidateSource.FOUND_IN_TEXT]

        assert found
        assert not any(one.preselected for one in found)

    def test_대표자는_언제나_사람이_고른다(self) -> None:
        """구조화 데이터에 대표자를 선언하는 사이트는 없어, 늘 본문에서 나온다."""
        draft = read_identity_draft(JSON_LD, url="https://example.kr")

        assert all(not one.preselected for one in draft.of(IdentityField.REPRESENTATIVE))

    def test_구조화_데이터가_없으면_확인하라고_말한다(self) -> None:
        draft = read_identity_draft(NO_JSON_LD, url="https://example.kr")

        assert any("확인" in note for note in draft.notes_ko)
