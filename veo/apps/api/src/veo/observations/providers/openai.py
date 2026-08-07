"""The OpenAI adapter, against the Responses API.

Two decisions in here are worth reading before changing anything:

* **Citations are structural or absent.** ``url_citation`` annotations are read when the
  web-search tool was attached. When it was not, the API returns no citation objects at
  all, and this adapter reports :attr:`CitationSupport.NOT_EXPOSED_BY_PROVIDER` rather
  than an empty tuple. "No citations" and "citations were never observable" are different
  facts, and only the first one may be reported as a zero in a citation rate.
* **Nothing is parsed out of prose.** A model that writes ``출처: https://example.com``
  into its answer has not cited anything the API is prepared to attest to. Promoting that
  string to a citation would manufacture the exact evidence a customer is paying VEO to
  verify.

실측으로 확인한 것 (2026-07-30, 실제 API 호출)
--------------------------------------------
요청·응답 모양은 문서와 맞았다. 한국어 답변 수신, ``model_version`` 을 응답에서 읽음
(``gpt-4o-mini-2024-07-18``), 토큰 수 수신, 가격표가 없으면 비용을 지어내지 않음.

**그 과정에서 결함이 드러났다.** 검색 모드이기만 하면 ``STRUCTURED`` 로 단정하고 있었다.
그런데 인용을 돌려주는지는 **모델마다 다르다.**

    gpt-4o      + web_search  →  url_citation annotation 2개
    gpt-4o-mini + web_search  →  annotation **0개** (검색은 실행됨: 입력 토큰 23 → 8,174)

그래서 mini 로 재면 ``citation_support=STRUCTURED`` 이면서 ``citations=()`` 가 되어
**"찾아봤지만 인용이 없었다"** 로 기록됐다. 사실은 **"이 모델은 인용을 알려주지 않는다"**
다. 앞의 것으로 기록되면 citation rate 가 0 이 되어 고객에게 "AI 가 당신을 한 번도
인용하지 않습니다" 라고 보고하게 된다 — 지어낸 값보다 나쁘다. 지어낸 줄도 모른다.

Gemini·Perplexity 어댑터는 **응답에 인용 구조가 실제로 있는지** 보고 판정하는데, OpenAI
에서는 그 방법이 통하지 않는다. ``annotations`` 키가 두 경우 모두 존재하므로(mini 는 빈
배열, 4o 는 채워짐) 응답 모양으로는 "못 하는 모델" 과 "인용할 것이 없던 답변" 을 가를
수 없다. 그래서 **모델의 능력은 선언**한다 — :data:`CITATION_CAPABLE_MODEL_PREFIXES`.

세 번째 사실 (2026-08-08 실측)
------------------------------
위 두 가지 말고 하나가 더 있었다. **도구를 붙였다고 검색이 도는 것이 아니다.**

    "임플란트 수술 후 붓기는 며칠 가나요?"  →  output=['message']
                                              입력 319 토큰 · annotation 0
    "베놈애드는 어떤 회사인가요?" (3회)     →  output=['web_search_call','message']
                                              입력 17,286 / 17,310 / 21,504 토큰

같은 모델·같은 도구인데 모델이 그때그때 정한다. 검색을 안 한 답변을 ``STRUCTURED`` +
``citations=()`` 로 적으면 **"AI 가 찾아봤지만 당신을 인용하지 않았다"** 가 된다. 사실은
"AI 가 찾아보지도 않았다" 이고, 거래처에 주는 지시가 정반대다.

그래서 :func:`_search_ran` 이 응답에서 ``web_search_call`` 을 확인한다. 위의 옛 설명은
"둘 다 web_search_call 을 남긴다" 고 적고 있었는데 **오늘 재보니 아니었다** — 검색이 안
돈 응답에는 그 항목 자체가 없다. 그때 사실이던 것이 오늘도 사실이라고 두지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar, Final

from pydantic import SecretStr

from veo.observations.providers.base import (
    AnswerSchemaError,
    CitationSupport,
    HttpAnswerProvider,
    ProviderAnswer,
    collect_urls,
    read_token_count,
    require_model_version,
)
from veo.observations.runs import RunConditions, SearchMode

__all__ = ["OPENAI_BASE_URL", "OPENAI_RESPONSES_PATH", "OpenAIAnswerProvider"]

OPENAI_BASE_URL: Final = "https://api.openai.com"
OPENAI_RESPONSES_PATH: Final = "/v1/responses"

#: The tool that makes ``url_citation`` annotations possible. Without it the response
#: carries no citation objects and none can be claimed.
_WEB_SEARCH_TOOL: Final = {"type": "web_search"}

#: 인용을 실제로 돌려주는 것이 **실측으로 확인된** 모델의 접두어.
#:
#: 여기 없는 모델로 재면 인용 지표는 0 이 아니라 **측정 불가**가 된다. 그것이 정직한
#: 답이다 — 우리가 확인하지 않은 능력을 있다고 가정하면 그 모델의 모든 답변이 "인용
#: 없음" 으로 기록되고, 고객은 자기 사이트가 한 번도 인용되지 않는다고 읽는다.
#:
#: **목록을 넓힐 때는 반드시 실제 호출로 확인한다.** 문서에 지원한다고 적혀 있는 것과
#: 그 모델이 `url_citation` annotation 을 돌려주는 것은 다른 사실이고, 실제로 달랐다.
#: 확인 방법은 `docs/operations/verifying-citation-support.md` 에 적어 두었다.
#:
#: 접두어로 맞춘다. OpenAI 는 `gpt-4o-2024-11-20` 처럼 날짜를 붙인 이름을 함께 쓰고,
#: 그것들은 같은 모델이다.
#:
#: 2026-07-30 실측 (같은 질문, `web_search` 도구 부착):
#:
#:     gpt-5         url_citation 6개   ← 확인됨
#:     gpt-4o        url_citation 2개   ← 확인됨
#:     gpt-4.1       0개                ← 못 돌려준다
#:     gpt-4o-mini   0개                ← 못 돌려준다
#:
#: `gpt-4.1` 이 못 돌려준다는 것은 문서만 보고는 알 수 없었다. 새 이름이 붙었다고 능력이
#: 따라오지 않으며, 버전이 올라갈수록 좋아진다는 가정도 성립하지 않는다.
CITATION_CAPABLE_MODEL_PREFIXES: Final[tuple[str, ...]] = ("gpt-4o", "gpt-5")

#: 위 목록에 없는 모델을 만났을 때 결과에 남길 사유.
UNVERIFIED_CITATION_MODEL_KO: Final = (
    "이 모델이 인용을 구조적으로 돌려주는지 확인되지 않았습니다. 인용 지표는 0 이 아니라 "
    "측정 불가로 남습니다 — 인용이 없었던 것과 인용을 볼 수 없었던 것은 다른 사실입니다."
)


def reports_citations(model: str) -> bool:
    """이 모델이 인용을 돌려주는 것이 확인됐는가.

    `gpt-4o-mini` 가 `gpt-4o` 접두어에 걸리지 않아야 한다 — 둘은 다른 모델이고, 그
    차이가 바로 이 함수가 존재하는 이유다. 그래서 접두어 뒤에 이어지는 문자가 날짜
    구분자(`-` 뒤 숫자)이거나 아무것도 없을 때만 같은 모델로 본다.
    """
    name = model.strip().lower()
    for prefix in CITATION_CAPABLE_MODEL_PREFIXES:
        if name == prefix:
            return True
        if name.startswith(f"{prefix}-") and name[len(prefix) + 1 :][:1].isdigit():
            return True
    return False


class OpenAIAnswerProvider(HttpAnswerProvider):
    """Asks one question of an OpenAI model, or says why it could not."""

    engine: ClassVar[str] = "OPENAI"
    base_url: ClassVar[str] = OPENAI_BASE_URL
    settings_field: ClassVar[str] = "openai_api_key"

    def _build_request(
        self, credential: SecretStr, prompt_text: str, conditions: RunConditions
    ) -> tuple[str, Mapping[str, str], Mapping[str, Any]]:
        body: dict[str, Any] = {
            "model": conditions.model,
            "input": prompt_text,
        }
        if conditions.search_mode is SearchMode.BROWSING:
            body["tools"] = [dict(_WEB_SEARCH_TOOL)]
        return (
            f"{self._base_url}{OPENAI_RESPONSES_PATH}",
            {
                "Authorization": f"Bearer {credential.get_secret_value()}",
                "Content-Type": "application/json",
            },
            body,
        )

    def _parse(
        self, payload: Mapping[str, Any], *, conditions: RunConditions
    ) -> ProviderAnswer:
        model_version = require_model_version(payload)
        text, annotations = _read_output(payload)
        if not text.strip():
            raise AnswerSchemaError("response carries no output_text")

        # 인용을 "0건" 으로 셀 수 있으려면 **세 가지가 모두** 참이어야 한다.
        #
        #   1. 우리가 검색을 켜서 요청했는가        (search_mode)
        #   2. 그 모델이 인용을 돌려주는 모델인가    (reports_citations)
        #   3. **그 호출에서 검색이 실제로 돌았는가** (_search_ran)
        #
        # 셋 중 하나라도 아니면 "인용 0건" 이 아니라 **인용을 물을 수 없는 답변**이다.
        # 하나라도 빠뜨리면 그 답변이 인용률의 분모에 들어가 0으로 세어진다.
        observable = (
            conditions.search_mode is SearchMode.BROWSING
            and reports_citations(conditions.model)
            and _search_ran(payload)
        )
        citations = _read_url_citations(annotations) if observable else ()
        support = (
            CitationSupport.STRUCTURED if observable else CitationSupport.NOT_EXPOSED_BY_PROVIDER
        )

        usage = payload.get("usage")
        return ProviderAnswer(
            text=text,
            model=conditions.model,
            model_version=model_version,
            citations=citations,
            citation_support=support,
            input_tokens=read_token_count(usage, "input_tokens", "prompt_tokens"),
            output_tokens=read_token_count(usage, "output_tokens", "completion_tokens"),
        )


def _search_ran(payload: Mapping[str, Any]) -> bool:
    """이 호출에서 웹 검색이 **실제로** 돌았는가.

    도구를 붙였다고 검색이 도는 것이 아니다. 모델이 그때그때 정한다.

    실측 2026-08-08 · gpt-4o · 같은 도구(`web_search`)를 붙인 채:

        "임플란트 수술 후 붓기는 며칠 가나요?"   output=['message']
                                                입력 319 토큰 · annotation 0
        "베놈애드는 어떤 회사인가요?" 3회 반복    output=['web_search_call','message']
                                                입력 17,286 / 17,310 / 21,504 토큰
                                                annotation 7 / 7 / 10

    앞의 것은 모델이 **자기 기억으로 답한** 경우다. 검색을 안 했으니 인용할 출처도
    없다. 그런데 고치기 전 코드는 그것을 `STRUCTURED` + `citations=()` 로 적었고,
    그것은 **"AI 가 검색해 봤지만 당신을 인용하지 않았다"** 로 읽힌다. 사실은
    "AI 가 검색조차 하지 않았다" 이며, 둘은 거래처에 정반대의 지시를 준다 — 앞은
    "경쟁사에 밀렸다", 뒤는 "이 질문은 애초에 검색으로 안 간다" 이다.

    **이 모듈 앞머리의 설명은 오늘 실측과 다르다.** 거기엔 "`annotations` 키가 두 경우
    모두 존재하고 둘 다 `web_search_call` 을 남기므로 응답 모양으로는 가를 수 없다" 고
    적혀 있다(2026-07-30 기준). 오늘 재보니 검색이 안 돈 응답에는 `web_search_call`
    자체가 **없다.** API 가 바뀌었거나 그때의 관측이 좁았다. 그때 사실이었던 것이
    오늘도 사실이라고 가정하지 않는다.

    없는 쪽으로 틀리는 것이 안전하다: 검색이 돈 것을 안 돌았다고 보면 인용이 있는
    답변 하나를 '측정 불가' 로 버릴 뿐이지만, 반대로 틀리면 없는 0을 만들어 낸다.
    """
    output = payload.get("output")
    if not isinstance(output, list):
        return False
    return any(
        isinstance(item, dict) and item.get("type") == "web_search_call" for item in output
    )


def _read_output(payload: Mapping[str, Any]) -> tuple[str, list[Any]]:
    """Concatenated ``output_text`` and every annotation attached to it."""
    output = payload.get("output")
    if not isinstance(output, list):
        raise AnswerSchemaError("response has no output array")

    parts: list[str] = []
    annotations: list[Any] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "output_text":
                continue
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
            block_annotations = block.get("annotations")
            if isinstance(block_annotations, list):
                annotations.extend(block_annotations)
    return "".join(parts), annotations


def _read_url_citations(annotations: list[Any]) -> tuple[str, ...]:
    """URLs from ``url_citation`` annotations, in the order the model produced them."""
    urls = [
        annotation.get("url")
        for annotation in annotations
        if isinstance(annotation, dict) and annotation.get("type") == "url_citation"
    ]
    return collect_urls(urls)
