"""전역 열쇠 하나를 모두가 쓴다 — **조직이 하나뿐이라 지금은 괜찮다.**

## 무엇이 실제 상태인가

기획서 E11 은 *"자격증명 볼트 미사용(전역 키 공유)"* 을 중간 심각도로 적어 두었다.
[실측 2026-08-10] 재보니 그림이 다르다 —

```
볼트          다 지어져 있다. 조직별 · 암호화 · 회전 · 폐기 · 검증 · 창구까지
제공자 이음매  다 있다. `SecretResolver.resolve_for_use(organization_id=...)`
런타임        `get_provider_credentials()` — 설정에서 읽는 전역 열쇠 하나
조직          **두 번째를 만들 길이 없다.** 창구는 조회 둘뿐이고 부트스트랩은 일회성
```

조직이 하나면 전역 열쇠와 조직별 열쇠는 **기능적으로 같다.** 샐 상대가 없다. 그래서
지금 배선하면 얻는 것이 없고, 모든 제공자 인증 경로를 건드리는 위험만 진다.

## 그러면 왜 시험이 있나

**두 번째 조직이 생기는 순간 조용히 사고가 된다.** 그때 A 조직의 화면에서 실행한
진단이 B 조직의 열쇠로 남의 API 한도를 먹고, 청구서가 섞인다. 그리고 그 변화는
"조직 만들기 창구 추가" 라는 평범한 커밋으로 들어온다 — 볼트를 떠올릴 이유가 없다.

이 시험이 그 자리를 지킨다. **조직을 만들 수 있게 되는 순간 실패하고, 무엇을 먼저
해야 하는지 말한다.**

같은 모양의 관문이 이미 둘 있다 — `test_queueable_matches_the_worker.py`(껍데기를
큐로 보내는 것), `test_measurement_integrity.py`(채점 경로의 반올림).
"""

from __future__ import annotations

import pathlib
import re

import pytest

pytest.importorskip("pydantic")

_API_SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "veo"

_WIRE_THE_VAULT_FIRST = (
    "조직을 만들 수 있게 되었습니다. **볼트를 먼저 배선해야 합니다** — 지금 모든 "
    "제공자는 `get_provider_credentials()` 로 전역 열쇠 하나를 읽습니다. 조직이 둘이 "
    "되면 A 의 진단이 B 의 열쇠로 남의 API 한도를 먹고 청구서가 섞입니다.\n"
    "배선할 자리: 제공자의 `SecretResolver` 이음매에 `CredentialVault` 를 꽂습니다 "
    "— 둘 다 이미 지어져 있고 부르는 사람만 없습니다."
)


def organizations_router() -> str:
    return (_API_SRC / "organizations" / "router.py").read_text(encoding="utf-8")


class TestASecondOrganizationCannotBeCreated:
    """이것이 참인 동안에만 전역 열쇠가 안전하다."""

    def test_the_organizations_router_only_reads(self) -> None:
        source = organizations_router()
        writes = re.findall(r"@router\.(post|put|patch|delete)", source)

        assert not writes, f"{_WIRE_THE_VAULT_FIRST}\n찾은 것: {sorted(set(writes))}"

    def test_bootstrap_is_still_one_shot(self) -> None:
        """*"once an organization exists, the door closes"* — 그 문이 열리면 알아야 한다."""
        source = (_API_SRC / "bootstrap.py").read_text(encoding="utf-8")

        assert "one-shot" in source, _WIRE_THE_VAULT_FIRST
        assert "BootstrapRefused" in source


class TestTheVaultIsBuiltAndWaiting:
    """배선만 안 됐다는 사실 자체를 못박는다 — 다음 사람이 처음부터 짓지 않도록."""

    def test_the_vault_exists(self) -> None:
        from veo.credentials import CredentialVault

        assert hasattr(CredentialVault, "resolve_for_use"), (
            "제공자가 기대하는 이음매 이름이다. 바뀌면 배선할 때 안 맞는다"
        )

    def test_providers_already_have_the_seam(self) -> None:
        for module in ("google", "naver"):
            source = (_API_SRC / "providers" / module / "credentials.py").read_text(
                encoding="utf-8"
            )
            assert "organization_id" in source, f"{module}: 조직별 이음매가 사라졌다"
            assert "resolve_for_use" in source


class TestWhatRuntimeActuallyUsesToday:
    def test_it_is_the_global_settings_key(self) -> None:
        """이 사실이 조용히 바뀌면 위 시험들의 전제가 무너진다.

        누군가 볼트를 배선하면 이 시험이 실패한다 — 그때는 **이 파일을 지우면 된다.**
        그것이 이 관문이 할 일을 다 한 순간이다.
        """
        source = (_API_SRC / "providers" / "google" / "credentials.py").read_text(
            encoding="utf-8"
        )

        assert "get_provider_credentials()" in source, (
            "런타임 경로가 바뀌었다. 볼트를 배선했다면 이 파일을 지우고 "
            "WORKLIST §4 에서 E11 을 끝난 것으로 옮긴다"
        )
