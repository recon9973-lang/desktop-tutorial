---
name: minimal-swiss
description: 타이포·그리드 중심의 스위스 스타일. 무채색 + 모노 액센트. 스튜디오·B2B·포트폴리오용.
useFor: [디자인스튜디오, 포트폴리오, B2B, 컨설팅, 건축, 제조, IR/회사소개]
colors:
  primary: "#111111"
  accent: "#0038ff"
  ink: "#111111"
  ink-mute: "#6b6b6b"
  on-dark: "#ffffff"
  canvas: "#ffffff"
  canvas-soft: "#f2f2f2"
  hairline: "#111111"
  hairline-soft: "#dcdcdc"
typography:
  display-xxl: { fontFamily: "'Pretendard', 'Helvetica Neue', Arial, sans-serif", fontSize: 64px, fontWeight: 700, lineHeight: 1.0, letterSpacing: -0.03em }
  display-xl:  { fontSize: 40px, fontWeight: 700, lineHeight: 1.05, letterSpacing: -0.02em }
  heading:     { fontSize: 18px, fontWeight: 500, lineHeight: 1.3, letterSpacing: -0.01em }
  body:        { fontSize: 16px, fontWeight: 400, lineHeight: 1.6, letterSpacing: 0 }
  mono:        { fontFamily: "'JetBrains Mono', 'SF Mono', monospace", fontSize: 13px, fontWeight: 400, lineHeight: 1.5, letterSpacing: 0 }
  eyebrow:     { fontFamily: "mono", fontSize: 12px, fontWeight: 400, letterSpacing: 0.05em, textTransform: uppercase }
rounded: { sm: 0px, md: 0px, lg: 0px, pill: 0px }
spacing: { xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 40px, xxl: 64px, huge: 100px }
components:
  button-primary: { bg: primary, text: on-dark, rounded: sm, padding: "14px 24px", weight: 500 }
  button-line: { bg: canvas, text: ink, border: "1px solid ink", rounded: sm, padding: "14px 24px" }
  card: { bg: canvas, border: "1px solid hairline", rounded: sm, padding: 24px, shadow: none }
  nav: { bg: canvas, text: ink, padding: "20px 24px", border-bottom: "1px solid hairline" }
  divider: { border: "1px solid hairline", note: "굵고 명확한 구분선이 시그니처" }
---

## 특징
- **타이포가 주인공**: 큰 굵은 산세리프 제목 + 명확한 그리드. 장식 최소.
- **무채색 + 모노 액센트**: 블랙/화이트/그레이에 블루(`accent`) 딱 한 스푼. 컬러로 승부 안 함.
- **각진 0 라운드**: 모서리 없음. 굵은 헤어라인(1px 블랙)으로 구획.
- **그리드 노출**: 컬럼·베이스라인 그리드를 숨기지 않고 오히려 드러냄. 넘버링·인덱스.
- **모노스페이스 디테일**: eyebrow·메타 정보에 모노폰트로 기술적 톤.

## 컴포넌트 핵심
- 히어로: 좌측 상단 대형 타이틀 + 우측/하단 짧은 설명. 여백과 라인으로 긴장감.
- 인덱스/리스트: 01—프로젝트명 —— 연도, 굵은 구분선으로 행 구분.
- 카드: 그림자 없이 1px 라인 박스. 호버 시 배경 반전(블랙↔화이트).
- 푸터: 그리드형 링크 + 모노 메타.

## Do & Don't
- ✅ 그리드·정렬을 엄격히. 눈에 보이는 정렬이 스타일.
- ✅ 색은 무채색 + 액센트 1개로 제한.
- ✅ 굵은 구분선·넘버링 적극 사용.
- ❌ 둥근 모서리·그림자·그라디언트 금지 (톤 붕괴)
- ❌ 폰트 여러 종 섞지 말 것 (산세리프 1 + 모노 1)
- ❌ 장식용 일러스트 남발 금지

## 반응형
- 디스플레이 64→40→30px. 그리드 12열→6열→1열.
- 구분선·넘버링은 모바일에서도 유지(스타일 정체성).
