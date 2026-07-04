"""프로젝트 ① — 완성 PDF를 팩스 전송용 이미지(PNG)로 변환.

팩스는 흑백/저해상도이므로, 텍스트 선명도를 위해 고DPI 그레이스케일 PNG로 생성한다.
파일명 규칙: 고객명_가입설계동의_YYYYMMDD_팩스전송용_{n}.png
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import fitz


def pdf_to_fax_images(
    pdf_path: str | Path,
    out_dir: str | Path,
    customer_name: str,
    when: date | None = None,
    dpi: int = 200,
) -> list[Path]:
    when = when or date.today()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{customer_name}_가입설계동의_{when:%Y%m%d}_팩스전송용"
    doc = fitz.open(pdf_path)
    paths: list[Path] = []
    for i, page in enumerate(doc, start=1):
        # 그레이스케일: 팩스 톤과 유사, 파일 경량화
        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
        p = out_dir / f"{stem}_{i}.png"
        pix.save(p)
        paths.append(p)
    doc.close()
    return paths


def output_pdf_name(customer_name: str, when: date | None = None) -> str:
    when = when or date.today()
    return f"{customer_name}_가입설계동의_{when:%Y%m%d}.pdf"
