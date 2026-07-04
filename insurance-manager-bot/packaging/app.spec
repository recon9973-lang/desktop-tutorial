# PyInstaller spec — 보험 매니저 봇 (Windows 단일 exe)
# 빌드: pyinstaller packaging/app.spec   (프로젝트 루트에서 실행)
#
# 주의:
#  - Tesseract(OCR)와 Playwright(Chromium)는 용량이 커서 exe에 묶지 않고
#    사용 PC에 별도 설치하는 것을 권장한다(build_windows.md 참고).
#  - 한글 폰트(assets/NanumGothic.ttf)와 좌표 템플릿(template.json)은 번들한다.

import os
block_cipher = None
ROOT = os.path.abspath(os.getcwd())

datas = [
    (os.path.join("assets", "NanumGothic.ttf"), "assets"),
    (os.path.join("consent_bot", "template.json"), "consent_bot"),
]

hiddenimports = [
    "pytesseract",
    "PIL", "PIL.Image",
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    "fitz",
    "keyring.backends.Windows",   # Windows Credential Manager
]

a = Analysis(
    ["packaging/entry.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["playwright"],   # 별도 설치 권장(용량). 웹 자동화는 개발 PC에서.
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name="보험매니저봇",
    console=False,          # GUI 앱
    debug=False,
    strip=False,
    upx=True,
    onefile=True,
)
