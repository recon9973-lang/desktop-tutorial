"""PyInstaller 진입점. UI를 실행한다."""
import os
import sys

# 패키징(_MEIPASS) 환경에서 프로젝트 루트를 import 경로에 추가
_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

if __name__ == "__main__":
    # 패키징 검증용 셀프테스트: 창을 띄우고 스크린샷만 저장 후 종료
    if os.environ.get("IMB_SELFTEST") == "1":
        from PySide6.QtWidgets import QApplication  # noqa: E402
        from ui.app_ui import MainWindow            # noqa: E402
        app = QApplication([])
        w = MainWindow(); w.show(); app.processEvents()
        shot = os.environ.get("IMB_SELFTEST_SHOT", "selftest.png")
        w.grab().save(shot)
        n = w.centralWidget().count()
        print(f"SELFTEST OK: tabs={n}, screenshot={shot}, font_bundle="
              f"{os.path.exists(os.path.join(_ROOT, 'assets', 'NanumGothic.ttf'))}")
        sys.exit(0)
    from ui.app_ui import main  # noqa: E402
    main()
