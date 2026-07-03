---
name: friendly-rounded
description: 둥근 모서리 + 파스텔 + 친근한 톤. 소아과·산부인과·B2C·앱 랜딩용.
useFor: [소아과, 산부인과, 치과(어린이), 한의원, 교육, 육아, 앱랜딩, B2C서비스]
colors:
  primary: "#5b8def"
  accent-mint: "#4fd1c5"
  accent-peach: "#ff9a8b"
  accent-yellow: "#ffd66b"
  ink: "#2d3748"
  ink-mute: "#718096"
  on-primary: "#ffffff"
  canvas: "#ffffff"
  canvas-soft: "#f5f9ff"
  canvas-warm: "#fff8f0"
  hairline: "#e6edf5"
typography:
  display-xl: { fontFamily: "'Pretendard', 'Noto Sans KR', system-ui, sans-serif", fontSize: 44px, fontWeight: 800, lineHeight: 1.25, letterSpacing: -0.02em }
  display-lg: { fontSize: 32px, fontWeight: 700, lineHeight: 1.3, letterSpacing: -0.02em }
  heading:    { fontSize: 20px, fontWeight: 700, lineHeight: 1.4, letterSpacing: -0.01em }
  body:       { fontSize: 16px, fontWeight: 400, lineHeight: 1.75, letterSpacing: 0 }
  caption:    { fontSize: 13px, fontWeight: 500, lineHeight: 1.5 }
rounded: { sm: 10px, md: 16px, lg: 24px, xl: 32px, pill: 9999px }
spacing: { xs: 4px, sm: 8px, md: 12px, lg: 20px, xl: 32px, xxl: 48px, huge: 72px }
components:
  button-primary: { bg: primary, text: on-primary, rounded: pill, padding: "14px 28px", weight: 700, shadow: "rgba(91,141,239,0.3) 0 6px 16px" }
  button-soft: { bg: canvas-soft, text: primary, rounded: pill, padding: "14px 28px", weight: 700 }
  card: { bg: canvas, border: "1px solid hairline", rounded: xl, padding: 28px, shadow: "rgba(45,55,72,0.06) 0 8px 24px" }
  card-tint: { bg: canvas-soft, rounded: xl, padding: 28px }
  nav: { bg: canvas, text: ink, padding: "16px 24px", rounded: pill, note: "떠 있는 알약형 네비도 잘 어울림" }
  pill-tag: { bg: accent-mint, text: on-primary, rounded: pill, padding: "6px 14px", weight: 600 }
---

## 특징
- **둥근 모서리**: 카드 24~32px, 버튼 pill. 부드럽고 친근한 인상.
- **파스텔 팔레트**: 소프트 블루 베이스 + 민트·피치·옐로 액센트. 밝고 따뜻하게.
- **부드러운 그림자**: 컬러가 스민 소프트 섀도우(블러 큼). 둥둥 떠 있는 느낌.
- **일러스트/아이콘**: 라운드한 일러스트·이모지톤 아이콘이 잘 어울림.
- **넉넉한 본문**: line-height 1.75, 700 웨이트 제목으로 또렷하되 부담 없이.

## 컴포넌트 핵심
- 히어로: 밝은 배경 + 친근한 카피 + 일러스트/사진 + pill CTA(컬러 섀도우).
- 카드: 큰 라운드 + 소프트 섀도우. 파스텔 tint 배경 변형.
- 스텝/과정: 둥근 넘버 뱃지 + 짧은 설명, 밝은 색으로 단계 구분.
- 네비: 흰 배경 or 떠 있는 pill형.

## Do & Don't
- ✅ 라운드·파스텔·소프트 섀도우로 친근함 유지.
- ✅ 액센트 색을 밝게 여러 개 써도 OK(단, 조화롭게).
- ✅ 아이콘·일러스트로 설명을 쉽게.
- ❌ 각진 0라운드·하드 섀도우·무거운 다크 톤 금지 (친근함 붕괴)
- ❌ 프리미엄·고급 포지셔닝엔 부적합 (그건 editorial-luxury)
- ❌ 파스텔 대비 부족으로 본문 가독성 떨어뜨리지 말 것(대비 ≥4.5:1)

## 반응형
- 디스플레이 44→32→26px. 라운드·pill 유지.
- 카드 그리드 3열→2열→1열. 소프트 섀도우 유지.
- 하단 떠 있는 CTA(예약/상담)를 모바일에 노출.
