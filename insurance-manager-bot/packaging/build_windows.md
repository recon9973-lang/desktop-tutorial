# Windows 배포용 exe 빌드 가이드

설계사 PC에 파이썬 없이 **더블클릭 실행**할 수 있는 단일 exe를 만든다.
(빌드는 반드시 Windows에서 수행 — PyInstaller는 크로스 컴파일을 하지 않는다.)

## 1. 준비 (빌드 PC = Windows)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

## 2. 빌드
프로젝트 루트(`insurance-manager-bot/`)에서:
```powershell
pyinstaller packaging/app.spec
```
→ `dist/보험매니저봇.exe` 생성. 한글 폰트·좌표 템플릿은 exe에 포함된다.

## 3. 사용 PC 요구사항
| 기능 | 필요 | 비고 |
|------|------|------|
| PDF 작성·팩스 이미지·UI | 없음(내장) | exe만으로 동작 |
| **이미지 OCR** | Tesseract 설치 | 아래 3-1 |
| **GA 웹 자동화** | Playwright/Chromium | 개발·운영 PC에서 별도 (아래 3-2) |

### 3-1. Tesseract(OCR) — 온디바이스, 개인정보 보호
- 설치: https://github.com/UB-Mannheim/tesseract/wiki (설치 시 **Korean** 언어팩 체크)
- 기본 경로: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- 경로가 다르면 환경변수 또는 코드에서 `pytesseract.pytesseract.tesseract_cmd` 지정.

### 3-2. Playwright(GA 웹 자동화, 선택)
웹 자동화까지 쓰려면 exe와 별도로:
```powershell
pip install playwright && playwright install chromium
```
그리고 `consent_bot/ga_automation.py`·`entry_bot/ga_*.py`의 `SELECTORS`를
실제 GA 화면에서 캘리브레이션한다. (로그인·간편PW는 설계상 사용자 수동)

## 4. 폰트 커스터마이즈(선택)
다른 한글 폰트를 쓰려면 `IMB_FONT` 환경변수에 .ttf 경로를 지정하면 우선 적용된다.

## 5. 배포 체크리스트
- [ ] `dist/보험매니저봇.exe` 실행 시 두 탭이 뜨는가
- [ ] ① 원본 동의서 PDF 선택 → 작성 & 미리보기 정상
- [ ] ① 팩스 이미지(PNG) 생성 및 폴더 열기
- [ ] ② 카톡 붙여넣기/이미지 OCR → 주민번호 마스킹·체크섬 표시
- [ ] (OCR 사용 시) Tesseract 설치 및 Korean 언어팩 확인
