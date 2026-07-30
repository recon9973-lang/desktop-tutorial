"""진단할 주소를 **찾는** 단계.

수집(`crawl.py`)은 주소를 받아 가져오는 일만 한다. 그 주소가 어디서 왔는지를 정하는
것이 여기다. 둘을 나눠 둔 이유는 발견이 네트워크 없이 시험 가능해야 하기 때문이다 —
사이트맵 본문과 HTML 문자열만 주면 어떤 주소가 나오는지 검사할 수 있다.

지금까지 콘솔 진단은 **직원이 주소를 하나하나 입력해야** 했다. 그래서 실제로는 한두
장만 보게 되고, 사이트를 봐야 판정되는 여덟 항목(사이트맵 두 개, 고아 페이지, 깨진
내부 링크, 중복 메타데이터, 중복 본문, 클릭 깊이, 내부 링크 밀도)이 어떤 사이트를
재도 측정 불가로 남았다. 못 잰 항목은 분모에 남은 채 0점이므로(ADR 0016), 이것은
**우리가 수집을 안 만든 탓에 모든 고객의 점수가 내려가고 있었다**는 뜻이다.

발견 경로는 셋이고, 결과에 어느 쪽으로 찾았는지 남긴다. "이 주소를 왜 봤는가" 에
답할 수 없는 수집은 나중에 검증할 수 없다.

``SEED``
    사람이 직접 지정한 주소. 진입 URL 과 직원이 추가로 넣은 주소.
``SITEMAP``
    사이트가 스스로 "이것이 내 페이지다" 라고 선언한 목록. sitemap index 는 한 단계
    따라 들어간다.
``LINK``
    진입 페이지에서 내부 링크를 따라간 것. 클릭 깊이를 재려면 이 경로가 필요하다 —
    사이트맵에만 있고 아무도 링크하지 않는 페이지가 곧 고아 페이지다.

**대상 사이트의 robots.txt 를 지킨다.** 단 진입 URL 자체는 예외다: 그 주소는 사람이
명시적으로 "이걸 진단해 달라" 고 지정한 것이고, 모든 봇을 막아 둔 사이트를 진단하는
일 자체가 VEO 가 보고해야 할 사실이기 때문이다. 발견해서 **덧붙인** 주소는 전부
robots.txt 를 따른다. 남의 서버를 도는 범위를 우리가 늘릴 때는 그쪽 규칙을 따른다.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import final
from urllib.parse import urlsplit

from veo.seo.parsing.html import parse_html
from veo.seo.parsing.robots import CRAWLER_AGENT_NAME, RobotsFile
from veo.seo.parsing.sitemap import parse_sitemap
from veo.seo.parsing.urls import normalise_url, resolve, same_site

#: 관례 경로. robots.txt 가 사이트맵을 선언하지 않았을 때만 시도한다.
CONVENTIONAL_SITEMAP_PATH = "/sitemap.xml"

#: 주소만 보고 HTML 문서가 아니라고 판단할 수 있는 확장자.
#:
#: 확장자로 형식을 단정하는 것은 원칙적으로 틀린 방법이다 — 정답은 응답의
#: `Content-Type` 이다. 그런데 그것을 알려면 **요청을 보내야** 하고, 그 요청은 대상
#: 서버의 비용이며 우리 호스트 예산을 쓴다. 실측에서 이미지 사이트맵 하나가 25장 예산
#: 가운데 9장을 이미지 내려받기로 태웠고, 그 아홉은 전부 "분석할 수 없는 형식" 으로
#: 버려졌다. 확실히 페이지가 아닌 것을 **안 보내는** 편이 정직하다.
#:
#: 목록은 좁게 유지한다. 애매한 확장자(`.php`, `.aspx`, 확장자 없음)는 전부 페이지로
#: 취급해 요청을 보낸다. 페이지를 놓치는 쪽이 이미지를 한 장 더 받는 쪽보다 나쁘다.
NON_PAGE_EXTENSIONS = frozenset(
    {
        # 이미지
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp", ".tif",
        ".tiff",
        # 문서·압축 — 페이지가 아니고, 크기가 커서 상한에 걸린다
        ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z", ".dmg", ".exe", ".apk",
        # 미디어
        ".mp4", ".webm", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg", ".m4a", ".flac",
        # 정적 자원
        ".css", ".js", ".mjs", ".map", ".woff", ".woff2", ".ttf", ".eot", ".otf",
        # 자료 형식
        ".json", ".xml", ".rss", ".atom", ".csv", ".txt",
    }
)


def looks_like_a_page(url: str) -> bool:
    """이 주소가 HTML 문서일 수 있는가.

    확실히 아닌 것만 걸러낸다. 판단이 서지 않으면 페이지로 본다.
    """
    path = urlsplit(url).path.lower()
    dot = path.rfind(".")
    slash = path.rfind("/")
    if dot < 0 or dot < slash:
        return True  # 확장자가 없다 — 대개 페이지다
    return path[dot:] not in NON_PAGE_EXTENSIONS


class DiscoverySource(StrEnum):
    """이 주소를 어떻게 찾았는가. 결과에 그대로 남는다."""

    SEED = "SEED"
    SITEMAP = "SITEMAP"
    LINK = "LINK"


@final
@dataclass(frozen=True, slots=True)
class DiscoveredUrl:
    """찾은 주소 하나와, 그것을 찾은 경위."""

    url: str
    source: DiscoverySource
    found_on: str | None = None
    """이 주소를 담고 있던 문서. 링크면 링크한 페이지, 사이트맵이면 그 사이트맵."""


def sitemap_candidates(entry_url: str, robots: RobotsFile | None) -> tuple[str, ...]:
    """어느 주소에서 사이트맵을 찾아볼 것인가.

    robots.txt 가 선언했다면 **그것만** 본다. 선언이 있는데도 관례 경로를 함께 두드리면,
    사이트가 명시적으로 알려 준 위치를 무시하고 없는 파일을 요청하는 셈이 된다.
    선언이 하나도 없을 때만 `/sitemap.xml` 을 시도한다.

    다른 호스트를 가리키는 선언은 버린다. robots.txt 는 진단 대상이 스스로 쓴 파일이고,
    그것을 그대로 따라가면 VEO 가 임의의 주소로 요청을 보내는 도구가 된다. 주소 가드가
    뒤에서 한 번 더 막지만, 애초에 보내지 않는 것이 맞다.
    """
    parts = urlsplit(entry_url)
    if not parts.scheme or not parts.netloc:
        return ()

    declared = tuple(
        normalise_url(location)
        for location in (robots.sitemaps if robots is not None else ())
        if location.strip() and same_site(entry_url, location)
    )
    if declared:
        return tuple(dict.fromkeys(declared))
    return (normalise_url(f"{parts.scheme}://{parts.netloc}{CONVENTIONAL_SITEMAP_PATH}"),)


def sitemap_index_targets(
    entry_url: str, body: str, *, limit: int
) -> tuple[str, ...]:
    """sitemap index 가 가리키는 하위 사이트맵 주소.

    index 가 아니면 빈 값이다. 한 단계만 따라간다 — index 가 index 를 가리키는 구조는
    표준이 허용하지 않고, 무한히 따라가면 사이트 하나가 우리를 임의 깊이로 끌고 갈 수
    있다.
    """
    parsed = parse_sitemap(body)
    if parsed.kind != "sitemapindex":
        return ()
    found: list[str] = []
    for location in parsed.locations:
        candidate = resolve(entry_url, location)
        if candidate is None or not same_site(entry_url, candidate):
            continue
        if candidate not in found:
            found.append(candidate)
        if len(found) >= limit:
            break
    return tuple(found)


def urls_in_sitemaps(
    entry_url: str, sitemaps: Mapping[str, str]
) -> tuple[DiscoveredUrl, ...]:
    """사이트맵이 선언한 페이지 주소. index 항목은 페이지가 아니므로 제외한다."""
    found: dict[str, DiscoveredUrl] = {}
    for sitemap_url, body in sitemaps.items():
        parsed = parse_sitemap(body)
        if parsed.kind != "urlset":
            continue
        for location in parsed.locations:
            candidate = resolve(sitemap_url, location)
            if candidate is None or not same_site(entry_url, candidate):
                continue
            found.setdefault(
                candidate,
                DiscoveredUrl(
                    url=candidate, source=DiscoverySource.SITEMAP, found_on=sitemap_url
                ),
            )
    return tuple(found.values())


def links_on_page(page_url: str, html: str) -> tuple[DiscoveredUrl, ...]:
    """같은 사이트를 가리키는 내부 링크. 문서에 나온 순서를 지킨다.

    순서를 지키는 이유는 상한에 걸려 잘릴 때다. 페이지 앞쪽의 링크가 대개 대표 메뉴이고,
    바닥글의 약관 링크보다 먼저 봐야 할 것이다.

    ``rel=nofollow`` 는 따르지 않는다. 그것은 사이트가 검색엔진에게 "이 링크로 평가를
    옮기지 말라" 고 말한 것이지 "가져가지 말라" 가 아니다. 다만 **고아 페이지 판정에서**
    링크로 세지 않는 것은 별개 문제이고, 그 판단은 수집기가 아니라 채점기가 한다.
    """
    parsed = parse_html(html)
    found: dict[str, DiscoveredUrl] = {}
    for anchor in parsed.links:
        if not anchor.href:
            continue
        candidate = resolve(page_url, anchor.href)
        if candidate is None or not same_site(page_url, candidate):
            continue
        if candidate == normalise_url(page_url):
            continue
        found.setdefault(
            candidate,
            DiscoveredUrl(url=candidate, source=DiscoverySource.LINK, found_on=page_url),
        )
    return tuple(found.values())


def allowed_by_robots(robots: RobotsFile | None, url: str) -> bool:
    """대상 사이트의 robots.txt 가 VEO 의 크롤링을 허용하는가.

    SEO 엔진은 robots.txt 를 **평가**한다. 이것은 VEO 가 그것을 **지키는** 쪽이다. 둘은
    다른 일이고, 평가한다는 이유로 지키지 않아도 되는 것은 아니다.
    """
    if robots is None:
        return True
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return robots.decide(path, user_agent=CRAWLER_AGENT_NAME).allowed


def build_frontier(
    entry_url: str,
    *,
    seeds: Sequence[str] = (),
    discovered: Iterable[DiscoveredUrl] = (),
    robots: RobotsFile | None = None,
    limit: int,
    seen: Iterable[str] = (),
) -> tuple[tuple[DiscoveredUrl, ...], tuple[str, ...]]:
    """가져올 주소 목록과, robots.txt 때문에 건너뛴 주소 목록.

    순서는 사람이 지정한 것 → 사이트가 선언한 것 → 링크로 찾은 것이다. 상한에 걸려
    잘리는 것은 언제나 뒤쪽이어야 한다: 직원이 직접 넣은 주소가 사이트맵 5,000번째
    항목 때문에 빠지면 그건 시키지 않은 일을 한 것이다.

    ``seen`` 은 이미 가져왔거나 이미 판단이 끝난 주소다. 넓이 우선으로 여러 번 부를 때
    같은 주소를 두 번 가져오지 않게 하려면 호출한 쪽이 이것을 채워 넘겨야 한다. 이
    함수는 아무것도 바꾸지 않는다 — 갱신은 호출한 쪽의 몫이다.

    진입 URL 은 언제나 제외한다. 이미 가져왔고, 그것이 없으면 진단 자체가 성립하지
    않으므로 상한을 다투는 대상이 아니다.
    """
    entry = normalise_url(entry_url)
    ordered: list[DiscoveredUrl] = [
        DiscoveredUrl(url=normalise_url(url), source=DiscoverySource.SEED)
        for url in seeds
        if url.strip()
    ]
    by_source: dict[DiscoverySource, list[DiscoveredUrl]] = {
        DiscoverySource.SITEMAP: [],
        DiscoverySource.LINK: [],
    }
    for record in discovered:
        by_source.setdefault(record.source, []).append(record)
    ordered.extend(by_source[DiscoverySource.SITEMAP])
    ordered.extend(by_source[DiscoverySource.LINK])

    frontier: list[DiscoveredUrl] = []
    blocked: list[str] = []
    visited: set[str] = {entry, *seen}

    if limit <= 0:
        return (), ()

    for record in ordered:
        if record.url in visited:
            continue
        visited.add(record.url)
        # 사람이 직접 지정한 주소는 걸러내지 않는다. 진입 URL 과 같은 이유다 —
        # 시킨 일이지 우리가 넓힌 범위가 아니다.
        if record.source is DiscoverySource.SEED:
            frontier.append(record)
            if len(frontier) >= limit:
                break
            continue
        if not looks_like_a_page(record.url):
            # 실패 목록에도 넣지 않는다. 요청을 보내지 않았으므로 실패한 것이 없고,
            # 이미지 주소를 "가져오지 못한 페이지" 로 세면 없는 결함이 된다.
            continue
        if not allowed_by_robots(robots, record.url):
            blocked.append(record.url)
            continue
        frontier.append(record)
        if len(frontier) >= limit:
            break

    return tuple(frontier), tuple(blocked)


__all__ = [
    "CONVENTIONAL_SITEMAP_PATH",
    "NON_PAGE_EXTENSIONS",
    "DiscoveredUrl",
    "DiscoverySource",
    "allowed_by_robots",
    "build_frontier",
    "links_on_page",
    "looks_like_a_page",
    "sitemap_candidates",
    "sitemap_index_targets",
    "urls_in_sitemaps",
]
