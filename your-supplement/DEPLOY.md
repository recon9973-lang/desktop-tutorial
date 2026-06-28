# 🚀 배포 가이드 (한 번만 하면 끝)

배포하면 **터미널·git pull·재시작이 전부 사라져요.** 사장님은 URL 하나만 열면 되고,
제가 코드를 고쳐서 push하면 **자동으로** 그 URL이 업데이트됩니다.

> ⚠️ 솔직한 한계: Claude(저)는 클라우드에서 돌아서 **사장님 Vercel 계정에 직접 로그인할 수 없어요.**
> 그래서 "계정 연결"이라는 **한 번뿐인 클릭 작업**만 사장님이 해주시면, 그 뒤로는 전부 자동이에요.

---

## STEP 1. Vercel 가입 + GitHub 연결 (한 번)
1. https://vercel.com 접속 → **Sign Up**
2. **Continue with GitHub** 선택 → GitHub 계정으로 로그인/권한 허용

## STEP 2. 프로젝트 가져오기
1. Vercel 대시보드 → **Add New… → Project**
2. **recon9973-lang/desktop-tutorial** 저장소 **Import**
3. 설정 화면에서 ⭐ **중요**:
   - **Root Directory**: `Edit` 눌러 → `your-supplement/apps/web` 선택
   - **Framework Preset**: `Next.js` (자동 감지됨)
   - **Branch**: `claude/hospital-pharmacy-brainstorm-pdafsj` 선택

## STEP 3. 환경변수 입력 (Environment Variables)
배포 화면의 **Environment Variables**에 아래를 추가 (Key / Value):

| Key | Value |
|-----|-------|
| `NAVER_CLIENT_ID` | 네이버 Client ID |
| `NAVER_CLIENT_SECRET` | 네이버 Client Secret |
| `NEXT_PUBLIC_KAKAO_MAP_KEY` | 카카오 JavaScript 키 |
| `DATA_GO_KR_KEY` | (있으면) 공공데이터 키 |

> 키가 없으면 그 줄은 비워도 됨 — 샘플 데이터로 동작해요.

## STEP 4. Deploy 클릭
- **Deploy** 누르면 1~2분 후 **`https://○○○.vercel.app`** 주소가 나와요.
- 이게 사장님 사이트 주소예요! 📱 휴대폰으로도 열려요.

## STEP 5. 카카오맵 도메인 추가 (지도용)
배포 URL이 나오면, 지도가 그 주소에서도 뜨도록 도메인 등록:
1. developers.kakao.com → 내 앱(당신의영양제) → **플랫폼 키** → JS 키 **수정**
2. 사이트 도메인에 **배포 URL**(`https://○○○.vercel.app`) 추가 → 저장

---

## ✅ 이후부터는 (자동)
- 제가 코드를 고쳐 push → Vercel이 **자동 재배포** (1~2분) → URL 새로고침하면 최신 화면.
- **터미널 / git pull / 서버 재시작 → 더 이상 안 함!** 🎉

## 로컬 개발은 그대로 유지
- 빠르게 실험하고 싶을 땐 기존 `npm run dev`(localhost:3000)도 계속 쓸 수 있어요.
- 배포 URL = "남에게 보여주는 진짜 사이트", 로컬 = "내가 실험하는 곳".
