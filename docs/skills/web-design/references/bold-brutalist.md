---
name: bold-brutalist
description: 강한 대비 + 초대형 타이포 + 원색. 에이전시·캠페인·이벤트·개성 브랜드용.
useFor: [광고에이전시, 캠페인, 이벤트, 페스티벌, 스트리트브랜드, 스타트업런칭]
colors:
  primary: "#ff3b00"
  accent-yellow: "#ffe500"
  accent-blue: "#2b2bff"
  ink: "#000000"
  on-dark: "#ffffff"
  canvas: "#ffffff"
  canvas-alt: "#ffe500"
  canvas-dark: "#000000"
  hairline: "#000000"
typography:
  display-mega: { fontFamily: "'Pretendard', 'Archivo', Arial Black, sans-serif", fontSize: 96px, fontWeight: 900, lineHeight: 0.95, letterSpacing: -0.04em, textTransform: uppercase }
  display-xl:   { fontSize: 56px, fontWeight: 800, lineHeight: 1.0, letterSpacing: -0.03em }
  heading:      { fontSize: 22px, fontWeight: 700, lineHeight: 1.2, letterSpacing: -0.01em }
  body:         { fontSize: 17px, fontWeight: 500, lineHeight: 1.55, letterSpacing: 0 }
  caption:      { fontSize: 14px, fontWeight: 700, lineHeight: 1.3, textTransform: uppercase }
rounded: { sm: 0px, md: 0px, lg: 0px, pill: 9999px }
spacing: { xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 40px, xxl: 64px, huge: 96px }
components:
  button-primary: { bg: ink, text: on-dark, rounded: sm, padding: "18px 32px", weight: 800, border: "3px solid ink" }
  button-loud: { bg: primary, text: on-dark, rounded: sm, padding: "18px 32px", weight: 800 }
  card: { bg: canvas, border: "3px solid ink", rounded: sm, padding: 24px, shadow: "8px 8px 0 #000000" }
  nav: { bg: accent-yellow, text: ink, padding: "16px 24px", border-bottom: "3px solid ink" }
  tag: { bg: accent-blue, text: on-dark, rounded: pill, padding: "6px 14px", weight: 700 }
---

## 특징
- **초대형 타이포**: 96px+ 블랙(900) 대문자 제목. 화면을 꽉 채우는 존재감.
- **원색 대비**: 레드·옐로·블루 원색 + 블랙 아웃라인. 파스텔·중간톤 없음.
- **하드 섀도우**: `8px 8px 0 #000` 오프셋 그림자(블러 0). 스티커·포스터 느낌.
- **굵은 보더**: 3px 블랙 테두리로 모든 요소를 또렷하게.
- **비대칭·과감**: 요소를 일부러 겹치거나 기울여 에너지.

## 컴포넌트 핵심
- 히어로: 초대형 대문자 카피 + 원색 배경 블록. 텍스트가 곧 그래픽.
- 카드: 3px 보더 + 하드 섀도우. 호버 시 그림자 축소(눌리는 느낌).
- 버튼: 두꺼운 보더 + 하드 섀도우, 클릭 시 offset 0으로 눌림.
- 네비: 옐로 바 + 블랙 굵은 하단선.

## Do & Don't
- ✅ 대비를 최대로. 원색 + 블랙.
- ✅ 하드 섀도우·굵은 보더로 포스터 느낌.
- ✅ 타이포 스케일을 과감하게(96px+).
- ❌ 파스텔·부드러운 그림자·미묘한 그라디언트 금지
- ❌ 신뢰·차분함이 중요한 업종(병원·금융)엔 부적합
- ❌ 가독성 해칠 정도의 겹침은 지양(에너지 ≠ 혼란)

## 반응형
- display-mega 96→56→40px. 대문자·블랙 웨이트 유지.
- 하드 섀도우 8px→4px로 축소. 보더 3px 유지.
- 비대칭 레이아웃은 모바일에서 세로 스택으로 정리.
