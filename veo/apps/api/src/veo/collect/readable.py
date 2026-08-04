"""응답을 우리가 실제로 **읽었는가**.

이 진단기에는 "표본이 사이트 전체인가" 를 묻는 관문이 세 겹으로 있었다. 그런데 그보다
앞선 질문 — **이 응답을 우리가 실제로 읽었는가** — 는 한 번도 던지지 않았다.

2026-08-04, venomad.com 진단이 15~27점으로 나왔다. 운영 서버는 그 주소에서 HTTP 200 을
받았고 `status_ok` 는 통과했다. 그런데 본문에 title·h1·lang·viewport·charset·canonical
이 하나도 없었다. 엔진은 그것을 수집 실패로 보고하지 않고 **11개 항목을 FAIL 로 채점**
했다. 같은 주소를 다른 곳에서 받으면 그 값들이 전부 멀쩡히 있고, 같은 엔진을 로컬에서
돌리면 75.9점이 나온다.

**200 은 "서버가 답했다" 이지 "우리가 문서를 받았다" 가 아니다**(지침 0-K).

여기서 하는 판단은 사이트에 대한 것이 아니라 **우리 수집에 대한 것**이다. 목적은 나쁜
페이지를 걸러 내는 것이 아니라, **아무것도 받지 못한 것을 받았다고 착각하지 않는 것**
이다. 진짜로 부실한 페이지는 걸러지지 않고 채점되어야 한다 — 그것이 이 제품이 파는 값이다.

**이 파일의 숫자와 조건은 실물에서 나왔다.** 두 번 지어냈다가 두 번 다 틀렸다:
200바이트 문턱은 제목 있는 80바이트 정상 문서를 버렸고(GEO 시험이 잡음), "본문 글자가
있으면 통과" 는 763바이트짜리 차단 페이지를 통과시켰다(실물이 잡음). 세 번째는 실제로
받은 763바이트를 보고 정했다.

    운영 서버 → venomad.com        763 바이트 · title·desc·canonical 없음
    한국에서   → venomad.com     59,976 바이트 · 전부 있음
    운영 서버 → 다른 거래처       248,927 바이트 · 정상

같은 서버가 다른 사이트는 정상 수신한다. 우리 서버 문제도, 요청 방식 문제도 아니고,
그 호스팅이 우리를 차단하는 것이다. 그것을 "이 사이트에 제목이 없다" 로 채점해서는
안 된다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "MAX_SHELL_BYTES",
    "MIN_DOCUMENT_BYTES",
    "ReadFailure",
    "looks_like_interstitial",
    "read_failure",
]

#: 알맹이가 하나도 없을 때, 이보다 작으면 문서로 보지 않는다.
#:
#: **실측으로 정했다.** 2026-08-04, 운영 서버가 venomad.com 에서 받은 차단 페이지는
#: 763바이트였고 title·description·canonical 이 하나도 없었다. 같은 주소를 한국에서
#: 받으면 59,976바이트에 전부 들어 있다. 같은 서버가 다른 거래처 사이트에서는
#: 248,927바이트를 정상 수신한다 — 우리 서버 문제도, 요청 방식 문제도 아니다.
#:
#: 처음에는 200바이트로 잡았다. 지어낸 숫자였고, 763바이트짜리 실물을 통과시켰다.
#: 2,048 은 실물(763)의 두 배를 넘고, 제목 하나 있는 정상 페이지(최소 형태 ~80바이트,
#: 실사용 수 KB)를 가로막지 않는 자리다.
#:
#: **크기 하나로는 절대 거르지 않는다.** head 신호가 하나도 없을 때만 본다.
MAX_SHELL_BYTES = 2048

#: (옛 이름) 아래 호환을 위해 남긴다. 새 코드는 `MAX_SHELL_BYTES` 를 쓴다.
MIN_DOCUMENT_BYTES = MAX_SHELL_BYTES


#: 스크립트만 든 작은 응답인가 — 사람이 볼 문서가 아니라 **관문 페이지**인가.
#:
#: 2026-08-05, 운영 서버(싱가포르)가 거래처 두 곳에서 받은 759·760바이트의 정체가
#: 이것이었다. 차단 페이지가 아니라 **자바스크립트 쿠키 검사**다:
#:
#:     <html><body><script src="/cupid.js"></script><script>
#:       document.cookie="CUPID="+toHex(slowAES.decrypt(...));
#:       location.href="https://venomad.com/?ckattempt=1";
#:     </script></body></html>
#:
#: 브라우저는 이 스크립트를 실행해 쿠키를 굽고 다시 요청해 진짜 페이지를 받는다. 우리
#: 크롤러는 자바스크립트를 실행하지 않으므로 여기서 멈춘다. 한국 IP 에는 이 검사가
#: 제시되지 않는다(실측) — 그래서 이것을 알아채면 한국 관측점으로 한 번 더 받아 본다.
#:
#: `read_failure` 와 묻는 것이 다르다. 저쪽은 **파싱된 신호**를 보고 "이 응답으로 채점해도
#: 되는가" 를 묻고, 이쪽은 **받은 바이트**를 보고 "다시 받아 보면 달라질 것인가" 를 묻는다.
#: 그래서 층이 다르고, 같은 파일에 둔다 — "우리가 문서를 받았는가" 는 한 곳이 답한다(0-D).
_TITLE = re.compile(rb"<\s*title[\s>]", re.IGNORECASE)
_SCRIPT = re.compile(rb"<\s*script[\s>]", re.IGNORECASE)


def looks_like_interstitial(body: bytes) -> bool:
    """이 응답이 **스크립트뿐인 관문 페이지**로 보이는가.

    셋을 모두 만족할 때만 참이다. 하나라도 어긋나면 그냥 채점한다 — 실제로 부실한
    페이지를 "관문" 으로 오인해 다시 받으러 가면, 이 제품이 팔아야 할 판정을 스스로
    버리는 것이 된다.

    1. **작다** — 관문 페이지는 실물이 759·760바이트였다. 문턱은 `MAX_SHELL_BYTES`.
    2. **스크립트가 있다** — 관문은 스크립트로 쿠키를 굽고 되돌린다.
    3. **제목이 없다** — 제목이 있으면 그것은 문서다. 스크립트가 있든 없든.

    크기만으로 거르지 않는 이유는 `read_failure` 쪽에 적어 두었다: 제목 있는
    80바이트짜리 정상 문서를 한 번 버렸다.
    """
    if len(body) >= MAX_SHELL_BYTES:
        return False
    if not _SCRIPT.search(body):
        return False
    return not _TITLE.search(body)


@dataclass(frozen=True, slots=True)
class ReadFailure:
    """문서를 읽지 못했다는 사실과 그 이유.

    사이트의 결함이 아니라 **우리 수집의 상태**다. 화면과 로그가 그렇게 읽도록
    한국어 사유를 함께 들고 다닌다.
    """

    url: str
    reason_ko: str


def read_failure(
    *,
    url: str,
    status: int,
    body_length: int,
    has_html_root: bool,
    has_any_head_signal: bool,
    body_text_length: int,
) -> ReadFailure | None:
    """이 응답을 문서로 읽었는가. 읽었으면 ``None``, 못 읽었으면 그 사유.

    순서: 상태코드 → head 신호 → 크기·본문. **head 신호가 하나라도 있으면 즉시
    통과**시킨다. 크기는 head 가 하나도 없을 때만 본다 — 크기 하나로 거르면 정상 문서를
    버리고, 크기를 아예 안 보면 차단 페이지를 통과시킨다. 둘 다 실제로 겪었다.

    각 인자는 부르는 쪽이 이미 관측한 값이다. 이 함수는 바이트를 다시 파싱하지 않는다 —
    같은 일을 두 벌로 하면 언젠가 한쪽만 바뀐다(0-D).
    """
    if not 200 <= status < 300:
        # 2xx 가 아닌 응답의 본문은 그 페이지의 내용이 아니다(오류 페이지·차단 페이지).
        # 이 판정은 `status_ok` 검사와 별개다: 저것은 사이트의 사실이고, 이것은 "이
        # 바이트로 다른 항목을 채점해도 되는가" 이다.
        return ReadFailure(url=url, reason_ko=f"HTTP {status} 응답이라 문서를 읽지 못했습니다.")

    # **head 신호가 하나라도 있으면 읽은 것이다.** 제목·설명·canonical·viewport 중
    # 하나라도 있으면 그것은 문서이고, 나머지가 나쁘면 그것이 이 제품이 팔 판정이다.
    #
    # 처음에는 크기(200바이트)를 앞세워 걸렀다가 제목 있는 80바이트 정상 문서를
    # 버렸고(GEO 시험이 잡음), 다음에는 "본문 글자가 있으면 통과" 로 풀었다가 763바이트
    # 짜리 차단 페이지를 통과시켰다(실물이 잡음). 두 번 다 실물을 안 보고 지어낸
    # 규칙이었다.
    if has_any_head_signal:
        return None

    # head 신호가 하나도 없다. 여기서부터가 판단이다.
    #
    # 본문 글자만으로는 통과시키지 않는다 — 차단 페이지에도 "잠시만 기다려 주십시오"
    # 같은 글자와 링크가 있다. 다만 **본문이 충분히 있으면** 통과시킨다: 제목 없는
    # 긴 문서는 실제로 있고, 그것은 우리가 잡아야 할 진짜 결함이다.
    if body_length >= MAX_SHELL_BYTES and body_text_length > 0:
        return None

    if body_length < MAX_SHELL_BYTES:
        return ReadFailure(
            url=url,
            reason_ko=(
                f"응답이 {body_length}바이트뿐이고 제목·설명·canonical 이 하나도 "
                "없습니다. 서버가 응답은 했지만 그 페이지를 받지 못한 상태입니다 — "
                "봇 차단 페이지일 수 있습니다."
            ),
        )

    if not has_html_root:
        return ReadFailure(
            url=url,
            reason_ko="응답에 HTML 문서 구조가 없어 읽지 못했습니다.",
        )

    # 크기도 있고 HTML 구조도 있는데 알맹이만 없다 — 껍데기를 받은 것이다.
    return ReadFailure(
        url=url,
        reason_ko=(
            "응답에 제목·설명·본문이 모두 없어 문서를 받지 못한 것으로 봅니다. "
            "봇 차단 페이지이거나 화면에서 그려지는 사이트일 수 있습니다."
        ),
    )
