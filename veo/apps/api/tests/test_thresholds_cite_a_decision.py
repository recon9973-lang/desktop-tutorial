"""고객에게 나가는 판정을 가르는 **숫자는 근거 문서를 대야 한다.**

## 왜 이 시험이 생겼나

2026-08-08. 사장님이 물었다 — "신뢰·안전과 비교는 반드시 있어야 하고, 한 의도가 절반을
넘으면 안 됩니다. 이 주장은 어디서 나온거지?"

나는 그 규칙이 참인 것은 코드로 확인했지만, **왜 그 숫자인지를 지어내서 설명했다.**
"질문 3개로는 균형을 맞출 수 없다" 고 적었는데 실제로 재보니 맞출 수 있었다. 걸리는
것은 개수 하나뿐이었다. 참인 사실 뒤에 거짓 이유를 붙인 것이고, **사실이 맞아서 아무
검사에도 안 걸렸다.**

근거는 실제로 있었다 — `docs/adr/0015-prompt-sets-are-audited-artefacts.md`. 내가 그것을
찾아보지 않았을 뿐이다. 찾아보게 만드는 것이 이 시험이다.

## 무엇을 강제하나

아래 목록의 상수마다 **같은 파일 안에** 실재하는 ADR 파일 이름이 적혀 있어야 한다.
새 임계값을 추가하면서 근거를 안 적으면 이 시험이 막는다.

## 무엇을 강제하지 못하나

**적힌 ADR 이 그 숫자를 실제로 정당화하는지는 못 본다.** 사람이 읽어야 한다. 이 시험이
막는 것은 "근거를 아예 안 찾아본 것" 하나다 — 그것이 2026-08-08 에 실제로 일어난 일이다.

그리고 ADR 0015 자체도 **왜 5이고 왜 50%인지는 적지 않았다.** 이 시험은 그 빈칸을
메우지 않는다. 다만 빈칸이 어디 있는지를 가리킨다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "adr").is_dir():
            return parent
    raise AssertionError("docs/adr 를 찾지 못했습니다")


ROOT = _repo_root()

#: 고객에게 나가는 판정을 가르는 임계값. `(파일, 상수 이름)`.
#:
#: 여기 없는 상수를 새로 만들어도 이 시험은 모른다 — 그래서 아래
#: `test_no_threshold_escapes_the_list` 가 목록 자체를 지킨다.
GOVERNED: tuple[tuple[str, str], ...] = (
    ("apps/api/src/veo/observations/prompts.py", "MIN_PROMPTS_PER_SET"),
    ("apps/api/src/veo/observations/prompts.py", "MAX_SINGLE_INTENT_SHARE"),
    ("apps/api/src/veo/observations/prompts.py", "MAX_BRAND_SUBJECT_SHARE"),
    ("apps/api/src/veo/observations/prompts.py", "REQUIRED_INTENTS"),
    ("apps/web/src/lib/prompt-sets.ts", "MIN_PROMPTS"),
    ("apps/web/src/lib/prompt-sets.ts", "MAX_SINGLE_INTENT_SHARE"),
    ("apps/web/src/lib/prompt-sets.ts", "MAX_BRAND_SUBJECT_SHARE"),
    ("apps/web/src/lib/prompt-sets.ts", "REQUIRED_INTENTS"),
)

_ADR_REFERENCE = re.compile(r"(?:ADR\s*)?(\d{4})-[a-z0-9-]+\.md|ADR\s*(\d{4})")


def _known_adrs() -> set[str]:
    return {path.name.split("-")[0] for path in (ROOT / "docs" / "adr").glob("*.md")}


@pytest.mark.parametrize(("relative", "constant"), GOVERNED)
def test_every_threshold_names_a_decision_record(relative: str, constant: str) -> None:
    """이 숫자가 어디서 왔는지 파일 안에 적혀 있어야 한다."""
    path = ROOT / relative
    assert path.is_file(), f"{relative} 가 없습니다"
    source = path.read_text(encoding="utf-8")
    assert constant in source, f"{relative} 에 {constant} 가 없습니다"

    matches = [m.group(1) or m.group(2) for m in _ADR_REFERENCE.finditer(source)]
    known = _known_adrs()
    cited = [number for number in matches if number in known]

    assert cited, (
        f"{relative} 의 {constant} 는 고객 판정을 가르는 숫자인데 근거 문서가 "
        f"적혀 있지 않습니다. docs/adr/ 의 결정 기록을 파일 안에 인용하십시오 "
        f"(예: 'ADR 0015'). 근거가 없다면 먼저 ADR 을 쓰십시오 — "
        f"이유를 지어내지 마십시오. docs/CORRECTIONS.md 7·8번 참조."
    )


def test_no_threshold_escapes_the_list() -> None:
    """목록 자체가 낡지 않게 한다.

    임계값을 새로 만들면서 위 목록에 안 넣으면 이 시험 전체가 무의미해진다. 그래서
    `MIN_`·`MAX_`·`REQUIRED_` 로 시작하는 모듈 수준 상수를 훑어 목록과 대조한다.
    """
    watched = {
        "apps/api/src/veo/observations/prompts.py": re.compile(
            r"^(MIN_[A-Z_]+|MAX_[A-Z_]+|REQUIRED_[A-Z_]+)", re.MULTILINE
        ),
        "apps/web/src/lib/prompt-sets.ts": re.compile(
            r"^export const (MIN_[A-Z_]+|MAX_[A-Z_]+|REQUIRED_[A-Z_]+)", re.MULTILINE
        ),
    }
    listed = {(relative, constant) for relative, constant in GOVERNED}

    missing: list[str] = []
    for relative, pattern in watched.items():
        source = (ROOT / relative).read_text(encoding="utf-8")
        for match in pattern.finditer(source):
            name = match.group(1)
            if (relative, name) not in listed:
                missing.append(f"{relative}:{name}")

    assert not missing, (
        "근거 확인 목록(GOVERNED)에 없는 임계값이 생겼습니다: "
        f"{sorted(missing)}. 목록에 추가하고 근거 ADR 을 파일에 인용하십시오."
    )


def test_the_corrections_log_exists_and_is_not_empty() -> None:
    """오류 대장이 사라지면 "얼마나 틀렸는지" 를 다시 셀 수 없게 된다.

    사장님 지적(2026-08-08): "니가 얼마나 실수 했는지 기억도 안남."
    누적이 남지 않으면 나아졌는지 나빠졌는지도 모른다.
    """
    log = ROOT / "docs" / "CORRECTIONS.md"

    assert log.is_file(), "docs/CORRECTIONS.md 가 없습니다"
    body = log.read_text(encoding="utf-8")
    assert "지어낸 설명" in body, "오류 분류가 사라졌습니다"
    # 표의 데이터 행. 최소한 지금까지 적은 것이 남아 있어야 한다.
    rows = [line for line in body.splitlines() if re.match(r"^\|\s*\d+\s*\|", line)]
    assert len(rows) >= 12, f"기록이 {len(rows)}건뿐입니다 — 지우지 않습니다"
