import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';

import { SkipLink } from '@/components/SkipLink';

import '@veo/ui/tokens.css';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'VEO — SEO · GEO · 네이버 키워드 인텔리전스 플랫폼',
    template: '%s | VEO',
  },
  description:
    'VEO는 검색엔진과 AI 답변 엔진이 사이트를 읽을 수 있는 상태인지 점검하고, 네이버 검색 수요를 출처와 함께 보여줍니다. 개발 VENOM, 연구·방법론 VEO-LAB.',
  applicationName: 'VEO',
  authors: [{ name: 'VENOM' }],
  creator: 'VENOM',
  publisher: 'VENOM',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <SkipLink />
        {children}
      </body>
    </html>
  );
}
