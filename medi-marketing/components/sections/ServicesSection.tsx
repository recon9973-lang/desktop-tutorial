import Link from "next/link";

const SERVICES = [
  {
    icon: "🏥",
    title: "병원마케팅",
    desc: "치과·피부과·정형외과 등 8개 병과별 맞춤 마케팅 전략",
    tags: ["치과", "피부과", "정형외과", "+5"],
    color: "blue",
    href: "/hospital-marketing",
  },
  {
    icon: "📊",
    title: "온라인마케팅",
    desc: "네이버 파워링크부터 SNS, 언론홍보까지 10개 채널 통합 운영",
    tags: ["파워링크", "인스타그램", "언론"],
    color: "purple",
    href: "/online-marketing",
  },
  {
    icon: "💻",
    title: "홈페이지 제작",
    desc: "예약·진료일정·네이버 연동 포함 병원 특화 홈페이지 + SEO 패키지",
    tags: ["반응형", "SEO포함", "예약연동"],
    color: "emerald",
    href: "/website",
  },
  {
    icon: "⚡",
    title: "AI마케팅",
    desc: "ChatGPT·Perplexity·Gemini AI 검색에 병원이 노출되는 GEO·AEO 전략",
    tags: ["GEO", "AEO", "SEO"],
    color: "ai",
    href: "/ai-marketing",
    badge: "NEW",
  },
];

const COLOR_MAP: Record<string, string> = {
  blue: "bg-blue-100 text-blue-600 group-hover:bg-blue-600 group-hover:text-white",
  purple: "bg-purple-100 text-purple-600 group-hover:bg-purple-600 group-hover:text-white",
  emerald: "bg-emerald-100 text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white",
};

const TAG_COLOR: Record<string, string> = {
  blue: "bg-blue-50 text-blue-600",
  purple: "bg-purple-50 text-purple-600",
  emerald: "bg-emerald-50 text-emerald-600",
};

export default function ServicesSection() {
  return (
    <section id="services" className="py-24 bg-gray-50 section-fade">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold mb-4">
            서비스 소개
          </span>
          <h2 className="text-3xl lg:text-4xl font-black text-gray-900 mb-4">
            병원 성장을 위한<br />통합 마케팅 솔루션
          </h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto">
            광고부터 AI 최적화까지, 하나의 파트너로 모든 것을 해결하세요
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {SERVICES.map((s) =>
            s.color === "ai" ? (
              <Link
                key={s.title}
                href={s.href}
                className="card-hover group rounded-2xl p-6 border-0 cursor-pointer"
                style={{ background: "linear-gradient(145deg, #0f172a, #1e3a8a)" }}
              >
                <div className="w-12 h-12 bg-cyan-400/20 rounded-xl flex items-center justify-center mb-5 text-2xl">
                  {s.icon}
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-lg font-bold text-white">{s.title}</h3>
                  {s.badge && (
                    <span className="px-2 py-0.5 bg-cyan-400/20 text-cyan-300 text-xs rounded-full font-bold border border-cyan-400/30">
                      {s.badge}
                    </span>
                  )}
                </div>
                <p className="text-blue-200 text-sm leading-relaxed mb-4">{s.desc}</p>
                <div className="flex flex-wrap gap-2">
                  {s.tags.map((t) => (
                    <span key={t} className="px-2 py-1 bg-cyan-400/20 text-cyan-300 text-xs rounded-md font-medium border border-cyan-400/20">
                      {t}
                    </span>
                  ))}
                </div>
              </Link>
            ) : (
              <Link
                key={s.title}
                href={s.href}
                className="card-hover group bg-white rounded-2xl p-6 border border-gray-200 hover:border-blue-300 cursor-pointer"
              >
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-5 text-2xl transition ${COLOR_MAP[s.color]}`}>
                  {s.icon}
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed mb-4">{s.desc}</p>
                <div className="flex flex-wrap gap-2">
                  {s.tags.map((t) => (
                    <span key={t} className={`px-2 py-1 text-xs rounded-md font-medium ${TAG_COLOR[s.color] ?? "bg-gray-100 text-gray-500"}`}>
                      {t}
                    </span>
                  ))}
                </div>
              </Link>
            )
          )}
        </div>
      </div>
    </section>
  );
}
