"""Engine and session lifecycle."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from veo.core.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """이 프로세스의 DB 엔진. 연결 상한을 **명시해서** 만든다.

    상한을 안 적으면 SQLAlchemy 기본값(5 + 10)이 조용히 붙어 프로세스당 15개가 된다.
    그 숫자를 아무도 정하지 않았고, 그래서 "우리가 DB 를 얼마나 쓰는가" 에 답할 수
    없었다.

    답해야 하는 이유가 있다. 실측(2026-08-06): 이 DB 는 Neon 한 대이고 **최대 연결
    112개를 세 제품이 나눠 쓴다** — VEO, flowlens, 그리고 실제 영업에 쓰는 ERP.
    VEO 가 연결을 다 먹으면 ERP 가 먼저 죽는다. 테스트 중인 도구 때문에 영업이
    멈추는 순서는 만들지 않는다.

    값은 `Settings` 에 있다. 늘려야 할 때 코드가 아니라 설정을 바꾸면 되고,
    무엇보다 **그 숫자가 어딘가에 적혀 있다.**
    """
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,
        future=True,
        echo=False,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, class_=Session)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    with session_scope() as session:
        yield session
