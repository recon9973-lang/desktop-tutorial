"""CI 워크플로가 **실제로 도는 리포지터리**의 경로를 가리키는가.

이 파일은 이미 일어난 사고를 막으려고 있다.

`veo/.github/workflows/ci.yml` 은 `git subtree push --prefix=veo` 로 밀리면
`veo-platform` 리포지터리의 **루트** 워크플로가 된다. 거기에는 `veo/` 라는 디렉터리가
없다 — `apps/`, `packages/`, `tests/` 가 바로 루트에 있다.

그런데 파일 안에는 `veo/` 를 전제한 설정이 남아 있었다.

    defaults:
      run:
        working-directory: veo

결과: **아홉 번의 푸시에서 CI 가 전부 실패했다.** 셸이 시작조차 못 했다.

    An error occurred trying to start process '/usr/bin/bash' with working
    directory '/home/runner/work/veo-platform/veo-platform/veo'.

로컬에서 `make ci-local` 이 초록이었다는 사실은 이것을 대신하지 못한다. 지침서 0-F
가 말하는 "초록불은 동작이 아니다" 가 CI 자신에게 일어난 경우이고, 0-H 는 규칙에
검사를 붙이라고 한다. 이 파일이 그 검사다.

여기서 잡는 것은 **경로의 존재**뿐이다. 워크플로가 옳은 일을 하는지는 잡지 못한다 —
그건 실제 실행이 답할 문제다. 다만 경로가 틀려서 아무것도 안 도는 상태는 여기서
멈춘다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

#: `veo/apps/api/tests/release/` → `veo/`. 이 파일이 옮겨지면 함께 고쳐야 한다.
VEO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW = VEO_ROOT / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def workflow() -> str:
    assert WORKFLOW.is_file(), f"워크플로가 없습니다: {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def _settings(text: str) -> str:
    """주석을 뺀 본문. 주석에는 `veo/` 가 사고 설명으로 남아 있어도 된다."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def test_no_step_runs_inside_a_directory_named_veo(workflow: str) -> None:
    """`working-directory: veo...` 는 배포된 리포지터리에서 존재하지 않는 경로다.

    이 한 줄이 잡 전체를 시작도 못 하게 만들었다.
    """
    offenders = [
        line.strip()
        for line in _settings(workflow).splitlines()
        if "working-directory:" in line and re.search(r"working-directory:\s*veo(/|\s*$)", line)
    ]
    assert offenders == [], f"`veo/` 를 전제한 작업 디렉터리가 남아 있습니다: {offenders}"


def test_no_configured_path_starts_with_veo(workflow: str) -> None:
    """환경변수·경로 필터에도 `veo/` 접두사가 남으면 안 된다."""
    offenders = [
        line.strip()
        for line in _settings(workflow).splitlines()
        if re.search(r"(?<![\w./-])veo/", line)
    ]
    assert offenders == [], f"`veo/` 접두사가 남아 있습니다: {offenders}"


@pytest.mark.parametrize(
    "path",
    [
        "apps/api",
        "apps/web",
        "apps/api/tests",
        "apps/api/tests/contract",
        "packages/scoring-specs",
    ],
)
def test_every_path_the_workflow_names_exists(workflow: str, path: str) -> None:
    """워크플로가 부르는 경로가 실제로 있어야 한다.

    없는 경로를 부르는 잡은 실패하거나, 더 나쁘게는 "없으니 통과" 로 빠진다.
    """
    if path not in _settings(workflow):
        pytest.skip(f"워크플로가 {path} 를 부르지 않습니다")
    assert (VEO_ROOT / path).exists(), f"워크플로가 부르는 {path} 가 없습니다"


def test_the_contract_job_points_at_the_tests_that_exist(workflow: str) -> None:
    """계약 테스트 잡이 **빈 디렉터리**를 보고 있었다.

    루트의 `tests/contract` 는 비어 있고 진짜는 `apps/api/tests/contract` 에 있다.
    빈 쪽을 보면서 "없으니 통과" 로 빠져나갔으므로, 이 잡은 한 번도 테스트를 돌린
    적이 없다.
    """
    settings = _settings(workflow)
    assert "pytest apps/api/tests/contract" in settings
    assert (VEO_ROOT / "apps/api/tests/contract").is_dir()
    assert list((VEO_ROOT / "apps/api/tests/contract").glob("test_*.py"))


