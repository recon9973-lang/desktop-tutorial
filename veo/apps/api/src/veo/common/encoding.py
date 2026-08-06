"""받은 바이트를 **무엇으로 읽을 것인가**. 이 물음에 답하는 곳은 여기 하나다.

## 왜 따로 만들었나

2026-08-06 시뮬레이션에서 나왔다. `<meta charset="euc-kr">` 로 선언한 페이지를
진단했더니 제목이 ``'ѱ �����Դϴ'`` 로 읽혔고, 그 상태로 **43.3점과 지적 8건**이
나갔다. 사이트를 잰 것이 아니라 **우리 디코딩 실패를 쟀다.**

원인은 닭과 달걀이었다. ``parse_html`` 은 ``charset or "utf-8"`` 로 먼저 디코딩하고,
``<meta charset>`` 은 그 **뒤에** 읽었다. 서버가 헤더로 알려 주지 않으면 문서가 자기
입으로 밝힌 인코딩을 영원히 못 쓴다. 국내 병원 홈페이지는 오래된 제작 도구로 만든
경우가 많아 euc-kr 이 드물지 않고, 헤더 없이 meta 로만 선언한 경우가 흔하다.

## 순서

W3C/WHATWG 가 정한 순서를 그대로 따른다.

1. **BOM** — 파일이 스스로 붙인 표식. 다른 어떤 선언보다 우선한다.
2. **HTTP 헤더의 charset** — 응답과 함께 온 사실.
3. **문서 안의 선언** — ``<meta charset>`` 또는
   ``<meta http-equiv="Content-Type" content="...; charset=euc-kr">``.
4. 아무것도 없으면 utf-8.

3번을 **바이트에서** 찾는 것이 요점이다. 디코딩한 뒤에 찾으면 늦는다. 인코딩 선언은
어차피 아스키 호환 범위 안에 있어야 하므로 바이트에서 찾아도 안전하다.

## 무엇으로 읽었는지 남긴다

돌려주는 값에 인코딩 이름이 함께 온다. "우리가 무엇으로 읽었는가" 는 판정이 아니라
**측정 조건**이고, 조건을 안 남기면 나중에 결과를 되짚을 수 없다.
"""

from __future__ import annotations

import codecs
import re

__all__ = [
    "DEFAULT_ENCODING",
    "decode_html",
    "sniff_declared_charset",
]

#: 선언이 하나도 없을 때 쓰는 인코딩. 오늘의 웹에서 이것이 맞을 확률이 가장 높다.
DEFAULT_ENCODING = "utf-8"

#: 선언을 찾을 범위. HTML 명세는 처음 1024바이트 안에 두라고 한다. 실제 문서에는
#: 그보다 뒤에 두는 경우가 있어 여유를 준다 — 본문 전체를 훑을 이유는 없다.
_SNIFF_WINDOW = 4096

_META_CHARSET = re.compile(rb"""<\s*meta[^>]*?charset\s*=\s*["']?\s*([A-Za-z0-9_\-]+)""", re.I)

_BOMS: tuple[tuple[bytes, str], ...] = (
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
)


def _usable(name: str | None) -> str | None:
    """파이썬이 실제로 읽을 수 있는 인코딩 이름일 때만 돌려준다.

    사이트는 ``charset="unicode"`` 처럼 존재하지 않는 이름도 쓴다. 그것을 그대로
    믿으면 디코딩이 터지고, 터진 자리를 사이트의 결함으로 적게 된다.
    """
    if not name:
        return None
    cleaned = name.strip().strip("\"';").lower()
    if not cleaned:
        return None
    try:
        codecs.lookup(cleaned)
    except LookupError:
        return None
    return cleaned


def sniff_declared_charset(raw: bytes) -> str | None:
    """문서가 **자기 입으로** 밝힌 인코딩. 없거나 못 쓸 이름이면 ``None``.

    ``<meta charset>`` 과 옛 ``<meta http-equiv="Content-Type">`` 을 둘 다 본다 —
    정규식 하나가 두 형태를 모두 잡는다(둘 다 ``charset=`` 을 포함한다).
    """
    match = _META_CHARSET.search(raw[:_SNIFF_WINDOW])
    if match is None:
        return None
    return _usable(match.group(1).decode("ascii", errors="ignore"))


def decode_html(
    raw: bytes, *, header_charset: str | None = None, fallback: str = DEFAULT_ENCODING
) -> tuple[str, str]:
    """``(본문, 실제로 쓴 인코딩 이름)``. 절대 예외를 내지 않는다.

    ``fallback`` 은 **아무 선언도 없을 때만** 쓴다. 부르는 쪽이 기본값을 넘겨서 문서
    자신의 선언을 덮어 버리면 이 함수를 만든 이유가 사라진다.

    잘못 선언한 인코딩은 **결함이지 고장이 아니다** — 읽을 수 없는 글자는 대체
    문자로 남기고, 무엇으로 읽었는지는 두 번째 값으로 알린다.
    """
    for bom, encoding in _BOMS:
        if raw.startswith(bom):
            return raw.decode(encoding, errors="replace"), encoding

    encoding = (
        _usable(header_charset)
        or sniff_declared_charset(raw)
        or _usable(fallback)
        or DEFAULT_ENCODING
    )
    return raw.decode(encoding, errors="replace"), encoding
