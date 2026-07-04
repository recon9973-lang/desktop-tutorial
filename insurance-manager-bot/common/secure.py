"""자격증명 보안 저장 + 민감정보 마스킹 (프로젝트 ①·② 공유).

원칙(§4.1, 기획안_2 §2):
- 로그인 ID/PW는 OS 보안 저장소(keyring)에만 저장. 평문 파일 금지.
- 간편비밀번호는 저장하지 않는다(항상 사용자 수동 입력).
- 주민번호는 저장·로그 금지. 필요한 순간 메모리에서만 다루고 즉시 폐기.
"""
from __future__ import annotations

import re

SERVICE = "insurance-manager-bot"

try:
    import keyring  # type: ignore
    _HAS_KEYRING = True
except Exception:  # keyring 미설치 환경 보호
    _HAS_KEYRING = False


def save_credentials(user_key: str, login_id: str, password: str) -> None:
    """로그인 ID/PW를 OS 보안 저장소에 저장. 간편비밀번호는 절대 받지 않음."""
    if not _HAS_KEYRING:
        raise RuntimeError("keyring 미설치 — 자격증명 저장 불가. 평문 저장은 허용하지 않음.")
    keyring.set_password(SERVICE, f"{user_key}::id", login_id)
    keyring.set_password(SERVICE, f"{user_key}::pw", password)


def load_credentials(user_key: str) -> tuple[str | None, str | None]:
    if not _HAS_KEYRING:
        return None, None
    return (
        keyring.get_password(SERVICE, f"{user_key}::id"),
        keyring.get_password(SERVICE, f"{user_key}::pw"),
    )


def mask_phone(phone: str) -> str:
    d = re.sub(r"\D", "", phone or "")
    if len(d) < 4:
        return "*" * len(d)
    return f"{d[:3]}****{d[-4:]}" if len(d) >= 7 else "*" * len(d)


def mask_name(name: str) -> str:
    """가운데 글자 마스킹. 홍길동 → 홍*동, 김철수영 → 김**영."""
    if not name:
        return name
    if len(name) == 2:
        return name[0] + "*"
    return name[0] + "*" * (len(name) - 2) + name[-1]
