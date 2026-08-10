"""모델이 **출처를 돌려주는가** — 한 번 불러서 잰다.

## 왜 이것이 필요한가

관측 실행 화면은 모델을 고르기 전에 이렇게 말한다 —

    gpt-5 — 출처를 돌려줍니다
    gpt-4.1 — 출처를 돌려주지 않습니다

**그 문장은 약속이고, 약속은 재고 나서 해야 한다.** 안 재고 적으면 사람이 인용을 재려고
비싼 관측을 돌린 뒤에야 "측정 불가" 를 본다. 반대로 돌려주는 모델을 안 돌려준다고
적으면, 잴 수 있었던 것을 아무도 모른 채 지나간다.

**문서를 믿으면 안 된다** — `docs/operations/verifying-citation-support.md` 의 실측:

```
2026-07-30, 같은 질문 · 같은 도구
  gpt-5      url_citation 6개   확인됨
  gpt-4o                  2개   확인됨
  gpt-4.1                 0개   못 돌려준다
  gpt-4o-mini             0개   못 돌려준다
```

`gpt-4.1` 이 못 돌려준다는 것은 문서만 보고는 알 수 없었다. **새 이름이 붙었다고 능력이
따라오지 않는다.**

## 왜 이 파일이 패키지 안에 있나

열쇠는 Railway 에만 있다(노트북으로 옮기지 않는다). 그래서 **열쇠가 있는 곳에서** 돌아야
하고, 배포 이미지에는 `apps/api/src` 만 들어간다 — `scripts/` 는 안 들어간다.

    Railway → veo-platform → Console 에서:
        python -m veo.observations.probe

## 지키는 것

**실제 관측과 같은 경로로 부른다.** 어댑터를 그대로 쓴다 — 점검용 우회로를 따로 두면
그 우회로만 동작하는 상태를 못 잡는다(`usage/router.py` 의 경보 시험과 같은 이유).

**열쇠도 답변 원문도 출력하지 않는다.** 세는 것은 인용 개수와 판정뿐이다. 원문을 찍으면
그 화면을 보는 사람 모두가 그것을 갖고, 로그에도 남는다.

**돈이 나간다.** 모델 하나에 한 번씩이다. 함부로 돌지 않도록 기본은 **아무것도 안 하고
목록만 보여 주는 것**이고, 실제로 부르려면 `--run` 을 붙여야 한다.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Final, final

from veo.core.settings import get_provider_credentials
from veo.observations.providers.base import CitationSupport
from veo.observations.providers.registry import build_registry
from veo.observations.runs import AccountState, RunConditions, SearchMode
from veo.providers.naver.errors import UnknownValue

__all__ = ["CANDIDATES", "Candidate", "ProbeResult", "main", "probe_one"]

#: 출처를 요구하는 질문. 브랜드나 지역을 넣지 않는다 — 무엇을 재는지 흐려진다.
PROBE_PROMPT: Final = "오늘 서울의 주요 뉴스를 웹에서 찾아 출처와 함께 알려주세요."


@final
@dataclass(frozen=True, slots=True)
class Candidate:
    """잴 대상 하나. **이 목록이 곧 화면에 오를 후보다.**"""

    engine: str
    model: str


#: 재 볼 모델. 여기 적는 것은 "이것을 재겠다" 이지 "이것이 된다" 가 아니다 —
#: 판정은 아래 `probe_one` 이 실제 호출로 낸다.
#:
#: 모델 이름이 바뀌면 호출이 404 로 떨어지고, 그것도 **결과로 남는다**(FAILED).
#: 이름을 몰라서 못 쟀다는 사실이 "출처를 안 돌려준다" 로 둔갑하지 않게 한다.
CANDIDATES: Final[tuple[Candidate, ...]] = (
    Candidate("OPENAI", "gpt-5"),
    Candidate("ANTHROPIC", "claude-sonnet-4-5"),
    Candidate("GOOGLE_GEMINI", "gemini-2.5-flash"),
    Candidate("PERPLEXITY", "sonar"),
)


@final
@dataclass(frozen=True, slots=True)
class ProbeResult:
    engine: str
    model: str
    #: 실제로 받은 인용 개수. 못 부르면 `None` — 0 과 다르다.
    citations: int | None
    #: 어댑터가 스스로 낸 판정. 화면 문구는 여기서 나온다.
    support: str
    #: 못 불렀으면 그 사유. 성공했으면 빈 문자열.
    failure: str
    cost_usd: float | None
    #: 걸린 시간. **제한 시간을 정하려면 이 값이 있어야 한다** — 없으면 "60 은 부족하고
    #: 240 은 충분하다" 까지만 알고 그 사이는 짐작이 된다.
    latency_ms: int = 0

    @property
    def verdict_ko(self) -> str:
        if self.failure:
            return f"못 쟀음 — {self.failure}"
        if self.support == str(CitationSupport.NOT_EXPOSED_BY_PROVIDER):
            return "출처를 돌려주지 않음"
        if self.citations:
            return f"출처를 돌려줌 ({self.citations}개)"
        # 구조는 돌려주는데 이번에 인용이 없었다. **"못 돌려준다" 가 아니다.**
        return "출처 칸은 있는데 이번 답변에 인용이 없었음 — 다시 재 볼 것"


def probe_one(candidate: Candidate, *, timeout_seconds: float | None = None) -> ProbeResult:
    """한 모델을 한 번 부른다. 예외를 밖으로 내보내지 않는다.

    `timeout_seconds` 를 늘릴 수 있게 둔 이유는 **"느려서 못 쟀다" 와 "안 된다" 를
    갈라야** 하기 때문이다. 검색을 켠 호출은 기본값(60초)을 넘기도 한다. 제한에 걸린
    것을 "출처를 안 돌려준다" 로 적으면 그것이 곧 거짓이다.
    """
    registry = build_registry(
        credentials=get_provider_credentials(), timeout_seconds=timeout_seconds
    )
    try:
        provider = registry.resolve(candidate.engine)
    except Exception as exc:  # 등록되지 않은 엔진 이름
        return ProbeResult(
            candidate.engine, candidate.model, None, "", f"{type(exc).__name__}", None
        )

    conditions = RunConditions(
        engine=candidate.engine,
        model=candidate.model,
        model_version=candidate.model,
        search_mode=SearchMode.BROWSING,
        account_state=AccountState.ANONYMOUS,
        locale="ko-KR",
    )
    try:
        outcome = provider.ask(PROBE_PROMPT, conditions=conditions)
    except Exception as exc:
        # 열쇠가 없거나, 모델 이름이 틀렸거나, 한도에 걸렸다. **사유를 그대로 남긴다** —
        # 못 잰 것을 "안 돌려준다" 로 접으면 그 순간 거짓이 된다.
        return ProbeResult(
            candidate.engine, candidate.model, None, "", type(exc).__name__, None
        )

    answer = outcome.value
    if isinstance(answer, UnknownValue):
        # 호출은 돌아왔는데 값이 없다. **0 으로 접지 않는다** — `UnknownValue` 가
        # 일부러 숫자가 아닌 이유가 그것이다(`providers/naver/errors.py`).
        #
        # **사유를 반드시 함께 낸다.** `CallOutcome` 이 `failure` 를 들고 있는데 그것을
        # 버리면 "값 없음" 만 남고, 그 화면을 보는 사람은 열쇠 문제인지 모델 이름
        # 문제인지 한도 문제인지 알 수 없다 — 못 잰 이유를 모르면 고칠 수도 없다.
        failure = outcome.failure
        why = (
            f"{failure.error_code} · {failure.reason_ko}"
            if failure is not None
            else "값 없음(UNKNOWN) — 사유가 기록되지 않았다"
        )
        return ProbeResult(
            candidate.engine,
            candidate.model,
            None,
            "",
            why,
            outcome.cost_usd,
            outcome.latency_ms,
        )

    return ProbeResult(
        engine=candidate.engine,
        model=candidate.model,
        citations=len(answer.citations),
        support=str(answer.citation_support),
        failure="",
        cost_usd=outcome.cost_usd,
        latency_ms=outcome.latency_ms,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m veo.observations.probe",
        description="모델이 출처를 돌려주는지 실제로 한 번 불러서 잰다. 돈이 나간다.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="실제로 부른다. 붙이지 않으면 무엇을 잴지 보여 주기만 한다.",
    )
    parser.add_argument("--engine", default="", help="이 엔진만 (예: ANTHROPIC)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.0,
        help="한 호출의 제한 시간(초). 비우면 기본값. 느려서 못 잰 것과 안 되는 것을 가를 때 쓴다.",
    )
    args = parser.parse_args(argv)

    targets = [
        one
        for one in CANDIDATES
        if not args.engine or one.engine == args.engine.upper()
    ]
    if not targets:
        print(f"그런 엔진이 목록에 없습니다: {args.engine}")
        return 2

    if not args.run:
        print("잴 대상 (실제로 부르려면 --run 을 붙이십시오. 모델당 한 번, 돈이 나갑니다):")
        for one in targets:
            print(f"  {one.engine:<16} {one.model}")
        return 0

    print(f"{'엔진':<16} {'모델':<24} {'걸린시간':>9}  판정")
    print("-" * 88)
    for one in targets:
        result = probe_one(one, timeout_seconds=args.timeout or None)
        # 걸린 시간은 자르지 않고 그대로. 반올림하면 제한 시간을 정할 때 근거가 흐려진다.
        took = f"{result.latency_ms}ms" if result.latency_ms else "—"
        print(f"{result.engine:<16} {result.model:<24} {took:>9}  {result.verdict_ko}")
    print()
    print("화면에 올릴 값: '출처를 돌려줌' 이면 citesSources=true, '돌려주지 않음' 이면 false.")
    print("'못 쟀음' 은 **넣지 않는다** — 재지 못한 것을 잰 것처럼 적는 일이다.")
    return 0


if __name__ == "__main__":  # pragma: no cover - 사람이 손으로 돌리는 자리
    sys.exit(main())
