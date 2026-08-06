"""이 프로세스가 DB 에 몇 개까지 연결하는가.

숫자를 정해 두지 않으면 SQLAlchemy 기본값(pool_size 5 + max_overflow 10)이 조용히
붙어 프로세스당 15개가 된다. 그 값을 아무도 정하지 않았고 아무도 몰랐다.

**답해야 하는 이유** — 실측(2026-08-06): 이 DB 는 Neon 한 대이고 최대 연결 112개를
세 제품이 나눠 쓴다. VEO(25MB), flowlens(59MB), 그리고 실제 영업에 쓰는 ERP(`neondb`).
그때 전체 사용은 14개였다. VEO 를 열면 사용량이 5~20배가 되고 워커도 뜬다.

VEO 가 연결을 다 먹으면 **ERP 가 먼저 죽는다.** 테스트 중인 도구 때문에 영업이 멈추는
순서는 만들지 않는다.

이 파일은 "몇 개인가" 를 코드가 아니라 **검사가** 답하게 한다.
"""

from __future__ import annotations

from veo.core.settings import get_settings

#: 공유 DB 의 최대 연결 수(실측). 우리 몫은 여기서 한참 아래여야 한다.
SHARED_CEILING = 112

#: 동시에 도는 프로세스 수를 넉넉히 잡은 값 — API 여러 대 + 워커.
#: 실제로 이만큼 뜨지 않더라도, 이만큼 떠도 남의 제품을 죽이지 않아야 한다.
PLANNED_PROCESSES = 4


def test_the_pool_size_is_declared_not_inherited() -> None:
    """기본값에 기대지 않는다. 기대면 그 숫자를 아무도 모른다."""
    settings = get_settings()

    assert settings.db_pool_size > 0
    assert settings.db_max_overflow >= 0


def test_our_share_leaves_room_for_the_other_products() -> None:
    """**이 시험이 이 파일의 이유다.**

    우리가 최대로 쓸 수 있는 연결이 공유 상한의 절반을 넘으면, 우리가 정상으로
    도는 것만으로 남의 제품이 연결을 못 얻는 상황이 만들어진다.
    """
    settings = get_settings()
    per_process = settings.db_pool_size + settings.db_max_overflow
    worst_case = per_process * PLANNED_PROCESSES

    assert worst_case <= SHARED_CEILING // 2, (
        f"프로세스당 {per_process}개 x {PLANNED_PROCESSES}대 = {worst_case}개. "
        f"공유 상한 {SHARED_CEILING}개를 ERP·flowlens 와 나눠 쓰므로 절반을 넘으면 안 된다"
    )


def test_waiting_for_a_connection_gives_up_rather_than_hanging() -> None:
    """무한정 기다리면 응답이 영원히 안 오는 화면이 된다 — 고장보다 나쁘다."""
    settings = get_settings()

    assert settings.db_pool_timeout_seconds > 0


def test_the_engine_actually_uses_the_declared_numbers() -> None:
    """설정에 적어 두고 엔진에 안 넘기면 적어 둔 적이 없는 것과 같다(0-E)."""
    from veo.db.session import get_engine

    settings = get_settings()
    get_engine.cache_clear()
    pool = get_engine().pool

    assert pool.size() == settings.db_pool_size
    # `_max_overflow` 는 공개 속성이 아니지만, **넘겼는지 확인할 다른 길이 없다.**
    # 확인하지 못하는 설정은 설정이 아니라 주석이다.
    assert pool._max_overflow == settings.db_max_overflow
