import { useLocalSearchParams, router } from 'expo-router';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert } from 'react-native';
import { colors, spacing, typography, radius, durColor, durLabel } from '../lib/theme';

// 데모 결과 (실제: API /recommend 호출)
const DEMO_RESULT = {
  recommended: [
    { ingredient_id: 'vitamin_d',      name: '비타민D',    evidence_level: 3, duration_type: 'monitor',    functions: ['칼슘 흡수·뼈 형성에 필요', '면역 기능 유지'], warnings: [], best_price: { price: 12900, vendor: '네이버쇼핑', price_per_mg: 0.11 } },
    { ingredient_id: 'vitamin_b_complex', name: '비타민B군', evidence_level: 3, duration_type: 'continuous', functions: ['에너지 대사에 필요', '정상적 신경 기능'], warnings: [], best_price: { price: 18900, vendor: '쿠팡', price_per_mg: 0.19 } },
    { ingredient_id: 'lutein',         name: '루테인',      evidence_level: 3, duration_type: 'continuous', functions: ['노화로 인한 눈 건강 유지에 도움'], warnings: [], best_price: { price: 15900, vendor: '아이허브', price_per_mg: 1.06 } },
    { ingredient_id: 'magnesium',      name: '마그네슘',    evidence_level: 3, duration_type: 'continuous', functions: ['에너지 생성', '신경·근육 기능 유지'], warnings: [], best_price: { price: 14900, vendor: '네이버쇼핑', price_per_mg: 0.25 } },
    { ingredient_id: 'omega3',         name: '오메가3',     evidence_level: 3, duration_type: 'continuous', functions: ['혈중 중성지방 개선', '혈행 개선'], warnings: ['와파린 복용자 상담 필요'], best_price: { price: 21900, vendor: '쿠팡', price_per_mg: 0.24 } },
  ],
  not_recommended: [{ name: '홍국', reason: '스타틴 병용 금지' }],
  schedule: { morning: ['비타민D', '비타민B군', '루테인', '마그네슘'], evening: ['오메가3'] },
  interactions_note: ['🔗 비타민D + 마그네슘: 마그네슘이 비타민D 활성화에 관여', '🔗 비타민D + 칼슘: 뼈 형성 시너지'],
};

function StarBadge({ level }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(245,184,0,0.1)', borderRadius: radius.full, paddingHorizontal: 7, paddingVertical: 2, gap: 3 }}>
      <Text style={{ color: '#f5b800', fontSize: 11 }}>{'⭐'.repeat(level)}</Text>
      <Text style={{ ...typography.eyebrow, color: colors.inkMuted }}>
        {level === 3 ? '식약처' : level === 2 ? 'NIH' : '연구'}
      </Text>
    </View>
  );
}

