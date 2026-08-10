"""모델 인용 지원 점검기 — **못 잰 것을 잰 것처럼 적지 않는다.**

## 왜 이 도구가 있나

관측 실행 화면은 모델을 고르기 전에 *"출처를 돌려줍니다"* 라고 말한다. 그 문장은
약속이고, 약속은 재고 나서 해야 한다. 그리고 **문서를 믿으면 안 된다** —
`gpt-4.1` 은 이름만 보면 `gpt-4o` 보다 새것인데 출처를 못 돌려준다
(`docs/operations/verifying-citation-support.md`).

## 이 시험이 지키는 것

점검기가 내는 판정은 **네 갈래**여야 한다. 셋으로 접으면 거짓이 섞인다 —

```
출처를 돌려줌                    화면에 citesSources=true
출처를 돌려주지 않음              화면에 citesSources=false
출처 칸은 있는데 이번엔 없었음     아직 모른다. 다시 재야 한다
못 쟀음 (사유와 함께)             화면에 **아무것도 올리지 않는다**
```

마지막 둘을 "돌려주지 않음" 으로 접는 것이 이 파일이 막는 것이다.

[실측 2026-08-10] 이 도구로 `gpt-5` 를 재니 출처 6개 — 2026-07-30 기록과 같다.
그때 제한 시간 60초로는 **시간 초과로 못 쟀고**, 240초로 늘리니 나왔다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from veo.observations.probe import CANDIDATES, Candidate, ProbeResult
from veo.observations.providers.base import CitationSupport


def result(**kw: object) -> ProbeResult:
    base: dict[str, object] = {
        "engine": "OPENAI",
        "model": "gpt-5",
        "citations": 6,
        "support": str(CitationSupport.STRUCTURED),
        "failure": "",
        "cost_usd": 0.01,
    }
    base.update(kw)
    return ProbeResult(**base)  # type: ignore[arg-type]


class TestTheFourVerdictsStayApart:
    def test_citations_found_says_so_with_the_count(self) -> None:
        assert "출처를 돌려줌" in result().verdict_ko
        assert "6" in result().verdict_ko

    def test_a_provider_that_never_exposes_sources_says_so(self) -> None:
        verdict = result(
            citations=0, support=str(CitationSupport.NOT_EXPOSED_BY_PROVIDER)
        ).verdict_ko
        assert verdict == "출처를 돌려주지 않음"

    def test_zero_citations_with_structure_is_not_a_refusal(self) -> None:
        """**여기가 핵심이다.** 구조는 있는데 이번 답변에 인용이 없었을 뿐이다.

        이것을 "안 돌려준다" 로 적으면 잴 수 있었던 것을 영영 안 재게 된다.
        """
        verdict = result(citations=0, support=str(CitationSupport.STRUCTURED)).verdict_ko

        assert "돌려주지 않음" not in verdict
        assert "다시 재" in verdict

    def test_a_failure_never_looks_like_a_measurement(self) -> None:
        verdict = result(citations=None, failure="TIMEOUT").verdict_ko

        assert verdict.startswith("못 쟀음")
        assert "TIMEOUT" in verdict, "사유를 안 적으면 무엇을 고쳐야 할지 모른다"


class TestFailuresCarryTheirReason:
    def test_the_reason_is_part_of_the_verdict(self) -> None:
        """`CallOutcome.failure` 를 버리면 '값 없음' 만 남는다 — 실제로 한 번 그랬다."""
        verdict = result(
            citations=None, failure="PROVIDER_UNAVAILABLE · 제한 시간을 초과했습니다"
        ).verdict_ko

        assert "제한 시간" in verdict

    def test_missing_citations_is_none_not_zero(self) -> None:
        """못 부른 것과 인용 0개는 정반대다(ADR 0002)."""
        assert result(citations=None, failure="TIMEOUT").citations is None


class TestTheCandidateListIsHonest:
    def test_every_engine_we_have_a_key_for_is_listed(self) -> None:
        assert {one.engine for one in CANDIDATES} == {
            "OPENAI",
            "ANTHROPIC",
            "GOOGLE_GEMINI",
            "PERPLEXITY",
        }

    def test_a_candidate_names_one_model(self) -> None:
        """엔진마다 모델이 다르므로 엔진 이름만으로는 잴 수 없다."""
        for one in CANDIDATES:
            assert isinstance(one, Candidate)
            assert one.model.strip()
