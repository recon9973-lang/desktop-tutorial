"""금고가 아는 제공자와, 서버가 아는 제공자.

이 파일이 있는 이유는 **주석이 사실보다 오래 살았기 때문**이다. `providers.py` 는
"두 목록이 하나씩 맞는다" 고 적어 두었는데 2026-08-08 에 재 보니 5 대 8 이었다.
누가 `states()` 에 엔진을 더하면서 금고를 안 건드린 것이고, 아무 검사도 그것을 못 봤다.

여기서 지키는 것 둘.

**하나 — 이름은 정말 맞아야 한다.** 금고에 있는 이름이 서버가 아는 이름과 다르면
`/api/providers` 와 `/api/credentials` 가 같은 제공자를 다른 이름으로 부르게 된다.

**둘 — 빠진 것을 세어서 못박는다.** 지금 빠진 셋(Gemini·Perplexity·Anthropic)을
이름으로 적어 둔다. 그것이 채워지는 날 이 시험이 깨지고, 깨지면 문서와 주석을 같이
고치게 된다. 조용히 맞아 버리면 이번과 같은 일이 또 생긴다.
"""

from __future__ import annotations

from veo.core.settings import ProviderCredentials
from veo.credentials.providers import CredentialProvider

#: 서버는 아는데 금고에는 자리가 없는 제공자 — AI 답변 엔진 셋.
#:
#: 이들의 열쇠는 지금 배포 환경변수로만 들어간다. 금고에 넣으려면 호출 경로를 금고로
#: 돌리는 결정이 먼저다(`keywords/INTEGRATION_REQUEST.md` 요청 #5, 열림).
KNOWN_MISSING_FROM_VAULT = frozenset({"GOOGLE_GEMINI", "PERPLEXITY", "ANTHROPIC"})


def test_every_vault_provider_is_a_name_the_server_knows() -> None:
    """금고의 이름이 서버가 쓰는 이름과 같아야 한다."""
    known = set(ProviderCredentials().states())
    unknown = {str(provider) for provider in CredentialProvider} - known
    assert not unknown, (
        "금고에 서버가 모르는 제공자 이름이 있습니다 — 두 화면이 같은 제공자를 다른 "
        f"이름으로 부르게 됩니다: {sorted(unknown)}"
    )


def test_the_gap_between_the_two_lists_is_exactly_the_three_ai_engines() -> None:
    """빠진 것이 늘거나 줄면 여기서 걸린다 — 그때 문서도 같이 고친다."""
    known = set(ProviderCredentials().states())
    missing = known - {str(provider) for provider in CredentialProvider}

    assert missing == set(KNOWN_MISSING_FROM_VAULT), (
        "금고에 없는 제공자 목록이 달라졌습니다. 채웠다면 이 시험과 함께 "
        "`credentials/providers.py` 의 설명, `docs/audit/2026-08-08-server-ui-gap.md` "
        f"§A-2 를 같이 고치십시오. 지금: {sorted(missing)}"
    )
