import { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { colors, spacing, typography, radius, durColor, durLabel } from '../lib/theme';
import { scheduleIntakeAlarm, cancelAlarm } from '../lib/notifications';

const STORAGE_KEY = 'my_supplements';

export default function MySupplements() {
  const [supplements, setSupplements] = useState([]);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((raw) => {
      if (raw) setSupplements(JSON.parse(raw));
    });
  }, []);

  const save = async (list) => {
    setSupplements(list);
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  };

  const addSupplement = async () => {
    // 추천 결과에서 등록하는 흐름. 여기선 데모용으로 바로 추가
    const demo = {
      id: Date.now().toString(),
      name: '오메가3', ingredient_id: 'omega3',
      product_name: '○○ 알티지 오메가3 1000mg',
      started_at: new Date().toISOString().split('T')[0],
      duration_type: 'continuous',
      alarms: [],
    };
    const next = [...supplements, demo];
    await save(next);
  };

  const removeSupp = (id) => {
    Alert.alert('삭제', '이 영양제를 목록에서 제거할까요?', [
      { text: '취소', style: 'cancel' },
      {
        text: '삭제', style: 'destructive', onPress: async () => {
          const supp = supplements.find((s) => s.id === id);
          if (supp?.alarms?.length) {
            await Promise.all(supp.alarms.map((a) => cancelAlarm(a.notificationId).catch(() => {})));
          }
          await save(supplements.filter((s) => s.id !== id));
        },
      },
    ]);
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.canvasSoft }} contentContainerStyle={{ padding: spacing.lg, paddingBottom: 48 }}>
      <Text style={[typography.heading2, { color: colors.ink, marginBottom: 4 }]}>내 영양제</Text>
      <Text style={[typography.bodySm, { color: colors.inkMuted, marginBottom: spacing.xl }]}>
        등록한 영양제의 조합 충돌 · 복용 알람을 관리해요
      </Text>

      {supplements.length === 0 ? (
        <View style={s.empty}>
          <Text style={{ fontSize: 40, marginBottom: spacing.sm }}>💊</Text>
          <Text style={[typography.title, { color: colors.inkMuted, marginBottom: 4 }]}>아직 등록된 영양제가 없어요</Text>
          <Text style={[typography.caption, { color: colors.inkFaint, textAlign: 'center' }]}>
            추천 결과에서 등록하거나{'\n'}아래 버튼으로 직접 추가하세요
          </Text>
        </View>
      ) : (
        supplements.map((supp) => (
          <SuppCard key={supp.id} supp={supp} onDelete={() => removeSupp(supp.id)} onAlarm={() => router.push({ pathname: '/alarm', params: { id: supp.id, name: supp.name } })} supplements={supplements} save={save} />
        ))
      )}

      <TouchableOpacity style={s.addBtn} onPress={addSupplement}>
        <Text style={s.addBtnText}>+ 영양제 추가 (데모)</Text>
      </TouchableOpacity>

      <TouchableOpacity style={[s.addBtn, { backgroundColor: colors.surface, borderColor: colors.hairline }]} onPress={() => router.push('/survey')}>
        <Text style={[s.addBtnText, { color: colors.ink }]}>🧬 추천 다시 받기</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

function SuppCard({ supp, onDelete, onAlarm, supplements, save }) {
  const hasConflict = checkConflict(supp, supplements);

  return (
    <View style={s.card}>
      <View style={{ flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <View style={{ flex: 1 }}>
          <Text style={[typography.title, { color: colors.ink }]}>{supp.name}</Text>
          <Text style={[typography.caption, { color: colors.inkFaint, marginTop: 2 }]}>{supp.product_name}</Text>
        </View>
        <TouchableOpacity onPress={onDelete} style={{ padding: 4 }}>
          <Text style={{ color: colors.inkFaint, fontSize: 18 }}>×</Text>
        </TouchableOpacity>
      </View>

      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: spacing.sm }}>
        <View style={{ backgroundColor: `${durColor[supp.duration_type]}18`, borderRadius: radius.full, paddingHorizontal: 8, paddingVertical: 2 }}>
          <Text style={{ ...typography.eyebrow, color: durColor[supp.duration_type] }}>
            {durLabel[supp.duration_type]}
          </Text>
        </View>
        <Text style={[typography.caption, { color: colors.inkFaint }]}>시작 {supp.started_at}</Text>
      </View>

      {hasConflict && (
        <View style={{ backgroundColor: '#fff8f0', borderRadius: radius.sm, padding: spacing.xs, marginTop: spacing.xs }}>
          <Text style={{ ...typography.caption, color: colors.accentOrange }}>
            ⚠️ {hasConflict}
          </Text>
        </View>
      )}

      {/* Alarms */}
      <View style={{ marginTop: spacing.sm, gap: 6 }}>
        {supp.alarms?.map((a, i) => (
          <View key={i} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.canvasSoft, borderRadius: radius.md, padding: spacing.xs }}>
            <Text style={[typography.bodySm, { color: colors.inkSecondary }]}>⏰ {a.time}</Text>
            <Text style={[typography.caption, { color: colors.inkFaint }]}>{a.days?.join(', ') || '매일'}</Text>
          </View>
        ))}
      </View>

      <TouchableOpacity style={s.alarmBtn} onPress={onAlarm}>
        <Text style={s.alarmBtnText}>
          {supp.alarms?.length ? '⏰ 알람 수정' : '+ 알람 설정'}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

// 조합 충돌 간이 체크 (상호작용 매트릭스 기반)
const CONFLICTS = { calcium: 'iron', iron: 'calcium', zinc: 'calcium' };
function checkConflict(supp, all) {
  const otherId = CONFLICTS[supp.ingredient_id];
  if (!otherId) return null;
  if (all.some((s) => s.ingredient_id === otherId && s.id !== supp.id)) {
    const names = { calcium: '칼슘', iron: '철분', zinc: '아연' };
    return `${names[supp.ingredient_id]}과 ${names[otherId]}은 2시간 이상 간격을 두세요`;
  }
  return null;
}

const s = StyleSheet.create({
  card: {
    backgroundColor: colors.surface, borderRadius: radius.xl,
    borderWidth: 1, borderColor: colors.hairline,
    padding: spacing.lg, marginBottom: 10,
  },
  empty: {
    backgroundColor: colors.canvasSoft, borderRadius: radius.xl,
    padding: spacing.xxl, alignItems: 'center', marginBottom: spacing.lg,
  },
  addBtn: {
    backgroundColor: colors.primary, borderRadius: radius.full,
    padding: 13, alignItems: 'center', marginBottom: 10,
    borderWidth: 1.5, borderColor: 'transparent',
  },
  addBtnText: { ...typography.button, color: colors.onPrimary },
  alarmBtn: {
    marginTop: spacing.sm, borderWidth: 1, borderColor: colors.hairline,
    borderRadius: radius.full, paddingVertical: 8, alignItems: 'center',
  },
  alarmBtnText: { ...typography.bodySm, color: colors.primary, fontWeight: '600' },
});