def test_an_empty_test_directory_does_not_pass_the_job(workflow: str) -> None:
    """"테스트가 없으니 통과" 하는 길을 남기지 않는다.

    검증이 사라진 것은 경고가 아니라 실패다. 경고는 초록불 옆에서 읽히지 않는다.
    """
    settings = _settings(workflow)
    assert "exit 0" not in settings, "빈 디렉터리를 통과로 처리하는 길이 남아 있습니다"


def test_the_python_version_matches_what_the_package_requires(workflow: str) -> None:
    """CI 가 다른 파이썬으로 돌면 여기서 통과한 것이 저기서 깨진다."""
    pyproject = (VEO_ROOT / "apps/api/pyproject.toml").read_text(encoding="utf-8")
    required = re.search(r'requires-python\s*=\s*">=(\d+\.\d+)"', pyproject)
    assert required is not None, "requires-python 을 읽지 못했습니다"

    configured = re.search(r'PYTHON_VERSION:\s*"(\d+\.\d+)"', workflow)
    assert configured is not None, "PYTHON_VERSION 을 읽지 못했습니다"

    assert tuple(int(part) for part in configured[1].split(".")) >= tuple(
        int(part) for part in required[1].split(".")
    ), f"CI 는 {configured[1]} 인데 패키지는 {required[1]} 이상을 요구합니다"


def test_the_gate_job_waits_for_every_other_job(workflow: str) -> None:
    """`ci-passed` 가 어떤 잡을 빠뜨리면 그 잡은 빨간불이어도 머지를 막지 못한다."""
    # `jobs:` 아래만 본다. `on:` 아래의 `push:` 는 잡이 아니다.
    body = workflow[workflow.index("\njobs:") :]
    declared = {
        match.group(1)
        for match in re.finditer(r"^  ([a-z][a-z-]*):$", body, flags=re.MULTILINE)
    } - {"ci-passed"}
    needs = re.search(r"needs:\s*\[([^\]]+)\]", workflow)
    assert needs is not None, "ci-passed 의 needs 를 읽지 못했습니다"

    waited = {name.strip() for name in needs[1].split(",")}
    missing = declared - waited
    assert missing == set(), f"`ci-passed` 가 기다리지 않는 잡: {sorted(missing)}"


def test_the_workflow_runs_on_the_branch_the_deploy_gate_watches() -> None:
    """`deploy.sh` 는 후보 가지의 실행을 기다린다. 거기서 워크플로가 안 돌면 배포가 멈춘다.

    관문은 `gh run list --branch deploy-candidate` 로 초록불을 확인한 뒤에만 main 으로
    민다(`scripts/deploy.sh:66`). 그러니 `push.branches` 에서 후보 가지가 빠지면 관문은
    영원히 "실행을 찾지 못했습니다" 가 된다.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    branches = re.search(r"^    branches:\s*\[([^\]]*)\]", text, flags=re.MULTILINE)
    assert branches is not None, "push.branches 를 읽지 못했습니다"

    named = {piece.strip().strip("\"'") for piece in branches[1].split(",")}
    assert "deploy-candidate" in named, (
        "`deploy-candidate` 가 push.branches 에 없습니다 — 배포 관문이 기다릴 실행이 "
        f"만들어지지 않습니다. 지금: {sorted(named)}"
    )


def test_the_workflow_does_not_re_run_the_same_commit_on_main() -> None:
    """main 에서 같은 커밋을 다시 검사하면 알아내는 것 없이 시간만 두 배로 쓴다.

    `deploy.sh` 는 후보 가지에서 **초록불을 받은 그 SHA 를** main 으로 민다. 그래서
    main 의 실행은 같은 입력에 같은 답이다. 실측(2026-08-01~08): 실행 153건 중 서로
    다른 커밋 117개, 두 가지에서 중복 실행된 커밋 36개.

    비공개 저장소라 그 시간은 무료 한도에서 깎이고, 한도가 막히면 **배포 자체가 멈춘다** —
    v0.3.71 이 실제로 그렇게 막혔다. 그래서 이것은 취향이 아니라 관문의 가용성 문제다.

    관문은 약해지지 않는다: main 에 닿는 유일한 길이 `deploy.sh` 이고 그 앞에 검사가 있다.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    branches = re.search(r"^    branches:\s*\[([^\]]*)\]", text, flags=re.MULTILINE)
    assert branches is not None

    named = {piece.strip().strip("\"'") for piece in branches[1].split(",")}
    assert "main" not in named, (
        "`main` 이 push.branches 에 있습니다 — 후보 가지에서 이미 통과한 커밋을 다시 "
        "검사하게 됩니다. 되돌리려면 이 시험과 워크플로 주석을 함께 고치십시오."
    )


