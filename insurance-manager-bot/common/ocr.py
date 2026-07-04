"""온디바이스 OCR (프로젝트 ①·② 공유).

개인정보(생년월일·주민번호 등)를 다루므로 **클라우드로 전송하지 않는다.**
로컬 Tesseract(kor+eng)만 사용한다. 미설치 시 명확히 실패시킨다.

설치:
  Windows: https://github.com/UB-Mannheim/tesseract/wiki (kor 언어팩 포함 설치)
  Linux:   apt-get install tesseract-ocr tesseract-ocr-kor
"""
from __future__ import annotations

import shutil
from pathlib import Path

__all__ = ["ocr_available", "image_to_text", "OCRUnavailable"]


class OCRUnavailable(RuntimeError):
    pass


def ocr_available() -> bool:
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
    except Exception:
        return False
    return True


def image_to_text(image_path: str | Path, lang: str = "kor+eng") -> str:
    """이미지 파일에서 텍스트 추출. 온디바이스 전용."""
    if not ocr_available():
        raise OCRUnavailable(
            "Tesseract/pytesseract 미설치 — 온디바이스 OCR 불가. "
            "개인정보 보호를 위해 클라우드 OCR로 대체하지 않는다."
        )
    import pytesseract
    from PIL import Image

    img = Image.open(image_path)
    # 간단 전처리: 그레이스케일(대비 향상). 필요 시 이진화/리사이즈 확장 가능.
    if img.mode != "L":
        img = img.convert("L")
    return pytesseract.image_to_string(img, lang=lang)
