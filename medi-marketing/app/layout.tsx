import type { Metadata } from "next";
import { Noto_Sans_KR } from "next/font/google";
import "./globals.css";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";

const noto = Noto_Sans_KR({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "메디마케팅 - 병원마케팅 전문 대행사 | GEO·AEO·SEO 통합 전략",
  description:
    "치과·피부과·정형외과 등 8개 병과 전문 마케팅. ChatGPT·네이버·구글 AI 검색 최적화(GEO·AEO·SEO). 병원홈페이지 제작부터 통합 마케팅까지 원스톱 솔루션.",
  keywords: "병원마케팅, 치과마케팅, 피부과마케팅, GEO, AEO, SEO, 병원홈페이지제작",
  openGraph: {
    title: "메디마케팅 - 병원마케팅 전문 대행사",
    description: "AI 시대 병원마케팅 선도. GEO·AEO·SEO 통합 전략으로 경쟁 병원보다 먼저 노출되세요.",
    type: "website",
    locale: "ko_KR",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="h-full">
      <body className={`${noto.className} min-h-full flex flex-col antialiased`}>
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
