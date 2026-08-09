"""측정에 AI 가 개입하지 않는다. 측정값을 다듬지 않는다.

## 왜 이 파일이 코드인가

사장님 지시(2026-08-09): *"우리는 실측, 거짓없이, 점수도 반올림이나 절삭없이 있는
그대로. 측정은 프로그램과 툴로, 여기서 AI가 개입되면 안돼! 몇 번을 말하는거야."*

**몇 번을 말해도 글은 안 지켜진다.** 사장님 `CLAUDE.md` 가 그 진단을 이미 적어 두었다 —

> "글로만 적힌 규칙은 지켜지지 않는다. … `make deploy`(CI 관문)는 한 번도 안 어겼다.
> … 차이는 하나다. 앞의 것은 글이고 뒤의 것은 관문이다. 글은 행동하는 순간에
> 개입하지 않는다. 관문은 어기려면 다른 행동을 해야 한다."

그래서 이 규칙을 문서가 아니라 **시험**으로 옮긴다. 어기려면 이 파일을 지워야 하고,
파일을 지우는 것은 커밋에 남는다.

## 무엇을 막나

1. **채점 경로에 AI 호출이 들어오는 것.** SEO·GEO 점수는 프로그램이 규칙대로 세는
   값이다. 거기에 모델이 한 번이라도 끼면 같은 입력에 다른 답이 나오고, 그때부터
   숫자는 측정이 아니라 의견이다.
2. **측정값을 다듬는 것.** 반올림·절삭·자릿수 줄이기 전부. 잰 값은 잰 값이다.
3. **상한이 걸렸을 때 잘리기 전 값을 잃는 것.** 상한은 명세의 규칙이라 적용은 하되,
   **자르기 전 값을 함께 보존**해야 무엇이 잘렸는지 사람이 볼 수 있다.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "veo"

#: 점수를 만드는 경로. 여기 안에서는 어떤 모델도 부르지 않는다.
SCORING_PACKAGES = ("seo", "geo", "scoring")

#: 이름에 이것이 들어간 모듈을 임포트하면 AI 를 부른다는 뜻으로 본다.
AI_MARKERS = ("openai", "anthropic", "google.generativeai", "litellm", "langchain")

#: 값을 다듬는 호출.
ROUNDING_CALLS = ("round",)

#: 여기까지는 부동소수점 잡음 정리로 본다. 그보다 짧게 깎으면 측정값 훼손이다.
MIN_DIGITS = 6


def python_files(package: str) -> list[pathlib.Path]:
    return sorted((SRC / package).rglob("*.py"))


def imported_names(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


class TestNoModelTouchesTheScore:
    """점수는 프로그램이 센다. 모델은 이 경로에 들어오지 않는다."""

    @pytest.mark.parametrize("package", SCORING_PACKAGES)
    def test_the_scoring_path_imports_no_ai_client(self, package: str) -> None:
        offenders: list[str] = []
        for path in python_files(package):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for name in imported_names(tree):
                lowered = name.lower()
                if any(marker in lowered for marker in AI_MARKERS):
                    offenders.append(f"{path.relative_to(SRC)} -> {name}")

        assert not offenders, (
            "채점 경로가 AI 클라이언트를 임포트한다. 점수는 프로그램이 세는 값이고, "
            "모델이 끼면 같은 입력에 다른 답이 나온다:\n  " + "\n  ".join(offenders)
        )

    @pytest.mark.parametrize("package", SCORING_PACKAGES)
    def test_the_scoring_path_calls_no_ai_provider_module(self, package: str) -> None:
        """`veo.observations.providers` 는 AI 엔진을 부르는 자리다. 채점이 쓰면 안 된다."""
        offenders = [
            f"{path.relative_to(SRC)} -> {name}"
            for path in python_files(package)
            for name in imported_names(ast.parse(path.read_text(encoding="utf-8")))
            if "observations.providers" in name
        ]

        assert not offenders, "채점 경로가 AI 엔진 모듈을 부른다:\n  " + "\n  ".join(offenders)


class TestTheScoreIsNotTidiedUp:
    """잰 값은 잰 값이다. 보기 좋게 만들려고 자릿수를 줄이지 않는다."""

    def test_the_evaluator_never_rounds_below_six_digits(self) -> None:
        """소수점 여섯 자리는 **부동소수점 잡음 정리**다. 그보다 줄이면 측정값 훼손이다.

        `round(x, 6)` 은 78.911122 를 78.911122 로 둔다 — 같은 계산이 실행마다 15번째
        자리에서 달라지는 것을 막아 **두 진단을 대조할 수 있게** 하는 장치다.
        `round(x, 2)` 나 자릿수 없는 `round(x)` 는 다르다. 그것은 사람이 보기 좋으라고
        값을 깎는 것이고, 그 순간 화면과 원자료가 다른 값을 말한다.
        """
        path = SRC / "scoring" / "evaluator.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        offenders: list[str] = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ROUNDING_CALLS
            ):
                continue
            digits = node.args[1] if len(node.args) > 1 else None
            value = digits.value if isinstance(digits, ast.Constant) else None
            if value is None or value < MIN_DIGITS:
                offenders.append(f"줄 {node.lineno} (자릿수 {value})")

        assert not offenders, (
            "scoring/evaluator.py 가 값을 여섯 자리보다 짧게 깎는다: "
            + ", ".join(offenders)
            + ". 잰 값은 그대로 싣고, 표기는 표기하는 쪽에서 정한다."
        )

    def test_the_public_payload_carries_the_score_as_measured(self) -> None:
        """응답 스키마의 점수는 실수(float)다 — 정수로 좁히면 그 자리에서 값이 깎인다."""
        from veo.public.schemas import PublicScoreBlock

        annotation = PublicScoreBlock.model_fields["score"].annotation
        assert annotation is not int, "점수를 정수로 좁히면 측정값이 깎인다"


class TestACapNeverHidesTheMeasuredValue:
    """상한은 명세의 규칙이라 적용한다. 다만 **자르기 전 값을 잃지 않는다.**"""

    def test_the_result_keeps_the_score_before_caps(self) -> None:
        from veo.scoring.models import ScoreResult

        assert "overall_score_before_caps" in ScoreResult.model_fields, (
            "상한을 걸면서 잘리기 전 값을 안 남기면, 무엇이 얼마나 잘렸는지 아무도 못 본다"
        )

    def test_a_cap_only_lowers(self) -> None:
        """상한이 점수를 올리는 일은 없어야 한다 — 올린다면 그것은 측정이 아니다."""
        source = (SRC / "scoring" / "evaluator.py").read_text(encoding="utf-8")
        assert "a cap never raises a score" in source, (
            "상한의 방향(내리기만 한다)이 코드에 적혀 있어야 한다"
        )


class TestACapSaysOnlyWhatWasLookedAt:
    """상한 사유가 **보지 않은 범위**를 단정하면 거짓이 된다.

    실측 2026-08-09 — `good-tour.kr/member/login.php` 한 장을 진단했더니 사유가
    "홈페이지 또는 사이트 전체가 색인 차단" 이었다. 그 사이트 robots.txt 는
    `Allow: /` 이고 로그인 페이지만 일부러 막은 것이다.
    """

    def test_no_published_cap_claims_the_whole_site(self) -> None:
        from veo.scoring import latest_published

        spec = latest_published("veo.seo.readiness")
        assert spec.caps, "상한이 하나도 없으면 이 시험은 아무것도 안 지킨다"
        for cap in spec.caps:
            assert "사이트 전체" not in cap.reason_ko, (
                f"{cap.id}: 평가한 URL 만 보고 사이트 전체를 단정한다 — {cap.reason_ko}"
            )
