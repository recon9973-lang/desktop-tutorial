# 웹 (Next.js)

SEO·공유·결제 담당. 추천 로직은 `../../engine/recommend.js` 공유.

## 권장 스택
- Next.js (App Router) — "오메가3 추천" 등 검색 유입 위해 SSR/SEO
- 공유 엔진 import → `/api/recommend`는 `server/api/recommend.js` 래핑

## 주요 화면
- `/` 랜딩 → "1분 설문으로 내 영양제 찾기"
- `/survey` 설문 (고민·복용약·알레르기)
- `/result/[id]` 결과(근거·복용기간·경고·최저가·스케줄) + 카카오 공유
- `/ingredient/[id]` 성분 상세 + 별점·의견(참고 레이어)

## 셋업(예정)
```bash
npx create-next-app@latest .
```
