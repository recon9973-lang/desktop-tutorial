import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { colors, spacing, typography, radius } from '../lib/theme';

const FEATURES = [
  { emoji: '⭐', title: '근거 등급제',       desc: '식약처·NIH·논문 출처를 모든 추천에 표기' },
  { emoji: '⏱️', title: '복용 기간 가이드',  desc: '🟢지속 / 🟡점검 / 🔴주기 타입으로 안내' },
  { emoji: '🔗', title: '상호작용 엔진',     desc: '시너지·길항·의약품 경고 자동 반영' },
  { emoji: '💰', title: '함량당 최저가',     desc: '유효성분 mg당 가성비 랭킹' },
  { emoji: '💬', title: '카카오톡 전송',     desc: '추천 결과와 알람을 카톡으로' },
  { emoji: '⏰', title: '복용 알람',        desc: '시간·요일 맞춤 앱 푸시 알림' },
];

export default function Home() {
  return (
    <ScrollView style={s.container} contentContainerStyle={s.content}>
      {/* Hero */}
      <View style={s.hero}>
        <View style={s.badge}>
          <Text style={s.badgeText}>식약처 인정 근거 기반</Text>
        </View>
        <Text style={s.heroTitle}>내 몸에 맞는{'\n'}영양제, 근거로{'\n'}찾아드립니다</Text>
        <Text style={s.heroSub}>광고·후기가 아닌 검증된 데이터로{'\n'}당신의 영양제를 추천해요</Text>

        <TouchableOpacity style={s.btnPrimary} onPress={() => router.push('/survey')}>
          <Text style={s.btnPrimaryText}>1분 설문 시작하기 →</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.btnSecondary} onPress={() => router.push('/my-supplements')}>
          <Text style={s.btnSecondaryText}>내 영양제 관리</Text>
        </TouchableOpacity>
      </View>

      {/* Features */}
      <View style={s.section}>
        <Text style={s.sectionLabel}>왜 다른가요</Text>
        <Text style={[typography.heading2, { color: colors.ink, marginBottom: spacing.lg }]}>
          근거 기반 차별점
        </Text>
        <View style={s.grid}>
          {FEATURES.map((f) => (
            <View key={f.title} style={s.featureCard}>
              <Text style={{ fontSize: 26, marginBottom: spacing.xs }}>{f.emoji}</Text>
              <Text style={[typography.title, { color: colors.ink, marginBottom: 4 }]}>{f.title}</Text>
              <Text style={[typography.caption, { color: colors.inkMuted }]}>{f.desc}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* CTA bottom */}
      <View style={s.ctaBox}>
        <Text style={[typography.heading2, { color: colors.ink, marginBottom: spacing.xs }]}>
          지금 바로 시작해보세요
        </Text>
        <Text style={[typography.bodySm, { color: colors.inkMuted, marginBottom: spacing.lg }]}>
          1분 설문 · 무료 · 카카오톡 전송
        </Text>
        <TouchableOpacity style={s.btnPrimaryFull} onPress={() => router.push('/survey')}>
          <Text style={s.btnPrimaryText}>시작하기 →</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.canvasSoft },
  content:   { paddingBottom: 48 },

  hero: {
    backgroundColor: colors.secondary,
    padding: spacing.lg, paddingTop: 64, paddingBottom: 52,
    alignItems: 'flex-start',
  },
  badge: {
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.3)',
    borderRadius: radius.full, paddingHorizontal: spacing.sm, paddingVertical: 4,
    marginBottom: spacing.md, backgroundColor: 'rgba(255,255,255,0.1)',
  },
  badgeText: { ...typography.eyebrow, color: 'rgba(255,255,255,0.9)' },
  heroTitle: { fontSize: 34, fontWeight: '700', color: '#fff', letterSpacing: -0.75, lineHeight: 42, marginBottom: spacing.sm },
  heroSub:   { ...typography.bodySm, color: 'rgba(255,255,255,0.7)', marginBottom: spacing.xl, lineHeight: 22 },

  btnPrimary: {
    backgroundColor: colors.primary, borderRadius: radius.full,
    paddingVertical: 13, paddingHorizontal: spacing.xl, marginBottom: spacing.xs,
  },
  btnPrimaryText: { ...typography.button, color: colors.onPrimary },
  btnSecondary: {
    backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: radius.full,
    paddingVertical: 11, paddingHorizontal: spacing.lg, borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
  },
  btnSecondaryText: { ...typography.button, color: 'rgba(255,255,255,0.85)' },
  btnPrimaryFull: {
    backgroundColor: colors.primary, borderRadius: radius.full,
    paddingVertical: 14, alignItems: 'center',
  },

  section:      { padding: spacing.lg, paddingTop: spacing.xxl },
  sectionLabel: { ...typography.eyebrow, color: colors.primary, marginBottom: spacing.xs },
  grid:         { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  featureCard: {
    width: '47%', backgroundColor: colors.surface,
    borderRadius: radius.lg, padding: spacing.md,
    borderWidth: 1, borderColor: colors.hairline,
  },

  ctaBox: {
    margin: spacing.lg, backgroundColor: colors.surface,
    borderRadius: radius.xl, padding: spacing.lg,
    borderWidth: 1, borderColor: colors.hairline,
  },
});
