import type { Metadata } from "next";
import "./globals.css";
import { siteJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  metadataBase: new URL("https://flow.seokorea.org"),
  title: {
    default: "FlowLens — 개인정보 보호형 웹 행동 분석",
    template: "%s | FlowLens",
  },
  description: "내 홈페이지 고객의 행동 패턴을 히트맵으로 분석하고 전환율을 올리세요. 개인정보 미수집 설계, 한국어 개선 리포트, 대행사 화이트라벨.",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: "FlowLens",
    locale: "ko_KR",
    url: "https://flow.seokorea.org",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        {/* 사이트 공통 구조화 데이터 (Organization + WebSite) — GEO/검색 신뢰도 */}
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: siteJsonLd() }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
