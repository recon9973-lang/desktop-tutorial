"""자사 도메인으로 삼을 수 있는 것과 없는 것.

## 왜 이 파일이 생겼나

실측 2026-08-08 — 브랜드 등록 화면에서 자사 도메인 칸에
`https://blog.naver.com/momedn1` 이 입력됐다. 화면은 그 칸을 이렇게 설명하고 있었다:

> 도메인은 동명 업체와 공유되지 않습니다. 답변이 이 주소를 근거로 인용하면
> **그것만으로 확정됩니다.**

`blog.naver.com` 은 **네이버 블로그 전체가 공유하는 주소**다. 그것을 자사 도메인으로
저장하면 AI 답변이 아무 네이버 블로그를 인용해도 "우리 업체가 인용됐다" 로 잡힌다.
없는 노출을 만들어 내는 것이고, 그것도 **고객에게 유리한 방향**이라 아무도 이의를
제기하지 않는다.

막는 것이 아무 데도 없었다. 그래서 여기서 막는다.

## 무엇을 막나

**호스트가 공유 플랫폼인 것만** 막는다. 경로(`/momedn1`)가 자기 것이라도 소용없다 —
인용 대조는 도메인 단위로 하기 때문이다.

목록은 확인한 것만 넣는다. 여기 없는 공유 플랫폼은 통과한다 — 완전한 목록을 지어내는
것보다 아는 것을 막는 편이 낫다. 새로 발견하면 그때 추가한다.
"""

from __future__ import annotations

from typing import Final

#: 여러 업체가 함께 쓰는 호스트. 개인·업체마다 **경로**만 다르다.
#:
#: 병의원 거래처가 실제로 쓰는 것 위주로 확인해 넣었다(2026-08-08). 완전한 목록이
#: 아니며, 완전하게 만들 수도 없다 — 아는 것을 막는다.
SHARED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        # 네이버
        "blog.naver.com",
        "cafe.naver.com",
        "post.naver.com",
        "m.blog.naver.com",
        "m.cafe.naver.com",
        "smartstore.naver.com",
        "map.naver.com",
        "m.place.naver.com",
        "pcmap.place.naver.com",
        "in.naver.com",
        # 카카오·다음
        "blog.daum.net",
        "cafe.daum.net",
        "story.kakao.com",
        "pf.kakao.com",
        # 국내 블로그·커뮤니티
        "tistory.com",
        "blog.me",
        "modoo.at",
        "imweb.me",
        "cafe24.com",
        # 해외 플랫폼
        "blogspot.com",
        "wordpress.com",
        "wixsite.com",
        "medium.com",
        "instagram.com",
        "www.instagram.com",
        "facebook.com",
        "www.facebook.com",
        "youtube.com",
        "www.youtube.com",
        "linkedin.com",
        "www.linkedin.com",
        "threads.net",
        "x.com",
        "twitter.com",
    }
)


def normalise_domain(value: str) -> str:
    """입력에서 호스트만 남긴다. 주소를 통째로 붙여 넣어도 받는다."""
    text = value.strip().lower()
    if not text:
        return ""
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return text.removeprefix("www.") if text.count(".") > 1 else text


def is_shared_host(value: str) -> bool:
    """이 호스트를 여러 업체가 함께 쓰는가.

    `blog.naver.com/momedn1` 처럼 경로가 붙어 와도 호스트로 잘라 본다. 상위 도메인이
    목록에 있으면(`something.tistory.com`) 그것도 공유로 본다.
    """
    host = normalise_domain(value)
    if not host:
        return False
    if host in SHARED_HOSTS or f"www.{host}" in SHARED_HOSTS:
        return True
    # `xxx.tistory.com` · `xxx.cafe24.com` 처럼 하위 도메인으로 나눠 주는 곳.
    return any(host.endswith(f".{shared}") for shared in SHARED_HOSTS)


def reject_shared_domains(values: list[str]) -> list[str]:
    """공유 플랫폼 호스트만 골라 돌려준다. 비어 있으면 전부 쓸 수 있다."""
    return [one for one in values if one.strip() and is_shared_host(one)]


SHARED_DOMAIN_MESSAGE_KO: Final = (
    "여러 업체가 함께 쓰는 주소입니다: {hosts}. 이것을 자사 도메인으로 두면 **아무나 그 "
    "플랫폼에 올린 글이 인용돼도 우리 업체가 인용된 것으로 잡힙니다** — 없는 노출이 "
    "생기고, 그것도 유리한 방향이라 아무도 이의를 제기하지 않습니다.\n\n"
    "자기 도메인이 있으면 그것을 넣으십시오. 블로그만 운영한다면 도메인 칸은 비우고 "
    "상호·대표번호·소재지로 가리십시오 — 도메인이 없는 것과 남의 도메인을 우리 것이라고 "
    "하는 것은 다릅니다."
)


__all__ = [
    "SHARED_DOMAIN_MESSAGE_KO",
    "SHARED_HOSTS",
    "is_shared_host",
    "normalise_domain",
    "reject_shared_domains",
]
