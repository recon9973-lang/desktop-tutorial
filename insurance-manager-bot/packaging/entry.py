"""PyInstaller 진입점. UI를 실행한다."""
import os
import sys

# 패키징(_MEIPASS) 환경에서 프로젝트 루트를 import 경로에 추가
_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from ui.app_ui import main  # noqa: E402

if __name__ == "__main__":
    main()