DEPLOY_SH = VEO_ROOT / "scripts" / "deploy.sh"


def test_the_daily_deploy_limit_is_checked_before_anything_is_pushed() -> None:
    """세는 일이 미는 일보다 **먼저** 와야 한다.

    밀고 나면 CI 가 돌기 시작하고 분은 이미 나간다. 그 뒤에 "상한 초과" 라고 말해 봐야
    막은 것이 아니라 알린 것이다.
    """
    text = DEPLOY_SH.read_text(encoding="utf-8")

    limit_at = text.index('-ge "$DEPLOY_LIMIT_PER_DAY"')  # 실제 비교가 일어나는 자리
    push_at = text.index("git push --force")

    assert limit_at < push_at, (
        "상한 검사가 후보 가지 push 뒤에 있습니다 — 그때는 이미 분이 나갑니다."
    )


def test_the_limit_refusal_tells_the_reader_how_to_proceed_anyway() -> None:
    """막기만 하고 길을 안 알려주면 사람은 스크립트를 고쳐서 뚫는다.

    뚫는 길을 **한 줄로** 열어 두되, 그것이 의도된 행동이 되게 한다 — 환경변수를
    직접 적어야 하므로 실수로는 넘을 수 없다.
    """
    text = DEPLOY_SH.read_text(encoding="utf-8")
    assert "VEO_DEPLOY_LIMIT_PER_DAY=99" in text, "넘는 방법이 거부 문구에 없습니다"
    assert "묶어서" in text, "묶어서 배포하라는 권유가 없습니다 — 그것이 바라는 행동이다"


def test_the_limit_expires_on_a_named_date_rather_than_living_forever() -> None:
    """9월 1일에 무료 분량이 다시 채워진다. 그 뒤로도 조용히 막고 있으면 안 된다.

    날짜가 지나면 **세지 않고 통과**시키되 한 줄로 알린다. 조용히 사라지면 왜 있었는지
    아무도 모르게 되고, 조용히 남아 있으면 이유 없이 막는다.
    """
    text = DEPLOY_SH.read_text(encoding="utf-8")
    assert 'DEPLOY_LIMIT_UNTIL="2026-09-01"' in text, "상한 만료일이 없습니다"
    assert "다시 정하십시오" in text, "만료 뒤 무엇을 해야 하는지 안 알려줍니다"


def test_the_limit_counts_failed_runs_too() -> None:
    """실패한 실행도 분을 쓴다. 성공만 세면 상한이 새 나간다."""
    text = DEPLOY_SH.read_text(encoding="utf-8")
    counting = text[text.index("today_count=") : text.index("echo \"==> [0/4] 오늘")]
    assert "conclusion" not in counting, (
        "실행을 셀 때 conclusion 으로 거르고 있습니다 — 실패도 분을 씁니다"
    )


# --------------------------------------------------------------------------- #
# 잡이 실제로 테스트를 도는가
# --------------------------------------------------------------------------- #

TESTS_ROOT = VEO_ROOT / "apps/api/tests"


def test_no_conftest_marks_the_whole_session_as_needing_postgres() -> None:
    """`pytest_collection_modifyitems` 는 **세션 전체의 항목**을 받는다.

    한 패키지의 conftest 가 조건 없이 `for item in items:` 를 돌며
    `requires_postgres` 를 붙이면, 리포지터리의 **모든** 테스트가 DB 를 요구하게 되고
    DB 없이 도는 잡은 전부 건너뛴다.

    실제로 그랬다. CI 의 `단위 테스트` 잡이 4,261건을 전부 skip 하고 초록불을 냈다 —
    **한 건도 실행하지 않은 채로.** 훅이 자기 경로를 확인하는지 여기서 본다.
    """
    offenders: list[str] = []
    for conftest in TESTS_ROOT.rglob("conftest.py"):
        source = conftest.read_text(encoding="utf-8")
        if "pytest_collection_modifyitems" not in source:
            continue
        if "requires_postgres" not in source and "requires_redis" not in source:
            continue

        body = source[source.index("def pytest_collection_modifyitems") :]
        # 훅 안에서 항목을 걸러 내는 표시. 하나도 없으면 세션 전체를 표시하는 것이다.
        filters = ("continue", "fspath", "item.path", "item.module", "fixturenames")
        if not any(token in body for token in filters):
            offenders.append(str(conftest.relative_to(VEO_ROOT)))

    assert offenders == [], (
        "세션 전체를 표시하는 conftest 훅이 있습니다. 자기 경로의 항목만 표시하도록 "
        f"고쳐 주십시오: {offenders}"
    )


