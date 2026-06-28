import { useState } from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, TextInput } from 'react-native';
import { router } from 'expo-router';
import { colors, spacing, typography, radius } from '../lib/theme';

const STEPS = [
  {
    id: 'profile', title: '기본 정보', subtitle: '맞춤 추천을 위해 알려주세요',
    fields: [
      { id: 'age_range', label: '나이대', options: ['10대','20대','30대','40대','50대','60대+'] },
      { id: 'sex',       label: '성별',   options: ['남성','여성','선택 안 함'] },
    ],
  },
  {
    id: 'concerns', title: '어떤 고민이 있나요?', subtitle: '해당하는 것을 모두 선택해주세요',
    options: [
      { value: 'fatigue',      label: '피로 / 기력 저하',   emoji: '😴' },
      { value: 'sleep_stress', label: '수면 / 스트레스',     emoji: '🌙' },
      { value: 'eye',          label: '눈 피로 / 눈 건강',   emoji: '👁️' },
      { value: 'blood_lipid',  label: '혈관 / 혈중 지질',    emoji: '❤️' },
      { value: 'bone_joint',   label: '뼈 / 관절',           emoji: '🦴' },
      { value: 'immune',       label: '면역력',               emoji: '🛡️' },
      { value: 'gut',          label: '장 건강 / 소화',       emoji: '🦠' },
      { value: 'liver',        label: '간 건강',              emoji: '🍺' },
      { value: 'anemia_women', label: '빈혈 / 여성 건강',     emoji: '🩸' },
      { value: 'menopause',    label: '갱년기',               emoji: '🌡️' },
    ],
  },
  {
    id: 'medications', title: '복용 중인 약이 있나요?', subtitle: '상호작용 안전 확인에 사용됩니다 (없으면 건너뛰기)',
    options: [
      { value: 'none',            label: '없음' },
      { value: 'warfarin',        label: '와파린 (항응고제)' },
      { value: 'antiplatelet',    label: '아스피린 / 항혈소판제' },
      { value: 'antihypertensive',label: '혈압약' },
      { value: 'statin',          label: '스타틴 (고지혈증약)' },
      { value: 'levothyroxine',   label: '갑상선호르몬제' },
      { value: 'antibiotics',     label: '항생제' },
    ],
  },
  {
    id: 'allergies', title: '알레르기가 있나요?', subtitle: '해당 성분은 추천에서 제외됩니다',
    options: [
      { value: 'none',   label: '없음' },
      { value: 'milk',   label: '🥛 우유 / 유제품' },
      { value: 'soy',    label: '🫘 대두 / 콩' },
      { value: 'peanut', label: '🥜 땅콩' },
      { value: 'fish',   label: '🐟 생선 / 해산물' },
    ],
  },
];

