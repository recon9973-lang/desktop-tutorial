"""엑셀 칸 주소 — 두 곳이 같은 것을 따로 갖고 있었다.

키워드 내보내기(`keywords/export.py`)와 리포트 xlsx(`reports/render/xlsx.py`)가
`_cell_reference` 와 `_COLUMN_LETTERS` 를 한 벌씩 갖고 있었다(2026-08-09 실측, 본문은
글자까지 같았다). 지침서 0-D — **나중에 만든 쪽이 원본의 제약을 모른 채 더 관대해진다.**

여기서 쓰는 규칙은 엑셀의 것이지 우리 것이 아니다. 우리가 정할 것이 없으므로 두 벌을
가질 이유도 없다.
"""

from __future__ import annotations

from typing import Final

COLUMN_LETTERS: Final = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cell_reference(column_index: int, row_index: int) -> str:
    """``A1`` 모양 주소. 열은 0부터, 행은 1부터 센다.

    26열을 넘으면 ``AA`` 로 넘어간다 — 엑셀의 진법은 자리마다 1을 빼야 해서
    ``remaining // 26 - 1`` 이다. 흔히 틀리는 자리라 두 벌로 두면 한쪽만 틀린다.
    """
    letters = ""
    remaining = column_index
    while True:
        letters = COLUMN_LETTERS[remaining % 26] + letters
        remaining = remaining // 26 - 1
        if remaining < 0:
            break
    return f"{letters}{row_index}"
