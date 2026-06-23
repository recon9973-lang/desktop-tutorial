"use client";

import Link from "next/link";
import { CheckCircle } from "lucide-react";

export default function HeroSection() {
  return (
    <section
      className="relative min-h-screen flex items-center pt-16 overflow-hidden"
      style={{ background: "linear-gradient(135deg, #0A1628 0%, #1A3A6B 55%, #1e40af 100%)" }}
    >
      {/* Background decorations */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute top-1/2 -left-20 w-80 h-80 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute bottom-20 right-1/4 w-64 h-64 rounded-full bg-indigo-500/10 blur-3xl" />
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px)",
            backgroundSize: "32px 32px",
          }}
        />
      </div>

      <div className="max-w-7xl mx-auto px-6 py-20 relative z-10 w-full">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left */}
          <div>
            <div className="animate-hero-1">
              <span
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-white text-sm font-semibold mb-6"
                style={{ background: "linear-gradient(90deg, #06B6D4, #2563EB)" }}
              >
                ⭐ AI 시대 병원마케팅 선도
              </span>
            </div>

            <h1 className="animate-hero-2 text-4xl lg:text-6xl font-black text-white leading-tight mb-6">
              병원 매출을<br />
              올리는 가장<br />
              <span className="text-gradient">확실한 방법</span>
            </h1>

            <p className="animate-hero-3 text-lg text-blue-200 mb-10 leading-relaxed max-w-lg">
              SEO·GEO·AEO 통합 전략으로 ChatGPT, 네이버, 구글<br />
              모든 채널에서 경쟁 병원보다 먼저 노출되세요.
            </p>

            <div className="animate-hero-3 flex flex-wrap gap-4">
              <Link
                href="#contact"
                className="btn-pulse px-8 py-4 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-500/30 text-base"
              >
                무료 상담 신청하기 →
              </Link>
              <Link
                href="#services"
                className="px-8 py-4 bg-white/10 border border-white/20 text-white font-semibold rounded-xl hover:bg-white/20 transition text-base backdrop-blur-sm"
              >
                서비스 보기
              </Link>
            </div>

            <div className="mt-12 flex flex-wrap gap-6">
              {[
                "계약 후 2주 내 착수",
                "전담 마케터 1:1 배정",
                "월간 성과 리포트 제공",
              ].map((t) => (
                <div key={t} className="flex items-center gap-2 text-blue-200">
                  <CheckCircle className="w-5 h-5 text-cyan-400 flex-shrink-0" />
                  <span className="text-sm font-medium">{t}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Stats card */}
          <div className="hidden lg:block relative">
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8">
              <p className="text-blue-200 text-sm font-medium mb-6">
                📊 파트너 병원 평균 성과 (최근 12개월)
              </p>
              <div className="grid grid-cols-2 gap-6 mb-6">
                {[
                  { val: "+347%", label: "오가닉 트래픽 증가" },
                  { val: "+218%", label: "신규 환자 예약 증가" },
                  { val: "1위", label: "네이버 지역 검색 순위", cyan: true },
                  { val: "89%", label: "고객 재계약률" },
                ].map((s) => (
                  <div key={s.label} className="bg-white/10 rounded-xl p-5">
                    <div className={`text-3xl font-black mb-1 ${s.cyan ? "text-cyan-300" : "text-white"}`}>
                      {s.val}
                    </div>
                    <div className="text-blue-200 text-sm">{s.label}</div>
                  </div>
                ))}
              </div>

              {/* AI preview */}
              <div className="bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-400/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-5 h-5 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-xs font-bold">AI</span>
                  </div>
                  <span className="text-cyan-300 text-xs font-semibold">ChatGPT 검색 결과 노출 예시</span>
                </div>
                <p className="text-white/80 text-xs leading-relaxed">
                  "서울 강남구 피부과 추천"을 물어보면 AI가 먼저 추천하는 병원 —{" "}
                  <span className="text-cyan-300 font-semibold">GEO 최적화된 병원만 노출됩니다.</span>
                </p>
              </div>
            </div>

            <div className="absolute -top-4 -right-4 bg-amber-400 text-amber-900 font-bold text-sm px-4 py-2 rounded-full shadow-lg">
              🏆 2024 우수 대행사
            </div>
          </div>
        </div>
      </div>

      {/* Wave */}
      <div className="absolute bottom-0 left-0 right-0">
        <svg viewBox="0 0 1440 60" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M0 60L1440 60L1440 20C1200 60 960 0 720 20C480 40 240 0 0 20L0 60Z" fill="white" />
        </svg>
      </div>
    </section>
  );
}
