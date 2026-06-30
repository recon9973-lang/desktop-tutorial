// 당신의영양제 디자인 토큰 — React Native (웹 globals.css와 동일 팔레트)
// 내추럴 웰니스 그린

export const colors = {
  primary:        '#059669',
  primaryActive:  '#047857',
  secondary:      '#0b3b2d',
  onPrimary:      '#ffffff',
  canvas:         '#ffffff',
  canvasSoft:     '#f1f6f2',
  surface:        '#ffffff',
  ink:            '#10231b',
  inkSecondary:   '#2b3b34',
  inkMuted:       '#5c6b63',
  inkFaint:       '#9aa8a0',
  hairline:       '#e3eae5',
  accentMint:     '#6ee7b7',
  accentGreen:    '#16a34a',
  accentOrange:   '#d97706',
  accentRed:      '#d63b3b',
  kakaoYellow:    '#FEE500',
};

export const radius = {
  xs:   6,
  sm:   8,
  md:   10,
  lg:   14,
  xl:   20,
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
