import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';

import { SkipLink } from '@/components/SkipLink';
import { siteUrl } from '@/lib/site';

import '@veo/ui/tokens.css';
import './globals.css';

const TITLE = 'VEO — SEO · GEO · 네이버 키워드 인텔리전스 플랫폼';
const DESCRIPTION =
  'VEO는 검색엔진과 AI 답변 엔진이 사이트를 읽을 수 있는 상태인지 점검하고, 네이버 검색 수요를 출처와 함께 보여줍니다. 개발 VENOM, 연구·방법론 VEO-LAB.';

export const metadata: Metadata = {
  // `metadataBase` 가 있어야 아래 상대 주소들이 절대 주소로 나간다. 없으면 Next 가
  // canonical 과 오픈그래프 주소를 아예 안 내보낸다 — 2026-08-06 실측에서 우리
  // 진단이 우리 사이트를 "canonical 누락" 으로 잡은 원인이 이것이었다.
  metadataBase: new URL(siteUrl()),
  title: { default: TITLE, template: '%s | VEO' },
  description: DESCRIPTION,
  applicationName: 'VEO',
  authors: [{ name: 'VENOM' }],
  creator: 'VENOM',
  publisher: 'VENOM',
  // 이 페이지의 진짜 주소. 같은 내용이 여러 주소로 열릴 때 어느 것이 원본인지
  // 검색엔진에게 알린다. 하위 페이지는 각자 덮어쓴다.
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    siteName: 'VEO',
    locale: 'ko_KR',
    url: '/',
    title: TITLE,
    description: DESCRIPTION,
  },
  twitter: { card: 'summary', title: TITLE, description: DESCRIPTION },
};

/**
 * 이 사이트가 무엇이고 누가 만들었는지, 기계가 읽는 형태로.
 *
 * 2026-08-06 실측: 우리 진단이 우리 사이트에서 "수집한 페이지 어디에도 구조화
 * 데이터 선언이 없습니다" 를 잡아냈다. 구조화 데이터를 점검해 주는 도구가 자기
 * 페이지에는 하나도 두지 않은 상태였다.
 *
 * 지어내지 않는다 — 여기 적는 것은 전부 이미 화면과 `/bot` 에 적혀 있는 사실이다.
 */
const JSON_LD = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'WebSite',
      '@id': `${siteUrl()}/#website`,
      url: `${siteUrl()}/`,
      name: 'VEO',
      description: DESCRIPTION,
      inLanguage: 'ko-KR',
      publisher: { '@id': `${siteUrl()}/#organization` },
    },
    {
      '@type': 'Organization',
      '@id': `${siteUrl()}/#organization`,
      name: 'VENOM',
      url: `${siteUrl()}/`,
      description: 'VEO 를 개발·운영하는 곳. 방법론은 VEO-LAB.',
    },
  ],
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
        <script
          type="application/ld+json"
          // 우리가 만든 상수 하나를 직렬화한 것이다. 사용자 입력이 섞이지 않는다.
          dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
        />
      </body>
    </html>
  );
}
