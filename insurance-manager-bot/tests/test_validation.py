"""검증·파싱 단위 테스트. pytest 또는 `python tests/test_validation.py`로 실행.

주의: 실제 개인 주민번호를 넣지 않는다. 체크섬 규칙 검증용 합성값만 사용.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.validation import (  # noqa: E402
    validate_rrn, mask_rrn, rrn_birthdate, normalize_phone, normalize_birthdate,
)
from common.parsing import parse_customer_text  # noqa: E402

_W = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]


def _synth_rrn(front12: str) -> str:
    c = (11 - sum(int(front12[i]) * _W[i] for i in range(12)) % 11) % 10
    return front12 + str(c)


def test_rrn_checksum():
    good = _synth_rrn("900101100000")
    assert validate_rrn(good) is True
    # 마지막 자리 훼손 → 실패
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    assert validate_rrn(bad) is False
    assert validate_rrn("12345") is False


def test_rrn_birthdate_century():
    assert rrn_birthdate(_synth_rrn("990101100000")).year == 1999
    assert rrn_birthdate(_synth_rrn("050101300000")).year == 2005


def test_mask_rrn():
    r = _synth_rrn("900101100000")
    m = mask_rrn(r)
    assert m.startswith("900101-1") and m.endswith("******")
    assert r[7:] not in m  # 뒷자리 노출 금지


def test_phone():
    assert normalize_phone("01012345678") == "010-1234-5678"
    assert normalize_phone("010-1234-5678") == "010-1234-5678"
    assert normalize_phone("021234567") == "02-123-4567"
    assert normalize_phone("123") is None


def test_birthdate():
    assert str(normalize_birthdate("1975년 07월 28일")) == "1975-07-28"
    assert str(normalize_birthdate("19750728")) == "1975-07-28"
    assert normalize_birthdate("abc") is None


def test_parse_customer_text():
    rrn = _synth_rrn("900101100000")
    msg = f"이름: 홍길동\n연락처 010-1111-2222\n주민번호 {rrn[:6]}-{rrn[6:]}\n주소: 서울특별시 강남구 테헤란로 1"
    p = parse_customer_text(msg)
    assert p.name == "홍길동"
    assert p.phone == "010-1111-2222"
    assert p.rrn == rrn
    assert "강남구" in (p.address or "")
    assert p.confidence.get("rrn", 0) > 0.9


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} passed")
