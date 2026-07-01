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
   - **Branch**: `claude/continue-session-96nt5z` 선택

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

---

## ✅ 배포 점검 결과 (2026-06-29)

`npm run build` 통과(11페이지) + 프로덕션 서버 스모크 테스트 전부 정상:

| 라우트 | 상태 | 비고 |
|---|---|---|
| `/` `/survey` `/result` `/nearby` `/my` | 200 | 홈·설문·결과·지도·내 루틴 |
| `POST /api/recommend` | 200 | 추천 엔진(키 불필요) |
| `GET /api/offers` | 200 | 키 없으면 예시 가격(NO_KEY) |
| `GET /api/nearby` | 200 | 키 없으면 샘플 약국 |

**키 없이도 전부 동작**하고, 키를 넣으면 실데이터로 바뀝니다(아래 표). 내 루틴(복용기록·체크인·소진예측)은 브라우저 `localStorage` 기반이라 서버·키 불필요.

| 키 | 없을 때 | 넣으면 |
|---|---|---|
| `NEXT_PUBLIC_KAKAO_MAP_KEY` | 지도 자리에 안내, 목록은 정상 | /nearby 지도 임베드 |
| `DATA_GO_KR_KEY` | 샘플 약국·응급실 | 실시간 공공데이터 |
| `NAVER_CLIENT_ID/SECRET` | 예시 최저가 | 네이버쇼핑 실시간 최저가 |

> 환경변수 템플릿: `apps/web/.env.example` 참고. 전부 **선택사항**.

### ⚠️ 배포 전 확인할 것
1. **브랜치**: 현재 최신 작업은 `claude/continue-session-96nt5z`. Vercel 프로젝트의 **Production Branch**를 이 브랜치로 두거나 `main`에 병합하세요. (이 저장소의 `main`에는 영양제 앱이 없음)
2. **Root Directory**: `your-supplement/apps/web` (STEP 2 참고).
3. 카카오맵 키를 쓰면 배포 URL을 카카오 플랫폼 도메인에 등록(STEP 5).

---

## 🔧 현재 배포 상태 진단 (2026-06-30)

Vercel은 **이미 이 저장소에 연동**되어 있습니다. 다만 프로젝트가 **2개** 생성돼 문제가 있습니다:

| Vercel 프로젝트 | Root Directory | 상태 | 문제 |
|---|---|---|---|
| `desktop-tutorial` | (저장소 루트) | ✅ 배포됨 | ❌ **잘못된 폴더** — 영양제 앱은 `your-supplement/apps/web`인데 루트를 배포해 엉뚱한 내용이 뜸 |
| `desktop-tutorial-g6q8` | `your-supplement/apps/web` | ❌ 실패 | **무료 플랜 하루 100회 배포 한도 초과** (중복 프로젝트가 매 푸시마다 배포를 2배 소모) |

**즉, 설정이 올바른 프로젝트(g6q8)는 한도 때문에 못 떴고, 잘못된 프로젝트가 대신 떠 있는 상태입니다.**

### ✅ 해결 방법 (대시보드에서, 한 번만)
1. **중복 프로젝트 삭제** — Vercel → `desktop-tutorial`(Root=루트) 프로젝트 → Settings → 맨 아래 **Delete Project**. (올바른 `desktop-tutorial-g6q8`만 남김 → 배포 소모도 절반으로)
2. **배포 한도 풀리면 재배포** — 무료 플랜 한도는 ~24시간 후 리셋. 리셋 후 `desktop-tutorial-g6q8` → **Deployments → 우측 ⋯ → Redeploy**. (급하면 Pro 업그레이드 시 한도 없음)
3. (선택) 그 프로젝트 **Settings → Git → Production Branch**를 `claude/continue-session-96nt5z`로, **Root Directory**가 `your-supplement/apps/web`인지 확인.

> 코드·빌드는 정상입니다(`next build` 17페이지 통과). 남은 건 위 **대시보드 클릭 2~3번**뿐.
