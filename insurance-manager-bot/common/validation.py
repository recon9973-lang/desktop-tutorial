"""공통 검증 모듈 (프로젝트 ①·② 공유).

민감정보(주민등록번호)는 이 모듈 밖으로 로그를 남기지 않는다.
검증 결과만 반환하고, 원문은 호출자가 즉시 폐기하도록 설계한다.
"""
from __future__ import annotations

import re
from datetime import date

__all__ = [
    "validate_rrn",
    "rrn_birthdate",
    "mask_rrn",
    "normalize_phone",
    "validate_phone",
    "normalize_birthdate",
]

_RRN_WEIGHTS = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def validate_rrn(rrn: str) -> bool:
    """주민등록번호 형식 + 검증번호(체크섬) 확인.

    OCR/붙여넣기 오인식을 걸러내는 1차 방어선.
    13자리, 생년월일 유효성, 마지막 검증숫자 일치를 모두 확인한다.
    """
    d = _digits(rrn)
    if len(d) != 13:
        return False
    if rrn_birthdate(d) is None:
        return False
    total = sum(int(d[i]) * _RRN_WEIGHTS[i] for i in range(12))
    check = (11 - (total % 11)) % 10
    return check == int(d[12])


def rrn_birthdate(rrn: str) -> date | None:
    """주민번호 앞 7자리 + 성별코드로 생년월일 복원. 유효하지 않으면 None."""
    d = _digits(rrn)
    if len(d) < 7:
        return None
    yy, mm, dd = int(d[0:2]), int(d[2:4]), int(d[4:6])
    g = d[6]
    # 성별/세기 코드: 1,2/9,0 → 1900년대, 3,4 → 2000년대, 5,6 → 1900년대 외국인 등
    century = {
        "1": 1900, "2": 1900, "5": 1900, "6": 1900, "9": 1800, "0": 1800,
        "3": 2000, "4": 2000, "7": 2000, "8": 2000,
    }.get(g)
    if century is None:
        return None
    try:
        return date(century + yy, mm, dd)
    except ValueError:
        return None


def mask_rrn(rrn: str) -> str:
    """화면/로그 표시용 마스킹. 앞 6자리 + 성별 1자리만 노출, 나머지 마스킹.

    예) 900101-1******
    """
    d = _digits(rrn)
    if len(d) != 13:
        return "*" * len(d)
    return f"{d[0:6]}-{d[6]}{'*' * 6}"


def normalize_phone(phone: str) -> str | None:
    """휴대폰/일반전화 정규화. 실패 시 None."""
    d = _digits(phone)
    if d.startswith("02") and len(d) in (9, 10):  # 서울 지역번호
        return f"{d[0:2]}-{d[2:-4]}-{d[-4:]}"
    if len(d) == 11 and d.startswith("01"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:]}"
    if len(d) == 10 and d.startswith("0"):
        return f"{d[0:3]}-{d[3:6]}-{d[6:]}"
    return None


def validate_phone(phone: str) -> bool:
    return normalize_phone(phone) is not None


def normalize_birthdate(text: str) -> date | None:
    """'1975.07.28', '1975년 07월 28일', '19750728' 등을 date로 정규화."""
    d = _digits(text)
    if len(d) == 8:
        try:
            return date(int(d[0:4]), int(d[4:6]), int(d[6:8]))
        except ValueError:
            return None
    if len(d) == 6:  # YYMMDD → 세기 추정(50 기준)
        yy = int(d[0:2])
        year = 2000 + yy if yy <= (date.today().year % 100) else 1900 + yy
        try:
            return date(year, int(d[2:4]), int(d[4:6]))
        except ValueError:
            return None
    return None
