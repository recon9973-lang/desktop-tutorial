# 💻 맥(Mac)에서 개발 환경 세팅하기 (처음부터)

비개발자도 따라 할 수 있게 단계별로 정리했어요. **한 번에 한 단계씩** 하세요.

---

## STEP 0. 터미널 열기
- 키보드 `⌘(Command) + 스페이스바` → "터미널" 입력 → 엔터
- 검은(또는 흰) 창이 뜨면 성공. 여기에 명령어를 한 줄씩 붙여넣고 엔터 칩니다.

---

## STEP 1. 개발 도구 설치 (Node.js + Git)

### 1-1. Homebrew 설치 (맥용 설치 도우미)
터미널에 아래 한 줄을 붙여넣고 엔터:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
- 중간에 비밀번호를 물으면 **맥 로그인 비밀번호**를 입력 (화면에 안 보여도 정상)
- 설치 끝나면 안내에 나오는 `eval ...` 줄이 있으면 그것도 복사해 실행

### 1-2. Node.js 설치
```bash
brew install node
```

### 1-3. 설치 확인
```bash
node -v
git --version
```
- `v20.x.x` 같은 버전이 나오면 성공 ✅ (Git은 처음이면 설치 팝업이 뜰 수 있음 → 설치)

---

## STEP 2. 프로젝트 내려받기 (GitHub → 내 컴퓨터)

### 2-1. 바탕화면으로 이동해서 코드 복제
```bash
cd ~/Desktop
git clone https://github.com/recon9973-lang/desktop-tutorial.git
cd desktop-tutorial
```

### 2-2. 우리가 작업한 브랜치로 전환
```bash
git checkout claude/hospital-pharmacy-brainstorm-pdafsj
```
- 이제 `~/Desktop/desktop-tutorial/your-supplement` 안에 모든 코드가 있어요.

---

## STEP 3. 환경변수(.env) 만들기 — 네이버 키 입력

```bash
cd your-supplement
cp .env.example .env
open -e .env
```
- `open -e .env` 하면 **텍스트편집기**로 `.env`가 열려요.
- 아래 두 줄의 `=` 뒤를 본인 네이버 키로 교체 후 저장(`⌘+S`):
  ```
  NAVER_CLIENT_ID=여기에_Client_ID
  NAVER_CLIENT_SECRET=여기에_Client_Secret
  ```
- 카카오 4줄은 그대로 둬도 됩니다.

---

## STEP 4. 웹사이트 실행해보기 🎉

```bash
cd ~/Desktop/desktop-tutorial/your-supplement/apps/web
npm install
npm run dev
```
- `npm install`은 처음 한 번만 (1~2분 걸림)
- `Local: http://localhost:3000` 이 보이면 성공!
- 브라우저(크롬/사파리)에서 **http://localhost:3000** 열기 → 랜딩 페이지가 보여요.
- 종료하려면 터미널에서 `Control + C`

---

## STEP 5. 네이버 최저가 실제 테스트 (선택)

```bash
cd ~/Desktop/desktop-tutorial/your-supplement
npm install dotenv
node -e "
require('dotenv').config();
const { refreshOffersFromNaver } = require('./server/api/offers');
refreshOffersFromNaver('omega3', undefined, 1000)
  .then(r => { console.log('오메가3 최저가 TOP3:'); console.table(r.slice(0,3)); })
  .catch(e => console.error('오류:', e.message));
"
```
- 실제 네이버 쇼핑에서 오메가3 가격이 표로 나오면 키 연동 성공 ✅

---

## 문제가 생기면
- `command not found` → 해당 도구 설치(STEP 1)가 안 된 것
- `permission denied` → 명령어 앞에 `sudo ` 붙여서 재시도
- 그 외 에러 메시지를 그대로 복사해서 물어보세요!

## 자주 쓰는 명령어 요약
| 하고 싶은 것 | 명령어 |
|---|---|
| 웹 실행 | `cd ~/Desktop/desktop-tutorial/your-supplement/apps/web && npm run dev` |
| 최신 코드 받기 | `git pull origin claude/hospital-pharmacy-brainstorm-pdafsj` |
| 실행 중지 | `Control + C` |
