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


def _preprocess(img):
    """색 배경·저대비(카톡 스크린샷 등)에서도 잘 읽히도록 전처리.

    회색조 → 대비 정규화 → 2배 확대 → 이진화(Otsu 근사).
    """
    from PIL import Image, ImageOps

    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    # 2배 확대(작은 글자 인식률 향상)
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    # Otsu 임계값 계산
    hist = img.histogram()
    total = sum(hist)
    sum_all = sum(i * hist[i] for i in range(256))
    sumB = wB = 0.0
    max_var = threshold = 0
    for i in range(256):
        wB += hist[i]
        if wB == 0:
            continue
        wF = total - wB
        if wF == 0:
            break
        sumB += i * hist[i]
        mB = sumB / wB
        mF = (sum_all - sumB) / wF
        var = wB * wF * (mB - mF) ** 2
        if var > max_var:
            max_var, threshold = var, i
    return img.point(lambda p: 255 if p > threshold else 0)


def image_to_text(image_path: str | Path, lang: str = "kor+eng",
                  preprocess: bool = True) -> str:
    """이미지 파일에서 텍스트 추출. 온디바이스 전용."""
    if not ocr_available():
        raise OCRUnavailable(
            "Tesseract/pytesseract 미설치 — 온디바이스 OCR 불가. "
            "개인정보 보호를 위해 클라우드 OCR로 대체하지 않는다."
        )
    import pytesseract
    from PIL import Image

    img = Image.open(image_path)
    if preprocess:
        img = _preprocess(img)
    elif img.mode != "L":
        img = img.convert("L")
    # psm 6: 균일한 텍스트 블록 가정(카톡/문서 캡처에 적합)
    return pytesseract.image_to_string(img, lang=lang, config="--psm 6")
