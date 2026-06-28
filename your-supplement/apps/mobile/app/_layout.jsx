import { Stack } from 'expo-router';
import { useEffect } from 'react';
import { StatusBar } from 'react-native';
import { registerForPushNotifications } from '../lib/notifications';
import { colors } from '../lib/theme';

export default function RootLayout() {
  useEffect(() => {
    registerForPushNotifications().then((token) => {
      if (token) {
        // TODO: 서버에 토큰 저장 → 서버사이드 알림 발송에 사용
        console.log('Expo push token:', token);
      }
    });
  }, []);

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor={colors.secondary} />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.canvas },
          headerTintColor: colors.ink,
          headerTitleStyle: { fontWeight: '700', fontSize: 17 },
          headerShadowVisible: false,
          contentStyle: { backgroundColor: colors.canvasSoft },
        }}
      >
        <Stack.Screen name="index" options={{ title: '당신의 영양제', headerShown: false }} />
        <Stack.Screen name="survey" options={{ title: '내 영양제 찾기', headerBackTitle: '' }} />
        <Stack.Screen name="result" options={{ title: '추천 결과', headerBackTitle: '' }} />
        <Stack.Screen name="my-supplements" options={{ title: '내 영양제', headerBackTitle: '' }} />
        <Stack.Screen name="alarm" options={{ title: '복용 알람', headerBackTitle: '' }} />
      </Stack>
    </>
  );
}
