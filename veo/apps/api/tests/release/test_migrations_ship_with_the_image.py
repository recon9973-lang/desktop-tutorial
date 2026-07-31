"""배포 이미지가 **스스로 DB를 최신으로 만들 수 있는가.**

## 실제로 있었던 일

배포 이미지에는 `alembic` **라이브러리**만 들어가고 마이그레이션 **파일**은 빠져 있었다.
그래서 인수인계 문서와 커밋 메시지가 반복해서 안내하던

    Railway 에서 `alembic upgrade head` 를 실행하십시오

는 **실행할 수 없는 절차**였다. 그 명령은 컨테이너 안에서 "설정 파일이 없다" 로 끝난다.
아무도 실제로 쳐 보지 않았기 때문에 몇 판이 지나도록 드러나지 않았다(0-E — 부를 수
없는 절차는 없는 절차다).

## 이 파일이 고정하는 것

세 조각이 **함께** 있어야만 배포가 스스로 완결된다. 하나만 빠져도 증상은 똑같다 —
배포는 성공했다고 뜨고, 화면은 없는 칸을 찾다가 500 을 낸다.

1. `alembic.ini` 가 이미지에 있다
2. `alembic/` 폴더(마이그레이션 본체)가 이미지에 있다
3. 배포 직전에 그것을 실행하라고 `railway.json` 이 적혀 있다

셋을 각각 검사하지 않고 한 파일에 묶은 이유는, 나중에 하나를 지우는 사람이 **왜 나머지
둘이 있는지**를 여기서 읽게 하기 위해서다(0-H).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
DOCKERFILE = REPO_ROOT / "infra" / "docker" / "api.Dockerfile"
RAILWAY = REPO_ROOT / "railway.json"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"


@pytest.fixture(scope="module")
def dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def railway() -> dict[str, object]:
    return dict(json.loads(RAILWAY.read_text(encoding="utf-8")))


def _copy_targets(dockerfile: str) -> list[str]:
    """런타임 단계의 `COPY` 원본 경로들."""
    runtime = dockerfile.split("AS runtime", 1)[-1]
    return [
        match.group(1)
        for match in re.finditer(r"^COPY\s+(?:--[^\s]+\s+)*(\S+)\s+\S+", runtime, re.MULTILINE)
    ]


class TestTheImageCarriesItsOwnMigrations:
    def test_the_alembic_config_is_in_the_image(self, dockerfile: str) -> None:
        assert "apps/api/alembic.ini" in _copy_targets(dockerfile), (
            "설정 파일이 없으면 컨테이너 안에서 `alembic` 은 무엇을 할지 모른다."
        )

    def test_the_migration_scripts_are_in_the_image(self, dockerfile: str) -> None:
        assert "apps/api/alembic" in _copy_targets(dockerfile), (
            "마이그레이션 본체가 없으면 라이브러리만 있고 옮길 내용이 없다."
        )

    def test_dockerignore_does_not_take_them_back_out(self) -> None:
        """`.dockerignore` 한 줄이면 `COPY` 는 조용히 아무것도 안 옮긴다."""
        ignored = {
            line.strip()
            for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        forbidden = {"alembic/", "**/alembic/", "apps/api/alembic/", "apps/api/alembic.ini"}
        assert not (ignored & forbidden)


class TestTheDeployRunsThemByItself:
    def test_railway_migrates_before_the_new_version_serves(
        self, railway: dict[str, object]
    ) -> None:
        """사람이 기억해서 손으로 치는 절차는 언젠가 잊힌다.

        잊었을 때의 증상이 나쁘다 — 배포는 성공으로 뜨고, 화면만 없는 칸을 찾다가
        깨진다. 원인을 앱에서 찾게 되고, 실제로는 DB 가 한 판 뒤처져 있을 뿐이다.
        """
        deploy = railway.get("deploy")
        assert isinstance(deploy, dict)
        assert deploy.get("preDeployCommand") == "alembic upgrade head"

    def test_the_healthcheck_still_guards_the_rollout(
        self, railway: dict[str, object]
    ) -> None:
        """마이그레이션이 성공해도 앱이 안 뜨면 배포는 실패여야 한다."""
        deploy = railway.get("deploy")
        assert isinstance(deploy, dict)
        assert deploy.get("healthcheckPath") == "/api/health"


class TestTheMigrationsExistToBeCopied:
    def test_there_is_at_least_one_revision(self) -> None:
        versions = REPO_ROOT / "apps" / "api" / "alembic" / "versions"
        assert list(versions.glob("*.py")), "옮길 마이그레이션이 하나도 없다"

    def test_the_config_points_at_the_folder_we_copy(self) -> None:
        """`script_location` 이 바뀌면 `COPY` 대상도 같이 바뀌어야 한다."""
        config = (REPO_ROOT / "apps" / "api" / "alembic.ini").read_text(encoding="utf-8")
        assert re.search(r"^script_location\s*=\s*alembic\s*$", config, re.MULTILINE)
