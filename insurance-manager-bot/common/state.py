"""처리 이력·체크포인트·동의 증빙 audit trail (프로젝트 ①·② 공유).

로그 정책(§8): 주민번호·비밀번호·연락처/주소 원문 전문은 저장하지 않는다.
저장 항목은 마스킹된 식별자와 처리 결과 위주.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from .secure import mask_name

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    project       TEXT NOT NULL,          -- 'consent' | 'entry'
    dedup_key     TEXT NOT NULL,          -- 고객식별 해시 (원문 저장 안 함)
    customer_mask TEXT,                   -- 마스킹된 고객명
    input_source  TEXT,                   -- 'manual'|'paste'|'image'
    state         TEXT,                   -- 상태머신 현재 상태
    success       INTEGER,                -- 0/1
    fail_step     TEXT,
    files         TEXT,                   -- 생성 파일명(민감정보 아님)
    consent_ref   TEXT                    -- 동의 증빙 파일 경로(암호화 보관 위치)
);
CREATE INDEX IF NOT EXISTS ix_jobs_dedup ON jobs(dedup_key);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dedup_key(name: str, birth: date | str, work_day: date | None = None) -> str:
    """고객+업무일 기반 중복 방지 키. 원문 대신 해시만 저장."""
    work_day = work_day or date.today()
    raw = f"{name}|{birth}|{work_day.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class JobStore:
    def __init__(self, db_path: str | Path = "manager_bot.sqlite3"):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def already_done(self, key: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM jobs WHERE dedup_key=? AND success=1 LIMIT 1", (key,)
        )
        return cur.fetchone() is not None

    def record(
        self,
        *,
        project: str,
        key: str,
        customer_name: str,
        input_source: str,
        state: str,
        success: bool,
        fail_step: str | None = None,
        files: list[str] | None = None,
        consent_ref: str | None = None,
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO jobs
               (created_at, project, dedup_key, customer_mask, input_source,
                state, success, fail_step, files, consent_ref)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                _now(), project, key, mask_name(customer_name), input_source,
                state, int(success), fail_step,
                ",".join(files or []), consent_ref,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def close(self) -> None:
        self.conn.close()
