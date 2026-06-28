# 🔑 API 키 발급 가이드 (따라하기)

서비스 외부 연동에 필요한 키 발급 순서. **네이버(쉬움) → 카카오(사업자 필요)** 순으로 진행하세요.

발급한 키는 모두 `your-supplement/.env` 파일에 넣습니다 (`.env.example` 복사해서 시작).

```bash
cd your-supplement
cp .env.example .env   # 그 다음 .env 파일을 열어 값 채우기
```

> ⚠️ `.env` 파일은 절대 git에 커밋하지 마세요. (`.gitignore`에 이미 등록됨)

---

## 1️⃣ 네이버쇼핑 검색 API  — 약 10분, 무료, 사업자 불필요

최저가 비교에 사용. 가장 먼저 하세요.

### 단계
1. **네이버 개발자센터 접속** → https://developers.naver.com 로그인 (네이버 계정)
2. 상단 메뉴 **Application → 애플리케이션 등록**
3. 정보 입력:
   - **애플리케이션 이름**: `당신의영양제` (자유)
   - **사용 API**: `검색` 선택 ✅
   - **비로그인 오픈 API 환경**: `WEB 설정` 선택 → 서비스 URL에 `http://localhost:3000` 입력 (개발용)
4. **등록하기** 클릭
5. 발급된 **Client ID**, **Client Secret** 복사

### .env에 입력
```
NAVER_CLIENT_ID=발급받은_Client_ID
NAVER_CLIENT_SECRET=발급받은_Client_Secret
```

### 확인 (선택)
- 무료 한도: **하루 25,000회 호출** (MVP엔 충분)
- 검색 API는 별도 심사 없이 바로 사용 가능

### ✅ 동작 테스트
키 입력 후, 서버에서:
```bash
node -e "
require('dotenv').config();
const { refreshOffersFromNaver } = require('./server/api/offers');
refreshOffersFromNaver('omega3', undefined, 1000)
  .then(r => console.log('최저가 TOP3:', r.slice(0,3)))
  .catch(e => console.error(e.message));
"
```
(먼저 `npm i dotenv` 필요)

---

## 2️⃣ 카카오 알림톡  — 며칠 소요, 사업자등록 필요

추천 결과 전송 + 복용 알람에 사용. **개인은 발송 불가** — 사업자등록(개인사업자 OK)이 필요합니다.

> 💡 카카오는 알림톡을 **직접** 연동할 수 없고, **발송대행사**를 통해야 해요. (솔라피, 알리고, NHN Cloud 등)
> 가장 입문하기 쉬운 건 **솔라피(SOLAPI)** 라서 이 기준으로 안내합니다.

### 준비물 (먼저 확보)
- [ ] 사업자등록증 (개인사업자 가능)
- [ ] 카카오톡 채널 (없으면 무료로 개설)

### 단계 A — 카카오톡 채널 만들기
1. **카카오톡 채널 관리자센터** → https://center-pf.kakao.com 접속
2. **새 채널 만들기** → 채널 이름·검색용 아이디 설정
3. 채널 생성 완료 (이 채널이 알림톡 발신 주체가 됨)

### 단계 B — 발송대행사(솔라피) 가입 + 채널 연동
1. **솔라피** → https://solapi.com 회원가입
2. **카카오 비즈니스 → 채널 연동(발신프로필 등록)**
   - 단계 A에서 만든 카카오 채널을 연결
   - 사업자등록 정보 입력 → 카카오 비즈니스 인증 (1~2영업일)
3. 인증 완료 후 **발신프로필 키(senderKey)** 발급됨

### 단계 C — 알림톡 템플릿 등록 + 검수
알림톡은 **사전 승인된 템플릿**만 보낼 수 있어요. 2개를 등록합니다:

**템플릿 1 — 추천 결과** (`recommendation`)
```
[당신의 영양제] #{nickname}님의 맞춤 추천

▼ 추천 영양제
#{recommend_list}

▼ 복용 스케줄
아침: #{schedule_morning}
저녁: #{schedule_evening}

자세히 보기: #{rec_link}
```

**템플릿 2 — 복용 알람** (`intake_reminder`)
```
#{message}

오늘도 건강 챙기세요!
내 영양제 관리: #{my_link}
```

- 변수는 `#{변수명}` 형식 — 코드의 `templateArgs` 키와 **정확히 일치**해야 함 (kakao.js 참고)
- 등록 후 **카카오 검수** (1~2영업일). 광고성 문구가 있으면 반려되니 정보성으로만.

### 단계 D — API 키 발급
1. 솔라피 **개발/연동 → API Key 관리**에서 발급
2. 검수 통과한 템플릿의 **템플릿 ID** 확인

### .env에 입력
```
KAKAO_API_KEY=솔라피_API_Key
KAKAO_SENDER_KEY=발신프로필_senderKey
KAKAO_TEMPLATE_RECOMMENDATION=추천템플릿_ID
KAKAO_TEMPLATE_REMINDER=알람템플릿_ID
```

> ⚠️ **코드 수정 주의**: 현재 `server/api/kakao.js`는 카카오 직접 API 엔드포인트(`alimtalk-api.kakao.com`)로 작성돼 있어요.
> 솔라피 등 대행사를 쓰면 **엔드포인트와 인증 헤더 형식이 대행사 규격에 맞게 바뀌어야** 합니다.
> 대행사를 정하면 그에 맞춰 `sendAlimtalk()` 함수를 수정해 드릴게요. (대행사마다 요청 형식이 달라서 미리 못 맞춤)

---

## 3️⃣ 앱 푸시 (Expo) — 키 발급 불필요, 무료

앱 복용 알람은 **로컬 알림**이라 별도 키가 없어도 동작해요.
서버에서 원격 푸시를 보내려면 나중에 Expo Push 설정만 추가하면 됩니다 (스토어 출시 단계에서).

---

## ✅ 진행 체크리스트
- [ ] `.env` 파일 생성 (`cp .env.example .env`)
- [ ] 네이버 Client ID / Secret 발급 → `.env` 입력 → 동작 테스트
- [ ] (사업자 준비 후) 카카오 채널 개설
- [ ] 솔라피 가입 + 채널 연동 + 비즈니스 인증
- [ ] 알림톡 템플릿 2개 등록 + 검수 통과
- [ ] 카카오 키 `.env` 입력 + `kakao.js` 대행사 규격 반영
- [ ] 앱 푸시는 출시 단계에서 Expo Push 설정
