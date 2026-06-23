import Link from "next/link";
import { Check, Minus } from "lucide-react";

const PLANS = [
  {
    name: "기본형",
    price: "290",
    sub: "소규모 의원·개원 초기",
    features: [
      { text: "반응형 홈페이지 (5페이지)", included: true },
      { text: "진료 안내 · 예약 폼", included: true },
      { text: "네이버 플레이스 연동", included: true },
      { text: "기본 SEO 설정", included: true },
      { text: "AEO/GEO 최적화", included: false },
      { text: "콘텐츠 발행", included: false },
    ],
    featured: false,
    href: "/website/basic",
  },
  {
    name: "중급형 + SEO + AEO + GEO",
    price: "590",
    sub: "성장 중인 병원 · 경쟁 심화 지역",
    features: [
      { text: "반응형 홈페이지 (10페이지)", included: true },
      { text: "예약·진료일정 시스템", included: true },
      { text: "네이버·카카오 연동", included: true },
      { text: "SEO 풀 최적화", included: true },
      { text: "GEO·AEO 최적화 (키워드 2개)", included: true },
      { text: "월 콘텐츠 발행 8건", included: true },
    ],
    featured: true,
    badge: "🔥 가장 인기",
    href: "/website/pkg-b",
  },
  {
    name: "고급형 풀 패키지",
    price: "990",
    sub: "대형 병원 · 브랜딩 필요",
    features: [
      { text: "고급형 커스텀 디자인", included: true },
      { text: "과별 상세 페이지 무제한", included: true },
      { text: "전체 채널 연동", included: true },
      { text: "SEO + GEO + AEO (키워드 4개)", included: true },
      { text: "월 콘텐츠 발행 16건", included: true },
      { text: "전담 마케터 + 월간 전략회의", included: true },
    ],
    featured: false,
    href: "/website/pkg-f",
  },
];

export default function PricingSection() {
  return (
    <section className="py-24 bg-gray-50 section-fade">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold mb-4">
            홈페이지 제작 패키지
          </span>
          <h2 className="text-3xl lg:text-4xl font-black text-gray-900 mb-4">
            투명한 가격, 확실한 성과
          </h2>
          <p className="text-gray-500 text-lg">모든 패키지에 반응형·병원 특화 기능이 기본 포함됩니다</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6 items-start">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-2xl p-8 ${
                plan.featured
                  ? "text-white shadow-2xl shadow-blue-500/30"
                  : "bg-white border border-gray-200"
              } ${plan.featured ? "lg:scale-105" : ""}`}
              style={plan.featured ? { background: "linear-gradient(145deg, #1e3a8a, #1d4ed8)" } : {}}
            >
              {plan.badge && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1.5 bg-amber-400 text-amber-900 text-xs font-bold rounded-full whitespace-nowrap">
                  {plan.badge}
                </div>
              )}
              <div className={`text-sm font-semibold mb-2 ${plan.featured ? "text-blue-300" : "text-gray-500"}`}>
                {plan.name}
              </div>
              <div className={`text-4xl font-black mb-1 ${plan.featured ? "text-white" : "text-gray-900"}`}>
                {plan.price}
                <span className={`text-lg font-normal ${plan.featured ? "text-blue-300" : "text-gray-500"}`}>만원~</span>
              </div>
              <p className={`text-sm mb-6 ${plan.featured ? "text-blue-200" : "text-gray-400"}`}>{plan.sub}</p>
              <ul className="space-y-3 mb-8">
                {plan.features.map((f) => (
                  <li key={f.text} className="flex items-center gap-2 text-sm">
                    {f.included ? (
                      <Check className={`w-4 h-4 flex-shrink-0 ${plan.featured ? "text-cyan-400" : "text-green-500"}`} />
                    ) : (
                      <Minus className="w-4 h-4 flex-shrink-0 text-gray-300" />
                    )}
                    <span className={f.included ? (plan.featured ? "text-white" : "text-gray-700") : "text-gray-400"}>
                      {f.text}
                    </span>
                  </li>
                ))}
              </ul>
              <Link
                href={plan.href}
                className={`block w-full text-center py-3 font-semibold rounded-xl transition ${
                  plan.featured
                    ? "bg-cyan-400 text-cyan-900 hover:bg-cyan-300"
                    : "border-2 border-blue-600 text-blue-600 hover:bg-blue-600 hover:text-white"
                }`}
              >
                {plan.featured ? "상담 신청하기 →" : "상담 신청"}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
