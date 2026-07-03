---
name: medical-clinic
description: 신뢰·청결·여백 중심. 차분한 블루/틸 + 넉넉한 화이트스페이스. 대다수 병·의원 기본값.
useFor: [내과, 치과, 정형외과, 안과, 한의원, 이비인후과, 병원 일반, 건강검진]
colors:
  primary: "#1a73c2"
  primary-deep: "#155a9a"
  accent-teal: "#12b5a5"
  ink: "#12263a"
  ink-mute: "#5b6b7d"
  on-primary: "#ffffff"
  canvas: "#ffffff"
  canvas-soft: "#f4f8fb"
  canvas-tint: "#eef5fb"
  hairline: "#dde6ee"
  success: "#2e9e6a"
typography:
  display-xl: { fontFamily: "'Pretendard', 'Noto Sans KR', system-ui, sans-serif", fontSize: 42px, fontWeight: 700, lineHeight: 1.25, letterSpacing: -0.02em }
  display-lg: { fontSize: 32px, fontWeight: 700, lineHeight: 1.3, letterSpacing: -0.02em }
  heading:    { fontSize: 20px, fontWeight: 600, lineHeight: 1.4, letterSpacing: -0.01em }
  body:       { fontSize: 16px, fontWeight: 400, lineHeight: 1.75, letterSpacing: 0 }
  body-sm:    { fontSize: 14px, fontWeight: 400, lineHeight: 1.7 }
  caption:    { fontSize: 13px, fontWeight: 400, lineHeight: 1.5 }
rounded: { sm: 6px, md: 10px, lg: 16px, xl: 20px, pill: 9999px }
spacing: { xs: 4px, sm: 8px, md: 12px, lg: 20px, xl: 32px, xxl: 48px, huge: 80px }
components:
  button-primary: { bg: primary, text: on-primary, rounded: md, padding: "14px 28px", weight: 600 }
  button-outline: { bg: canvas, text: primary, border: "1.5px solid primary", rounded: md, padding: "14px 28px" }
  button-kakao: { bg: "#FEE500", text: "#3c1e1e", rounded: md, padding: "14px 28px", weight: 700 }
  card: { bg: canvas, border: "1px solid hairline", rounded: lg, padding: 28px, shadow: "rgba(18,38,58,0.06) 0 4px 16px" }
  info-band: { bg: canvas-tint, rounded: xl, padding: 40px }
  nav: { bg: canvas, text: ink, padding: "18px 28px", shadow: "rgba(18,38,58,0.04) 0 1px 0" }
---

## 특징
- **신뢰가 최우선**: 과장·화려함 배제. 청결한 화이트 + 차분한 블루(`primary`)로 안정감.
- **넉넉한 여백**: 섹션 간격 64~80px. 정보를 빽빽하게 넣지 않는다 → 환자 불안 완화.
- **정보 위계 명확**: 진료과목·의료진·오시는길·예약을 카드/밴드로 또렷이 구분.
- **카카오 상담 CTA**: 전화번호 남발 대신 카카오 노란 버튼 + 예약 버튼 조합(의료광고법 대응).
- **읽기 편한 본문**: line-height 1.75, Pretendard. 시니어 환자 배려.

## 컴포넌트 핵심
- 히어로: 좌측 카피(진료 핵심 메시지) + 우측 의료진/시설 사진. 신뢰 뱃지(학회·인증) 노출.
- 진료과 카드: 아이콘 + 과목명 + 1줄 설명, 3~4열 그리드.
- 의료진 카드: 원장 사진 + 이름 + 전문분야 + 약력(경험/전문성 = E-E-A-T).
- 예약 밴드: `canvas-tint` 배경 + 카카오/전화/오시는길 3버튼.

## Do & Don't
- ✅ 신뢰 신호(전문의·학회·장비·인증) 시각화
- ✅ CTA는 "예약/상담"으로 명확히. 카카오 채널 우선.
- ✅ 대비·글자 크기 넉넉히 (고령 환자 접근성)
- ❌ 최고·완치·100% 등 과장 표현 금지 (의료광고법 제56조 → `ai-content-writer` 검수 연동)
- ❌ 비포·애프터 자극적 이미지, 원색 남발 금지
- ❌ 여백을 줄여 정보를 몰아넣지 말 것

## 반응형
- 히어로 2단→1단(모바일은 카피 먼저).
- 진료과 4열→2열→1열. 의료진 3열→1열.
- 하단 고정 CTA 바(예약/전화/카카오)를 모바일에 노출.
