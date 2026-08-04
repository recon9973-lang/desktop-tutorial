"""응답을 우리가 실제로 **읽었는가**.

이 진단기에는 "표본이 사이트 전체인가" 를 묻는 관문이 세 겹으로 있었다. 그런데 그보다
앞선 질문 — **이 응답을 우리가 실제로 읽었는가** — 는 한 번도 던지지 않았다.

2026-08-04, venomad.com 진단이 15~27점으로 나왔다. 운영 서버는 그 주소에서 HTTP 200 을
받았고 `status_ok` 는 통과했다. 그런데 본문에 title·h1·lang·viewport·charset·canonical
이 하나도 없었다. 엔진은 그것을 수집 실패로 보고하지 않고 **11개 항목을 FAIL 로 채점**
했다. 같은 주소를 다른 곳에서 받으면 그 값들이 전부 멀쩡히 있고, 같은 엔진을 로컬에서
돌리면 75.9점이 나온다.

**200 은 "서버가 답했다" 이지 "우리가 문서를 받았다" 가 아니다**(지침 0-K).

여기서 하는 판단은 사이트에 대한 것이 아니라 **우리 수집에 대한 것**이다. 그래서
문턱을 아주 낮게 잡는다 — 나쁜 페이지를 걸러 내는 것이 목적이 아니라, **아무것도 받지
못한 것을 받았다고 착각하지 않는 것**이 목적이다. 진짜로 부실한 페이지는 걸러지지 않고
채점되어야 한다. 그것이 이 제품이 파는 값이다.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["MIN_DOCUMENT_BYTES", "ReadFailure", "read_failure"]

#: 이보다 작으면 문서로 보지 않는다.
#:
#: 유효한 HTML 문서의 최소 형태(`<html><head><title>x</title></head><body>y</body></html>`)
#: 가 70바이트 남짓이다. 실제 봇 차단 페이지·빈 껍데기는 대개 그보다도 작다. 문턱을
#: 높이면 정말로 얇은 페이지를 수집 실패로 오인하게 되므로, **의심스러우면 채점하는**
#: 쪽으로 낮게 둔다.
MIN_DOCUMENT_BYTES = 200


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

    판정 순서는 확실한 것부터다 — 상태코드 → 크기 → 구조. 앞에서 걸리면 뒤는 묻지
    않는다. 뒤로 갈수록 "부실한 페이지" 와 구분이 어려워지므로, 마지막 조건은 **세
    가지가 동시에** 비었을 때만 발동한다.

    각 인자는 부르는 쪽이 이미 관측한 값이다. 이 함수는 바이트를 다시 파싱하지 않는다 —
    같은 일을 두 벌로 하면 언젠가 한쪽만 바뀐다(0-D).
    """
    if not 200 <= status < 300:
        # 2xx 가 아닌 응답의 본문은 그 페이지의 내용이 아니다(오류 페이지·차단 페이지).
        # 이 판정은 `status_ok` 검사와 별개다: 저것은 사이트의 사실이고, 이것은 "이
        # 바이트로 다른 항목을 채점해도 되는가" 이다.
        return ReadFailure(url=url, reason_ko=f"HTTP {status} 응답이라 문서를 읽지 못했습니다.")

    if body_length < MIN_DOCUMENT_BYTES:
        return ReadFailure(
            url=url,
            reason_ko=(
                f"응답 본문이 {body_length}바이트뿐이라 문서로 읽지 못했습니다. "
                "서버가 응답은 했지만 내용을 받지 못한 상태입니다."
            ),
        )

    if not has_html_root:
        return ReadFailure(
            url=url,
            reason_ko="응답에 HTML 문서 구조가 없어 읽지 못했습니다.",
        )

    # 여기까지 왔으면 크기도 구조도 있다. 그런데도 head 신호가 하나도 없고 본문 글자도
    # 없다면, 그것은 "아무것도 없는 페이지" 가 아니라 **껍데기를 받은 것**이다.
    # 셋 중 하나라도 있으면 통과시킨다 — 진짜로 부실한 페이지는 채점되어야 한다.
    if not has_any_head_signal and body_text_length == 0:
        return ReadFailure(
            url=url,
            reason_ko=(
                "응답에 제목·설명·본문이 모두 없어 문서를 받지 못한 것으로 봅니다. "
                "봇 차단 페이지이거나 화면에서 그려지는 사이트일 수 있습니다."
            ),
        )

    return None