export default function Result() {
  const result = DEMO_RESULT;
  const [kakaoSent, setKakaoSent] = useState(false);

  const handleKakao = () => {
    // TODO: API 호출 → sendRecommendation
    setKakaoSent(true);
    Alert.alert('카카오톡 전송', '추천 결과를 카카오톡으로 보냈어요!');
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.canvasSoft }} contentContainerStyle={{ paddingBottom: 48 }}>
      {/* Hero */}
      <View style={{ backgroundColor: colors.secondary, padding: spacing.lg, paddingTop: 40, paddingBottom: 48 }}>
        <View style={s.badge}><Text style={s.badgeText}>근거 기반 맞춤 추천</Text></View>
        <Text style={{ fontSize: 28, fontWeight: '700', color: '#fff', letterSpacing: -0.5, marginBottom: 6 }}>🧬 당신의 영양제</Text>
        <Text style={{ ...typography.bodySm, color: 'rgba(255,255,255,0.7)' }}>후기·광고 미반영 · 식약처 인정 근거</Text>

        <TouchableOpacity style={s.kakaoBtn} onPress={handleKakao}>
          <Text style={s.kakaoBtnText}>{kakaoSent ? '✅ 카카오톡 전송됨' : '💬 카카오톡으로 받기'}</Text>
        </TouchableOpacity>
      </View>

      <View style={{ padding: spacing.lg }}>
        {/* Schedule */}
        <View style={s.card}>
          <Text style={[typography.title, { marginBottom: spacing.sm }]}>📅 복용 스케줄</Text>
          <View style={{ flexDirection: 'row', gap: 10 }}>
            {[['☀️ 아침', result.schedule.morning], ['🌙 저녁', result.schedule.evening]].map(([label, items]) => (
              <View key={label} style={{ flex: 1, backgroundColor: colors.canvasSoft, borderRadius: radius.md, padding: spacing.sm }}>
                <Text style={[typography.caption, { fontWeight: '600', marginBottom: 6 }]}>{label}</Text>
                {items.length ? items.map((n) => (
                  <Text key={n} style={[typography.caption, { color: colors.inkSecondary, marginBottom: 3 }]}>• {n}</Text>
                )) : <Text style={{ ...typography.caption, color: colors.inkFaint }}>없음</Text>}
              </View>
            ))}
          </View>
        </View>

        {/* Interactions */}
        <View style={[s.card, { backgroundColor: 'rgba(0,117,222,0.05)', borderColor: 'rgba(0,117,222,0.15)' }]}>
          {result.interactions_note.map((n, i) => (
            <Text key={i} style={[typography.bodySm, { color: colors.inkSecondary, marginBottom: i < result.interactions_note.length - 1 ? 6 : 0 }]}>{n}</Text>
          ))}
        </View>

        {/* Recommended */}
        <Text style={[typography.title, { marginBottom: spacing.sm }]}>✅ 추천 영양제</Text>
        {result.recommended.map((r, i) => (
          <View key={r.ingredient_id} style={[s.card, { marginBottom: 10 }]}>
            <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 12 }}>
              <View style={{
                width: 34, height: 34, borderRadius: radius.md,
                backgroundColor: i === 0 ? colors.primary : colors.canvasSoft,
                alignItems: 'center', justifyContent: 'center',
              }}>
                <Text style={{ fontWeight: '700', color: i === 0 ? '#fff' : colors.inkMuted }}>{i + 1}</Text>
              </View>

              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, alignItems: 'center', marginBottom: 4 }}>
                  <Text style={[typography.title, { color: colors.ink }]}>{r.name}</Text>
                  <StarBadge level={r.evidence_level} />
                </View>

                <View style={{ backgroundColor: `${durColor[r.duration_type]}18`, borderRadius: radius.full, paddingHorizontal: 8, paddingVertical: 2, alignSelf: 'flex-start', marginBottom: 6 }}>
                  <Text style={{ ...typography.eyebrow, color: durColor[r.duration_type] }}>
                    {durLabel[r.duration_type]}
                  </Text>
                </View>

                <Text style={[typography.caption, { color: colors.inkMuted, marginBottom: 6 }]}>
                  {r.functions.join(' · ')}
                </Text>

                {r.warnings.length > 0 && r.warnings.map((w, wi) => (
                  <Text key={wi} style={{ ...typography.caption, color: colors.accentOrange, marginBottom: 4 }}>⚠️ {w}</Text>
                ))}

                {r.best_price && (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 }}>
                    <View style={{ backgroundColor: colors.canvasSoft, borderRadius: radius.md, paddingHorizontal: 10, paddingVertical: 4 }}>
                      <Text style={{ fontWeight: '700', color: colors.primary, fontSize: 14 }}>
                        최저 ₩{r.best_price.price.toLocaleString()}
                      </Text>
                      <Text style={{ ...typography.caption, color: colors.inkFaint }}>mg당 ₩{r.best_price.price_per_mg} · {r.best_price.vendor}</Text>
                    </View>
                    <TouchableOpacity style={{ borderWidth: 1, borderColor: colors.hairline, borderRadius: radius.full, paddingHorizontal: 12, paddingVertical: 4 }}>
                      <Text style={[typography.caption, { color: colors.inkSecondary }]}>구매 →</Text>
                    </TouchableOpacity>
                  </View>
                )}
              </View>
            </View>
          </View>
        ))}

        {/* Not recommended */}
        {result.not_recommended.length > 0 && (
          <View style={s.card}>
            <Text style={[typography.title, { marginBottom: spacing.sm }]}>❌ 권하지 않아요</Text>
            {result.not_recommended.map((n) => (
              <View key={n.name} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <Text style={{ fontSize: 18 }}>🚫</Text>
                <View>
                  <Text style={[typography.bodySm, { fontWeight: '600' }]}>{n.name}</Text>
                  <Text style={[typography.caption, { color: colors.inkMuted }]}>{n.reason}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Register CTA */}
        <TouchableOpacity style={s.registerCta} onPress={() => router.push('/my-supplements')}>
          <View>
            <Text style={{ fontSize: 16, fontWeight: '700', color: '#fff', marginBottom: 2 }}>📦 내 영양제 등록하기</Text>
            <Text style={{ ...typography.caption, color: 'rgba(255,255,255,0.7)' }}>섭취 알람 · 복용 점검 · 조합 충돌 확인</Text>
          </View>
          <Text style={{ color: '#fff', fontSize: 20 }}>→</Text>
        </TouchableOpacity>

        <Text style={[typography.caption, { color: colors.inkFaint, textAlign: 'center', marginTop: spacing.lg, lineHeight: 18 }]}>
          ⚠️ 질병의 진단·치료가 아닌 정보 제공입니다.{'\n'}복용 전 의사·약사와 상담하세요.
        </Text>
      </View>
    </ScrollView>
  );
}

// useState import 누락 보정
import { useState } from 'react';

const s = StyleSheet.create({
  badge: {
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.3)', borderRadius: radius.full,
    paddingHorizontal: spacing.sm, paddingVertical: 3, alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,255,255,0.1)', marginBottom: spacing.md,
  },
  badgeText: { ...typography.eyebrow, color: 'rgba(255,255,255,0.9)' },
  kakaoBtn: {
    marginTop: spacing.lg, backgroundColor: '#FEE500', borderRadius: radius.full,
    paddingVertical: 11, paddingHorizontal: spacing.xl, alignSelf: 'flex-start',
  },
  kakaoBtnText: { fontWeight: '700', color: '#3A1D1D', fontSize: 15 },

  card: {
    backgroundColor: colors.surface, borderRadius: radius.xl,
    borderWidth: 1, borderColor: colors.hairline,
    padding: spacing.lg, marginBottom: spacing.sm,
  },
  registerCta: {
    backgroundColor: colors.secondary, borderRadius: radius.xl, padding: spacing.lg,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: spacing.md,
  },
});