export default function Survey() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({ age_range: '', sex: '', concerns: [], medications: [], allergies: [] });

  const current = STEPS[step];
  const progress = (step + 1) / STEPS.length;

  const toggleMulti = (key, val) => {
    setAnswers((prev) => {
      const arr = prev[key] || [];
      if (val === 'none') return { ...prev, [key]: [] };
      const next = arr.includes(val) ? arr.filter((v) => v !== val) : [...arr.filter((v) => v !== 'none'), val];
      return { ...prev, [key]: next };
    });
  };

  const canNext = () => {
    if (current.id === 'profile') return answers.age_range && answers.sex;
    if (current.id === 'concerns') return answers.concerns.length > 0;
    return true;
  };

  const handleNext = () => {
    if (step < STEPS.length - 1) setStep((s) => s + 1);
    else {
      const user = {
        profile: { age_range: answers.age_range, sex: answers.sex },
        concerns: answers.concerns,
        medications: answers.medications.filter((m) => m !== 'none'),
        allergies: answers.allergies.filter((a) => a !== 'none'),
      };
      router.push({ pathname: '/result', params: { user: JSON.stringify(user) } });
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.canvasSoft }}>
      {/* Progress */}
      <View style={{ height: 3, backgroundColor: colors.hairline }}>
        <View style={{ height: 3, width: `${progress * 100}%`, backgroundColor: colors.primary }} />
      </View>

      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: spacing.lg, paddingBottom: 120 }}>
        {/* Step label */}
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: spacing.lg }}>
          <View style={{ backgroundColor: colors.surface, borderRadius: radius.full, paddingHorizontal: 10, paddingVertical: 3, borderWidth: 1, borderColor: colors.hairline }}>
            <Text style={{ ...typography.eyebrow, color: colors.primary }}>{step + 1} / {STEPS.length}</Text>
          </View>
        </View>

        <Text style={[typography.heading1, { color: colors.ink, marginBottom: 6 }]}>{current.title}</Text>
        <Text style={[typography.bodySm, { color: colors.inkMuted, marginBottom: spacing.xl }]}>{current.subtitle}</Text>

        {/* Profile step */}
        {current.id === 'profile' && current.fields.map((field) => (
          <View key={field.id} style={{ marginBottom: spacing.lg }}>
            <Text style={[typography.title, { color: colors.ink, marginBottom: spacing.sm }]}>{field.label}</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {field.options.map((opt) => {
                const active = answers[field.id] === opt;
                return (
                  <TouchableOpacity key={opt}
                    style={[s.chip, active && s.chipActive]}
                    onPress={() => setAnswers((prev) => ({ ...prev, [field.id]: opt }))}
                  >
                    <Text style={[s.chipText, active && s.chipTextActive]}>{opt}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        ))}

        {/* Concerns step */}
        {current.id === 'concerns' && (
          <View style={{ gap: 8 }}>
            {current.options.map((opt) => {
              const active = answers.concerns.includes(opt.value);
              return (
                <TouchableOpacity key={opt.value}
                  style={[s.concernCard, active && s.concernCardActive]}
                  onPress={() => toggleMulti('concerns', opt.value)}
                >
                  <Text style={{ fontSize: 22 }}>{opt.emoji}</Text>
                  <Text style={[s.concernText, active && s.concernTextActive]}>{opt.label}</Text>
                  {active && <Text style={{ marginLeft: 'auto', color: colors.primary, fontSize: 18 }}>✓</Text>}
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        {/* Medications & Allergies steps */}
        {(current.id === 'medications' || current.id === 'allergies') && (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
            {current.options.map((opt) => {
              const arr = answers[current.id] || [];
              const active = opt.value === 'none' ? arr.length === 0 : arr.includes(opt.value);
              return (
                <TouchableOpacity key={opt.value}
                  style={[s.chip, active && s.chipActive]}
                  onPress={() => toggleMulti(current.id, opt.value)}
                >
                  <Text style={[s.chipText, active && s.chipTextActive]}>{opt.label}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        )}
      </ScrollView>

      {/* Bottom nav */}
      <View style={s.navBar}>
        {step > 0 ? (
          <TouchableOpacity style={s.btnBack} onPress={() => setStep((s) => s - 1)}>
            <Text style={s.btnBackText}>← 이전</Text>
          </TouchableOpacity>
        ) : <View />}
        <TouchableOpacity
          style={[s.btnNext, !canNext() && { opacity: 0.4 }]}
          onPress={handleNext} disabled={!canNext()}
        >
          <Text style={s.btnNextText}>
            {step === STEPS.length - 1 ? '결과 보기 🧬' : '다음 →'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  chip: {
    paddingHorizontal: spacing.md, paddingVertical: 9,
    borderRadius: radius.full, borderWidth: 1.5, borderColor: colors.hairline,
    backgroundColor: colors.surface,
  },
  chipActive: { borderColor: colors.primary, backgroundColor: 'rgba(0,117,222,0.06)' },
  chipText:       { ...typography.bodySm, color: colors.ink },
  chipTextActive: { color: colors.primary, fontWeight: '600' },

  concernCard: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    padding: spacing.md, borderRadius: radius.lg,
    borderWidth: 1.5, borderColor: colors.hairline, backgroundColor: colors.surface,
  },
  concernCardActive: { borderColor: colors.primary, backgroundColor: 'rgba(0,117,222,0.04)' },
  concernText:       { ...typography.bodySm, color: colors.ink, flex: 1 },
  concernTextActive: { color: colors.primary, fontWeight: '600' },

  navBar: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    backgroundColor: colors.canvas, borderTopWidth: 1, borderTopColor: colors.hairline,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: spacing.md, paddingBottom: 32,
  },
  btnBack: {
    paddingVertical: 11, paddingHorizontal: spacing.lg,
    borderRadius: radius.full, borderWidth: 1.5, borderColor: colors.hairline,
  },
  btnBackText: { ...typography.button, color: colors.ink },
  btnNext: {
    paddingVertical: 12, paddingHorizontal: spacing.xl,
    borderRadius: radius.full, backgroundColor: colors.primary,
  },
  btnNextText: { ...typography.button, color: colors.onPrimary },
});