def test_the_unit_job_runs_without_a_database() -> None:
    """DB 없이 도는 잡이 존재해야 한다.

    전부 DB 를 요구하게 되면 `단위 테스트` 잡은 초록불을 내면서 아무것도 검증하지
    않는다. 그 상태를 위 테스트가 막고, 이 테스트는 그런 잡이 **CI 에 실제로 있는지**
    를 본다.
    """
    workflow = WORKFLOW.read_text(encoding="utf-8")
    unit = workflow[workflow.index("  unit:") : workflow.index("  contract:")]
    settings = _settings(unit)
    assert "pytest apps/api/tests" in settings
    # 주석에서 이 이름을 언급하는 것은 괜찮다. **설정으로** 주면 안 된다.
    assert "VEO_TEST_DATABASE_URL" not in settings, (
        "단위 잡에 DB 주소를 주면 DB 없이 도는 경로가 사라집니다"
    )


def test_no_test_builds_a_connection_url_with_str() -> None:
    """`str(url)` 은 비밀번호를 `***` 로 가린다.

    그 문자열로 접속하면 비밀번호가 literal `***` 이 되어 인증에 실패한다. 로컬에서는
    소켓 접속이라 비밀번호가 없어 드러나지 않고, **비밀번호를 쓰는 CI 에서만** 터진다 —
    로컬 초록불이 구조적으로 잡을 수 없는 종류다.

    옆 데이터베이스를 가리키는 주소를 만들 때는 `render_as_string(hide_password=False)`
    를 쓴다.

    글자 찾기가 아니라 **구문 나무**로 본다. 설명하는 문장 안의 `str(url)` 까지 잡으면
    이 규칙을 문서로 남길 수가 없다.
    """
    offenders: list[str] = []
    for path in TESTS_ROOT.rglob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Name) and node.func.id == "str"):
                continue
            if not node.args:
                continue
            source = ast.dump(node.args[0])
            if "make_url" in source or "'set'" in source:
                offenders.append(f"{path.relative_to(VEO_ROOT)}:{node.lineno}")

    assert offenders == [], (
        "접속 주소를 `str()` 로 만들면 비밀번호가 가려집니다. "
        f"`render_as_string(hide_password=False)` 를 쓰십시오: {offenders}"
    )


# --------------------------------------------------------------------------- #
# 셸 스크립트는 리눅스에서 돈다
# --------------------------------------------------------------------------- #

SHELL_SCRIPTS = sorted(
    path
    for folder in ("infra",)
    for path in (VEO_ROOT / folder).rglob("*.sh")
)


def test_scripts_do_not_use_bsd_only_mktemp() -> None:
    """`mktemp -t prefix` 는 macOS 에서만 통한다.

    GNU coreutils 는 서식이 `X` 세 개 이상으로 끝나야 하고, 아니면
    `too few X's in template` 로 죽는다. 개발은 맥에서 하고 **스크립트는 리눅스
    서버에서 도므로**, 이 형태는 로컬에서 멀쩡하다가 서버에서만 터진다.

    실제로 복원 스크립트가 그랬다. CI 가 처음 돌면서 잡혔다.
    """
    offenders: list[str] = []
    for path in SHELL_SCRIPTS:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            found = re.search(r"mktemp\s+(?:-\w+\s+)*-t\s+(\S+)", stripped)
            if found and not found.group(1).rstrip("\"'").endswith("XXX"):
                offenders.append(f"{path.relative_to(VEO_ROOT)}:{number}")

    assert offenders == [], (
        "`mktemp -t 접두사` 는 리눅스에서 실패합니다. "
        f'`mktemp "${{TMPDIR:-/tmp}}/이름.XXXXXX"` 형태로 바꾸십시오: {offenders}'
    )


def test_every_shell_script_parses() -> None:
    """문법 오류가 배포 뒤에 드러나면 복구 중에 알게 된다."""
    import subprocess

    broken = [
        str(path.relative_to(VEO_ROOT))
        for path in SHELL_SCRIPTS
        if subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["/bin/bash", "-n", str(path)], capture_output=True, check=False
        ).returncode
        != 0
    ]
    assert broken == [], f"문법이 깨진 스크립트: {broken}"
