import { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Switch, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useLocalSearchParams, router } from 'expo-router';
import { colors, spacing, typography, radius } from '../lib/theme';
import { scheduleIntakeAlarm, cancelAlarm } from '../lib/notifications';

const HOURS   = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
const MINUTES = ['00', '15', '30', '45'];
const DAYS    = [
  { key: 'mon', label: '월' }, { key: 'tue', label: '화' }, { key: 'wed', label: '수' },
  { key: 'thu', label: '목' }, { key: 'fri', label: '금' }, { key: 'sat', label: '토' }, { key: 'sun', label: '일' },
];

export default function AlarmSetting() {
  const { id, name } = useLocalSearchParams();
  const [hour,   setHour]   = useState('08');
  const [minute, setMinute] = useState('00');
  const [days,   setDays]   = useState([]); // 빈 배열 = 매일
  const [active, setActive] = useState(true);

  const toggleDay = (key) =>
    setDays((prev) => prev.includes(key) ? prev.filter((d) => d !== key) : [...prev, key]);

  const handleSave = async () => {
    if (!active) {
      Alert.alert('알람 해제', '알람을 끄시겠어요?', [
        { text: '취소', style: 'cancel' },
        { text: '끄기', onPress: () => router.back() },
      ]);
      return;
    }

    const time = `${hour}:${minute}`;
    const selectedDays = days.length === 0 || days.length === 7 ? [] : days;

    try {
      const notificationId = await scheduleIntakeAlarm(name, time, selectedDays);

      // supplements 목록에 알람 정보 저장
      const raw = await AsyncStorage.getItem('my_supplements');
      const supps = raw ? JSON.parse(raw) : [];
      const updated = supps.map((s) => {
        if (s.id !== id) return s;
        const alarm = { time, days: selectedDays, notificationId };
        return { ...s, alarms: [...(s.alarms?.filter((a) => a.time !== time) ?? []), alarm] };
      });
      await AsyncStorage.setItem('my_supplements', JSON.stringify(updated));

      Alert.alert('알람 설정 완료', `${name} 알람이 매일 ${time}에 울립니다`, [
        { text: '확인', onPress: () => router.back() },
      ]);
    } catch (e) {
      Alert.alert('알람 설정 실패', e.message);
    }
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.canvasSoft }} contentContainerStyle={{ padding: spacing.lg, paddingBottom: 80 }}>
      <Text style={[typography.heading2, { color: colors.ink, marginBottom: 4 }]}>복용 알람</Text>
      <Text style={[typography.bodySm, { color: colors.inkMuted, marginBottom: spacing.xl }]}>
        {name} 복용 시간을 설정해주세요
      </Text>

      {/* Active toggle */}
      <View style={[s.card, { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }]}>
        <View>
          <Text style={[typography.title, { color: colors.ink }]}>알람 사용</Text>
          <Text style={[typography.caption, { color: colors.inkFaint }]}>앱 푸시 + 카카오 알림톡</Text>
        </View>
        <Switch value={active} onValueChange={setActive} trackColor={{ true: colors.primary, false: colors.hairline }} />
      </View>

      {active && (
        <>
          {/* Time picker */}
          <View style={s.card}>
            <Text style={[typography.title, { marginBottom: spacing.md }]}>복용 시간</Text>
            <View style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}>
              {/* Hour */}
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ maxWidth: '50%' }}>
                <View style={{ flexDirection: 'row', gap: 6 }}>
                  {HOURS.map((h) => (
                    <TouchableOpacity key={h} style={[s.timePill, hour === h && s.timePillActive]} onPress={() => setHour(h)}>
                      <Text style={[s.timePillText, hour === h && s.timePillTextActive]}>{h}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </ScrollView>
              <Text style={[typography.heading2, { color: colors.ink }]}>:</Text>
              {/* Minute */}
              <View style={{ flexDirection: 'row', gap: 6 }}>
                {MINUTES.map((m) => (
                  <TouchableOpacity key={m} style={[s.timePill, minute === m && s.timePillActive]} onPress={() => setMinute(m)}>
                    <Text style={[s.timePillText, minute === m && s.timePillTextActive]}>{m}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
            <View style={{ backgroundColor: colors.canvasSoft, borderRadius: radius.md, padding: spacing.sm, marginTop: spacing.md }}>
              <Text style={[typography.title, { color: colors.primary, textAlign: 'center' }]}>
                ⏰ {hour}:{minute}
              </Text>
            </View>
          </View>

          {/* Day picker */}
          <View style={s.card}>
            <Text style={[typography.title, { marginBottom: 4 }]}>반복 요일</Text>
            <Text style={[typography.caption, { color: colors.inkFaint, marginBottom: spacing.md }]}>선택 없음 = 매일</Text>
            <View style={{ flexDirection: 'row', gap: 6 }}>
              {DAYS.map((d) => {
                const on = days.includes(d.key);
                return (
                  <TouchableOpacity key={d.key} style={[s.dayPill, on && s.dayPillActive]} onPress={() => toggleDay(d.key)}>
                    <Text style={[s.dayPillText, on && s.dayPillTextActive]}>{d.label}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          {/* Dual channel notice */}
          <View style={{ backgroundColor: 'rgba(0,117,222,0.05)', borderRadius: radius.lg, borderWidth: 1, borderColor: 'rgba(0,117,222,0.12)', padding: spacing.md }}>
            <Text style={[typography.bodySm, { color: colors.inkSecondary, lineHeight: 20 }]}>
              📱 <Text style={{ fontWeight: '600' }}>앱 푸시</Text> + 💬 <Text style={{ fontWeight: '600' }}>카카오 알림톡</Text> 이중 채널로 알려드려요.{'\n'}앱을 삭제하셔도 카카오톡으로 계속 받을 수 있습니다.
            </Text>
          </View>
        </>
      )}

      <TouchableOpacity style={s.saveBtn} onPress={handleSave}>
        <Text style={s.saveBtnText}>{active ? '알람 저장' : '알람 끄기'}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  card: {
    backgroundColor: colors.surface, borderRadius: radius.xl,
    borderWidth: 1, borderColor: colors.hairline,
    padding: spacing.lg, marginBottom: 10,
  },
  timePill: {
    paddingHorizontal: 10, paddingVertical: 7,
    borderRadius: radius.md, borderWidth: 1, borderColor: colors.hairline,
    backgroundColor: colors.canvasSoft,
  },
  timePillActive:     { backgroundColor: colors.primary, borderColor: colors.primary },
  timePillText:       { ...typography.caption, color: colors.inkMuted, fontWeight: '600' },
  timePillTextActive: { color: '#fff' },

  dayPill:            { width: 38, height: 38, borderRadius: radius.full, borderWidth: 1.5, borderColor: colors.hairline, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  dayPillActive:      { backgroundColor: colors.primary, borderColor: colors.primary },
  dayPillText:        { ...typography.caption, color: colors.inkMuted, fontWeight: '600' },
  dayPillTextActive:  { color: '#fff' },

  saveBtn:     { backgroundColor: colors.primary, borderRadius: radius.full, padding: 14, alignItems: 'center', marginTop: spacing.md },
  saveBtnText: { ...typography.button, color: colors.onPrimary },
});
