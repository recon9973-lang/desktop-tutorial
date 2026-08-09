"""한글 도메인과 그 punycode 표기는 **같은 도메인**이다.

실측 2026-08-09 — 거래처 한 곳의 SEO 점수가 **40(취약)** 에 묶여 있었다. 그 사이트는
``xn--9m1bm0ji9bd0qotax68d.kr`` 로 서비스되면서 ``<link rel="canonical">`` 에는
``https://더바른한의원.kr`` 을 적어 두었다. 둘은 같은 도메인인데 문자열로 비교해서
"canonical 이 외부 도메인을 가리킨다(치명)" 로 판정했고, 명세의
``mass_cross_domain_canonical`` 상한이 걸려 다른 항목을 아무리 고쳐도 40 을 못 넘었다.

**사이트에는 아무 문제가 없었다.** 우리가 거래처에 거짓 경고를 보낼 뻔했다.

이 비교를 지나는 곳이 셋이고 셋 다 조용히 틀린다:

* canonical 의 외부 도메인 판정 (``seo.canonical.not_cross_domain`` — 상한 40)
* AI 답변 인용의 자사 도메인 대조 (``detection/citations.py``)
* ``same_site``

인용 쪽이 특히 나쁘다. 자사 도메인 인용은 **그것만으로** 확신도를 확정선 위로 올리는
신호라, 못 맞추면 실제로 인용된 노출이 검수 대기로 사라진다.
"""

from __future__ import annotations

import pytest

from veo.seo.parsing.urls import registrable_domain, same_site, to_ascii_host

HANGUL = "더바른한의원.kr"
PUNYCODE = "xn--9m1bm0ji9bd0qotax68d.kr"


class TestTheyAreTheSameDomain:
    def test_실제로_같은_도메인이다(self) -> None:
        """전제부터 확인한다 — 이것이 거짓이면 이 시험 전체가 뜻이 없다."""
        assert PUNYCODE.encode().decode("idna") == HANGUL

    def test_한글_주소를_punycode_로_맞춘다(self) -> None:
        assert to_ascii_host(HANGUL) == PUNYCODE

    def test_이미_punycode_면_그대로_둔다(self) -> None:
        assert to_ascii_host(PUNYCODE) == PUNYCODE

    def test_등록_도메인이_같게_나온다(self) -> None:
        assert registrable_domain(HANGUL) == registrable_domain(PUNYCODE)

    def test_같은_사이트로_본다(self) -> None:
        """이 한 줄이 상한 40 을 걸던 자리다."""
        assert same_site(f"https://{PUNYCODE}/", f"https://{HANGUL}/")
        assert same_site(f"https://{HANGUL}/about", f"https://{PUNYCODE}/contact")

    def test_www_가_붙어도_같다(self) -> None:
        assert same_site(f"https://www.{HANGUL}/", f"https://{PUNYCODE}/")


class TestItStillSeparatesRealStrangers:
    """오탐을 고치다가 **진짜 외부 도메인까지 같다고 하면** 더 나쁘다."""

    @pytest.mark.parametrize(
        ("left", "right"),
        [
            (f"https://{PUNYCODE}/", "https://naver.com/"),
            (f"https://{HANGUL}/", "https://다른한의원.kr/"),
            ("https://venomad.com/", "https://venomad.co.kr/"),
            ("https://ondam.kr/", "https://blog.naver.com/ondam"),
        ],
    )
    def test_다른_도메인은_여전히_다르다(self, left: str, right: str) -> None:
        assert not same_site(left, right)


class TestItNeverExplodes:
    """이상한 호스트는 사이트에 대한 사실이지 우리 쪽 고장이 아니다.

    여기서 예외가 나면 진단이 통째로 멈춘다 — 한 페이지의 이상한 링크 하나 때문에
    거래처 진단 전체가 실패하는 것이 가장 나쁜 결과다.
    """

    @pytest.mark.parametrize(
        "host",
        ["", "example..com", "a" * 70 + ".kr", "host_with_underscore.kr", "trailing.kr."],
    )
    def test_인코딩_못_해도_예외를_내지_않는다(self, host: str) -> None:
        assert isinstance(to_ascii_host(host), str)
        assert isinstance(registrable_domain(host), str)

    def test_빈_호스트는_빈_값이다(self) -> None:
        assert to_ascii_host("") == ""
        assert registrable_domain("") == ""
