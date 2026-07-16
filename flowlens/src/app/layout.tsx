import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FlowLens — 행동 분석 SaaS",
  description: "개인정보 보호형 웹 행동 분석 및 전환 개선 리포트 (대행사용 MVP)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
