// Notion 디자인 토큰 — React Native 버전
// DESIGNnotion.md 기반, CSS var → JS 상수로 변환

export const colors = {
  primary:        '#0075de',
  primaryActive:  '#005bab',
  secondary:      '#213183',
  onPrimary:      '#ffffff',
  canvas:         '#ffffff',
  canvasSoft:     '#f6f5f4',
  surface:        '#ffffff',
  ink:            '#000000',
  inkSecondary:   '#31302e',
  inkMuted:       '#615d59',
  inkFaint:       '#a39e98',
  hairline:       '#e6e6e6',
  accentGreen:    '#1aae39',
  accentOrange:   '#dd5b00',
  accentRed:      '#d63b3b',
  kakaoYellow:    '#FEE500',
};

export const radius = {
  xs:   4,
  sm:   5,
  md:   8,
  lg:   12,
  xl:   16,
  full: 9999,
};

export const spacing = {
  xxs: 4,
  xs:  8,
  sm:  12,
  md:  16,
  lg:  24,
  xl:  28,
  xxl: 32,
};

export const typography = {
  display:  { fontSize: 32, fontWeight: '700', letterSpacing: -1 },
  heading1: { fontSize: 26, fontWeight: '700', letterSpacing: -0.5 },
  heading2: { fontSize: 22, fontWeight: '700', letterSpacing: -0.25 },
  title:    { fontSize: 18, fontWeight: '600', letterSpacing: -0.1 },
  bodyMd:   { fontSize: 16, fontWeight: '400', lineHeight: 24 },
  bodySm:   { fontSize: 15, fontWeight: '400', lineHeight: 20 },
  button:   { fontSize: 16, fontWeight: '500' },
  caption:  { fontSize: 13, fontWeight: '400', lineHeight: 18 },
  eyebrow:  { fontSize: 11, fontWeight: '600', letterSpacing: 0.5, textTransform: 'uppercase' },
};

// 복용 기간 타입별 색상
export const durColor = {
  continuous: colors.accentGreen,
  monitor:    colors.accentOrange,
  cyclic:     colors.accentRed,
};
export const durLabel = {
  continuous: '🟢 지속 복용',
  monitor:    '🟡 3개월 후 점검',
  cyclic:     '🔴 8주 후 점검',
};
