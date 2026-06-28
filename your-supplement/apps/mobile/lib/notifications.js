// 앱 푸시 알림 — Expo Notifications
// 카카오 알림톡과 이중 채널: 사용자가 앱을 설치한 경우 앱 푸시, 미설치 시 카카오로 폴백
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

// 푸시 권한 요청 + Expo push token 반환
export async function registerForPushNotifications() {
  if (!Device.isDevice) return null; // 시뮬레이터에서는 토큰 발급 불가

  const { status: existing } = await Notifications.getPermissionsAsync();
  let finalStatus = existing;

  if (existing !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }
  if (finalStatus !== 'granted') return null;

  const projectId = Constants.expoConfig?.extra?.eas?.projectId;
  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  return token;
}

/**
 * 특정 시간에 반복 로컬 알람 예약
 * @param {string} supplementName - "오메가3"
 * @param {string} time - "08:00"
 * @param {string[]} days - ["monday", "tuesday", ...] (빈 배열 = 매일)
 * @returns {string} notificationId — 취소 시 사용
 */
export async function scheduleIntakeAlarm(supplementName, time, days = []) {
  const [hour, minute] = time.split(':').map(Number);

  // 매일 반복이면 daily trigger, 요일 지정이면 weekly trigger 반복 등록
  if (days.length === 0 || days.length === 7) {
    return Notifications.scheduleNotificationAsync({
      content: {
        title: '⏰ 영양제 드실 시간이에요',
        body: `${supplementName}을(를) 복용할 시간입니다`,
        sound: true,
      },
      trigger: { hour, minute, repeats: true },
    });
  }

  // 요일별 개별 등록 → ID 배열 반환
  const DAY_MAP = { sun: 1, mon: 2, tue: 3, wed: 4, thu: 5, fri: 6, sat: 7 };
  const ids = await Promise.all(
    days.map((day) =>
      Notifications.scheduleNotificationAsync({
        content: {
          title: '⏰ 영양제 드실 시간이에요',
          body: `${supplementName}을(를) 복용할 시간입니다`,
          sound: true,
        },
        trigger: { weekday: DAY_MAP[day] ?? 1, hour, minute, repeats: true },
      })
    )
  );
  return ids.join(',');
}

export async function cancelAlarm(notificationId) {
  const ids = notificationId.split(',');
  await Promise.all(ids.map((id) => Notifications.cancelScheduledNotificationAsync(id)));
}

export async function cancelAllAlarms() {
  await Notifications.cancelAllScheduledNotificationsAsync();
}
