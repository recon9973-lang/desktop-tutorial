---
name: saas-stripe
description: 인디고 CTA + 그라디언트 메시 히어로 + 씬(300) 타이포. 핀테크·SaaS·IT·마케팅 에이전시용.
useFor: [SaaS, 핀테크, IT서비스, 마케팅에이전시, B2B 제품]
colors:
  primary: "#533afd"
  primary-deep: "#4434d4"
  primary-press: "#2e2b8c"
  brand-dark-900: "#1c1e54"
  ink: "#0d253d"
  ink-mute: "#64748d"
  on-primary: "#ffffff"
  canvas: "#ffffff"
  canvas-soft: "#f6f9fc"
  canvas-cream: "#f5e9d4"
  hairline: "#e3e8ee"
  accent-ruby: "#ea2261"
  accent-magenta: "#f96bee"
typography:
  display-xxl: { fontFamily: "Inter, 'Pretendard', system-ui, sans-serif", fontSize: 56px, fontWeight: 300, lineHeight: 1.03, letterSpacing: -1.4px }
  display-xl:  { fontSize: 48px, fontWeight: 300, lineHeight: 1.15, letterSpacing: -0.96px }
  display-lg:  { fontSize: 32px, fontWeight: 300, lineHeight: 1.1,  letterSpacing: -0.64px }
  heading:     { fontSize: 20px, fontWeight: 300, lineHeight: 1.4,  letterSpacing: -0.2px }
  body:        { fontSize: 16px, fontWeight: 300, lineHeight: 1.6,  letterSpacing: 0 }
  body-tabular:{ fontSize: 14px, fontWeight: 300, lineHeight: 1.4,  letterSpacing: -0.42px, fontFeature: tnum }
  caption:     { fontSize: 13px, fontWeight: 400, lineHeight: 1.4,  letterSpacing: -0.39px }
rounded: { sm: 6px, md: 8px, lg: 12px, xl: 16px, pill: 9999px }
spacing: { xs: 4px, sm: 8px, md: 12px, lg: 16px, xl: 24px, xxl: 32px, huge: 64px }
components:
  button-primary: { bg: primary, text: on-primary, rounded: pill, padding: "8px 16px", weight: 400 }
  button-secondary: { bg: canvas, text: primary, border: "1px solid primary", rounded: pill, padding: "8px 16px" }
  card: { bg: canvas, border: "1px solid hairline", rounded: lg, padding: 32px, shadow: "rgba(0,55,112,0.08) 0 1px 3px" }
  card-featured: { bg: brand-dark-900, text: on-primary, rounded: lg, padding: 32px }
  nav: { bg: canvas, text: ink, padding: "16px 24px" }
---

## 특징
- **그라디언트 메시 히어로**: 크림→오렌지→라벤더→인디고→루비 파스텔 워시가 상단 1/3을 덮는다. 브랜드 시그니처.
- **씬 타이포**: 디스플레이는 항상 weight 300 + 음수 자간(-1.4px@56px). 400 이상으로 올리면 브랜드감 붕괴.
- **단일 인디고 CTA**: 채움 버튼은 밴드당 `primary` pill 1개만. 나머지는 아웃라인.
- **다크 네이비 강조**: featured 카드·대시보드 목업은 `brand-dark-900` 딥 네이비.
- **tabular 숫자**: 금액·수치 셀엔 `tnum`. 핀테크 시그널.

## 컴포넌트 핵심
- 버튼: pill(9999px), `8px 16px` 타이트 패딩. 짧고 단호하게.
- 카드: 흰 배경 + 12px 라운드 + 얇은 헤어라인 + 아주 옅은 그림자.
- 히어로: 그라디언트 메시 위에 흰 캔버스로 텍스트·제품 목업이 떠 있는 구성.

## Do & Don't
- ✅ 히어로엔 그라디언트 메시 필수 (맨 캔버스 히어로는 오프브랜드)
- ✅ 디스플레이 weight 300 유지, 음수 자간
- ✅ `primary`는 CTA·링크 강조에만 (본문 색으로 쓰지 말 것)
- ❌ 문서화된 그라디언트 스톱 외 새 액센트 색 추가 금지
- ❌ 버튼을 둥근 사각형으로 바꾸지 말 것 (pill 유지)

## 반응형
- 디스플레이 56→48→32→26px 단계 축소, 모바일 히어로 36px.
- 가격표 4열→2열→1열 (1024/768 브레이크).
- 그라디언트 메시는 모바일에서 리타일해 유지.

## 한글 적용
Sohne 대신 **Pretendard**(또는 Inter+Noto Sans KR) weight 300. 본문 line-height 1.6으로 한글 가독성 확보.
