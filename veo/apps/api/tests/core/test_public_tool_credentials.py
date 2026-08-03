"""공개 도구는 자기 한도를 쓴다.

공개 진단과 거래처 진단이 **같은 키를 쓰고 있었다.** 돈은 나가지 않지만 하루 한도를
나눠 쓰므로, 방문자가 한도를 다 쓰면 다음 날 아침 거래처 진단에서 성능·키워드가
"측정 불가" 로 나온다 — 남용의 대가를 고객이 치르는 구조였다.

리미터로는 이 문제를 풀 수 없다. 리미터는 **속도**를 늦출 뿐 **한도**를 나누지 못한다.
키를 나누는 것만이 "공개 쪽이 아무리 써도 거래처는 자기 한도를 그대로 갖는다" 를 만든다.

두 가지를 함께 지킨다.

1. 전용 키가 있으면 공개 도구는 **그것만** 쓴다.
2. 전용 키가 없으면 예전처럼 공용 키로 떨어진다 — 설정하지 않은 배포가 갑자기
   "자격증명 없음" 이 되어 공개 도구가 조용히 죽으면 안 된다.
"""

from __future__ import annotations

from pydantic import SecretStr

from veo.core.settings import ProviderCredentials


def _secret(value: SecretStr | None) -> str | None:
    return None if value is None else value.get_secret_value()


def _credentials(**values: object) -> ProviderCredentials:
    """`.env` 를 읽지 않는 자격증명.

    기본 생성자는 저장소의 `.env` 를 읽는다 — 그러면 이 시험이 **개발자 컴퓨터의 키**를
    보고, CI 에서는 다르게 행동한다(0-F). 여기서 재는 것은 슬롯 사이의 규칙이지 배포의
    설정이 아니므로, 파일을 끊고 값만 넘긴다.
    """
    return ProviderCredentials(_env_file=None, **values)  # type: ignore[arg-type]


class TestDedicatedKeysAreUsedWhenPresent:
    def test_pagespeed_uses_the_public_key(self) -> None:
        credentials = _credentials(
            google_pagespeed_api_key=SecretStr("console"),
            public_google_pagespeed_api_key=SecretStr("public"),
        )

        assert _secret(credentials.for_public_tools().google_pagespeed_api_key) == "public"

    def test_searchad_uses_the_public_set(self) -> None:
        credentials = _credentials(
            naver_searchad_api_key=SecretStr("console-key"),
            naver_searchad_secret_key=SecretStr("console-secret"),
            naver_searchad_customer_id="console-id",
            public_naver_searchad_api_key=SecretStr("public-key"),
            public_naver_searchad_secret_key=SecretStr("public-secret"),
            public_naver_searchad_customer_id="public-id",
        )

        public = credentials.for_public_tools()

        assert _secret(public.naver_searchad_api_key) == "public-key"
        assert _secret(public.naver_searchad_secret_key) == "public-secret"
        assert public.naver_searchad_customer_id == "public-id"

    def test_the_console_credentials_are_untouched(self) -> None:
        """분리의 요점은 **거래처 쪽이 그대로 남는 것**이다."""
        credentials = _credentials(
            google_pagespeed_api_key=SecretStr("console"),
            public_google_pagespeed_api_key=SecretStr("public"),
        )

        credentials.for_public_tools()

        assert _secret(credentials.google_pagespeed_api_key) == "console"


class TestUnsetPublicKeysFallBack:
    def test_pagespeed_falls_back_to_the_shared_key(self) -> None:
        """설정하지 않은 배포가 갑자기 죽으면 안 된다 — 예전 동작 그대로."""
        credentials = _credentials(google_pagespeed_api_key=SecretStr("console"))

        assert _secret(credentials.for_public_tools().google_pagespeed_api_key) == "console"

    def test_a_partial_public_set_falls_back_slot_by_slot(self) -> None:
        """반쪽만 넣은 설정이 나머지를 지우면, 반쪽 자격증명으로 401 만 받게 된다."""
        credentials = _credentials(
            naver_searchad_api_key=SecretStr("console-key"),
            naver_searchad_secret_key=SecretStr("console-secret"),
            naver_searchad_customer_id="console-id",
            public_naver_searchad_api_key=SecretStr("public-key"),
        )

        public = credentials.for_public_tools()

        assert _secret(public.naver_searchad_api_key) == "public-key"
        # 나머지는 공용 그대로 — 지워 버리면 자격증명이 불완전해진다.
        assert _secret(public.naver_searchad_secret_key) == "console-secret"
        assert public.naver_searchad_customer_id == "console-id"

    def test_nothing_configured_stays_nothing(self) -> None:
        """없는 키를 있는 것처럼 만들지 않는다."""
        assert _credentials().for_public_tools().google_pagespeed_api_key is None
