"""공유 플랫폼 주소를 자사 도메인으로 두면 **없는 노출이 생긴다.**

실측 2026-08-08 — 브랜드 등록 화면에서 자사 도메인 칸에
`https://blog.naver.com/momedn1` 이 입력됐다. 그 칸의 설명은 이랬다:

> 도메인은 동명 업체와 공유되지 않습니다. 답변이 이 주소를 근거로 인용하면
> **그것만으로 확정됩니다.**

`blog.naver.com` 은 네이버 블로그 **전체**가 함께 쓰는 주소다. 저장되면 AI 답변이
아무 블로그를 인용해도 "우리 업체가 인용됐다" 로 잡힌다 — 없는 노출이 생기고, 그것도
고객에게 유리한 방향이라 아무도 이의를 제기하지 않는다.

막는 것이 아무 데도 없었다. 이 시험이 그 자리다.
"""

from __future__ import annotations

import pytest

from veo.brands.domains import is_shared_host, normalise_domain, reject_shared_domains


class TestSharedHostsAreRecognised:
    @pytest.mark.parametrize(
        "value",
        [
            "https://blog.naver.com/momedn1",
            "blog.naver.com",
            "m.blog.naver.com/clinic",
            "cafe.naver.com/somegroup",
            "https://www.instagram.com/clinic",
            "someclinic.tistory.com",
            "shop.cafe24.com",
            "https://myclinic.wixsite.com/home",
        ],
    )
    def test_a_platform_address_is_refused(self, value: str) -> None:
        assert is_shared_host(value), f"{value} 는 여러 업체가 함께 쓰는 주소입니다"

    @pytest.mark.parametrize(
        "value",
        ["ondam.kr", "https://ondam.kr/about", "www.venomad.com", "chamsarang1075.com"],
    )
    def test_an_own_domain_passes(self, value: str) -> None:
        assert not is_shared_host(value)


class TestTheInputIsForgiving:
    """사람이 규칙을 외워야 하는 칸은 결국 잘못 채워진다."""

    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("https://ondam.kr/about?x=1", "ondam.kr"),
            ("HTTP://ONDAM.KR", "ondam.kr"),
            ("www.ondam.kr", "ondam.kr"),
            ("  ondam.kr  ", "ondam.kr"),
            ("", ""),
        ],
    )
    def test_a_whole_address_becomes_a_host(self, given: str, expected: str) -> None:
        assert normalise_domain(given) == expected


def test_only_the_offending_entries_come_back() -> None:
    """무엇이 문제인지 말해 줘야 고칠 수 있다. '입력을 확인하세요' 는 안내가 아니다."""
    offenders = reject_shared_domains(
        ["ondam.kr", "https://blog.naver.com/momedn1", "venomad.com"]
    )

    assert offenders == ["https://blog.naver.com/momedn1"]


def test_nothing_shared_means_nothing_to_report() -> None:
    assert reject_shared_domains(["ondam.kr", "venomad.com"]) == []
