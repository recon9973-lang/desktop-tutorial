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
에서는 그 방법이 통하지 않는다. ``annotations`` 키가 두 경우 모두 존재하고(mini 는 빈
배열, 4o 는 채워짐) 둘 다 ``web_search_call`` 을 남기므로, 응답 모양으로는 "못 하는
모델" 과 "인용할 것이 없던 답변" 을 가를 수 없다. 그래서 여기서는 능력을
**선언**한다 — :data:`CITATION_CAPABLE_MODELS`.
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

        # 검색을 켰다는 것과 그 모델이 인용을 돌려준다는 것은 다른 사실이다. 둘을
        # 하나로 묶으면 인용을 못 돌려주는 모델의 답변이 "인용 0건" 으로 기록된다.
        observable = (
            conditions.search_mode is SearchMode.BROWSING
            and reports_citations(conditions.model)
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
