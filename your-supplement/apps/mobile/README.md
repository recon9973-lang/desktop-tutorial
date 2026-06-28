# 앱 (React Native + Expo)

푸시 알림·복용 관리·홈 위젯 담당. 추천 로직은 `../../engine/recommend.js` 공유.

## 권장 스택
- Expo (iOS·Android 동시) + Expo Router
- Expo Notifications — 섭취 알람 푸시(카카오 알림톡과 이중 채널)
- 공유 엔진 import → 오프라인에서도 동일 추천 결과

## 주요 화면
- 온보딩 설문 → 추천 결과
- 내 영양제(`my_supplement`) 등록·조합 충돌 점검
- 섭취 알람(`intake_schedule`) 설정 — 시간·요일
- 복용 체크 + 점검 알림(🟡90일/🔴56일)

## 셋업(예정)
```bash
npx create-expo-app@latest .
```
