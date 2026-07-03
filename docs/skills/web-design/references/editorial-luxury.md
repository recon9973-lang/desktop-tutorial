---
name: editorial-luxury
description: 세리프 디스플레이 + 큰 여백 + 절제된 고급감. 프리미엄 클리닉·브랜드용.
useFor: [성형외과, 피부과, 프리미엄클리닉, 럭셔리브랜드, 웨딩, 호텔, 뷰티]
colors:
  primary: "#1a1a1a"
  accent-gold: "#b08d57"
  accent-gold-deep: "#8a6d3f"
  ink: "#1a1a1a"
  ink-mute: "#77726c"
  on-dark: "#f5f1ea"
  canvas: "#ffffff"
  canvas-cream: "#f7f3ec"
  canvas-dark: "#141210"
  hairline: "#e6e0d6"
typography:
  display-xxl: { fontFamily: "'Noto Serif KR', 'Nanum Myeongjo', Georgia, serif", fontSize: 60px, fontWeight: 400, lineHeight: 1.12, letterSpacing: -0.01em }
  display-xl:  { fontFamily: "'Noto Serif KR', serif", fontSize: 44px, fontWeight: 400, lineHeight: 1.2, letterSpacing: -0.01em }
  heading:     { fontFamily: "'Pretendard', sans-serif", fontSize: 18px, fontWeight: 500, lineHeight: 1.5, letterSpacing: 0.02em }
  body:        { fontFamily: "'Pretendard', sans-serif", fontSize: 16px, fontWeight: 300, lineHeight: 1.8, letterSpacing: 0.01em }
  eyebrow:     { fontSize: 12px, fontWeight: 500, lineHeight: 1.2, letterSpacing: 0.2em, textTransform: uppercase }
  caption:     { fontSize: 13px, fontWeight: 300, lineHeight: 1.6, letterSpacing: 0.02em }
rounded: { sm: 0px, md: 2px, lg: 4px, pill: 9999px }
spacing: { xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 40px, xxl: 64px, huge: 120px }
components:
  button-primary: { bg: primary, text: on-dark, rounded: sm, padding: "16px 40px", weight: 400, letterSpacing: 0.08em }
  button-ghost: { bg: transparent, text: ink, border: "1px solid ink", rounded: sm, padding: "16px 40px", letterSpacing: 0.08em }
  button-gold: { bg: accent-gold, text: "#ffffff", rounded: sm, padding: "16px 40px" }
  card: { bg: canvas, border: none, rounded: md, padding: 0, note: "이미지 우선, 텍스트는 하단 여백에" }
  nav: { bg: transparent, text: ink, padding: "28px 40px", note: "얇은 로고 + 자간 넓은 메뉴" }
---

## 특징
- **세리프 디스플레이**: 큰 명조/세리프 제목이 격조를 만든다. 본문은 산세리프(Pretendard) 300.
- **압도적 여백**: 섹션 간격 120px. 요소가 숨 쉬게 둔다 = 프리미엄 인식.
- **무채색 + 골드 1스푼**: 블랙/크림 베이스에 골드(`accent-gold`)를 액센트로 아주 절제해서.
- **각진 미니멀 버튼**: 라운드 거의 0(2~4px). 넓은 자간의 버튼 라벨.
- **이미지가 주인공**: 큰 고품질 사진. 텍스트는 사진 옆/아래 여백에 조용히.

## 컴포넌트 핵심
- 히어로: 풀블리드 이미지 or 크림 배경 + 세리프 대형 카피 + eyebrow(대문자·넓은 자간).
- 갤러리: 정갈한 그리드, 그림자 없이 이미지 자체로 승부. 호버 시 미세한 줌.
- 시술/서비스: 넘버링(01·02·03) + 세리프 제목 + 짧은 설명. 절제된 리스트.
- 푸터: 다크(`canvas-dark`) + 크림 텍스트.

## Do & Don't
- ✅ 여백을 과감하게. 채우려 하지 말 것.
- ✅ 골드는 포인트로만(테두리·구분선·소량 텍스트).
- ✅ 사진 퀄리티가 전부 — 저해상·자극적 이미지 금지.
- ❌ 원색·그라디언트·둥근 pill 버튼 금지 (톤 붕괴)
- ❌ 성형·피부 분야는 의료광고법상 비포애프터·과장 표현 주의 (`ai-content-writer` 검수)
- ❌ 폰트 종류 남발 금지 (세리프 1 + 산세리프 1)

## 반응형
- 디스플레이 60→44→32px. 여백은 120→64→40px로 축소하되 답답하지 않게.
- 갤러리 그리드 3열→2열→1열. 이미지 art-direction 크롭.
