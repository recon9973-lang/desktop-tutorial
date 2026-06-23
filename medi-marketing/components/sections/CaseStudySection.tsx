const CASES = [
  {
    initial: "치",
    color: "bg-blue-600",
    name: "서울 강남 ○○치과",
    sub: "임플란트 전문",
    stats: [{ val: "+420%", label: "네이버 트래픽" }, { val: "+280%", label: "신규 상담 건수" }],
    quote: "임플란트 키워드로 ChatGPT에서도 추천되기 시작했습니다. GEO 효과를 직접 체감했어요.",
    bg: "from-blue-50 to-indigo-50 border-blue-100",
    textColor: "text-blue-600",
  },
  {
    initial: "피",
    color: "bg-purple-600",
    name: "부산 해운대 ○○피부과",
    sub: "레이저·보톡스 전문",
    stats: [{ val: "1위", label: "부산 피부과 검색" }, { val: "+195%", label: "예약 건수" }],
    quote: "블로그 운영 6개월 만에 네이버 1위를 달성했습니다. 이제 광고비를 절반으로 줄였어요.",
    bg: "from-purple-50 to-pink-50 border-purple-100",
    textColor: "text-purple-600",
  },
  {
    initial: "정",
    color: "bg-emerald-600",
    name: "인천 ○○정형외과",
    sub: "도수치료 전문",
    stats: [{ val: "+312%", label: "오가닉 유입" }, { val: "3배", label: "월 매출 증가" }],
    quote: "홈페이지 제작부터 SEO까지 원스톱으로 진행해서 정말 편리했습니다.",
    bg: "from-emerald-50 to-cyan-50 border-emerald-100",
    textColor: "text-emerald-600",
  },
];

export default function CaseStudySection() {
  return (
    <section className="py-24 bg-white section-fade">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 bg-emerald-100 text-emerald-700 rounded-full text-sm font-semibold mb-4">
            성공 사례
          </span>
          <h2 className="text-3xl lg:text-4xl font-black text-gray-900 mb-4">
            실제 파트너 병원의 성과
          </h2>
          <p className="text-gray-500 text-lg">숫자가 증명하는 결과입니다</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {CASES.map((c) => (
            <div key={c.name} className={`card-hover bg-gradient-to-br ${c.bg} rounded-2xl p-7 border`}>
              <div className="flex items-center gap-3 mb-5">
                <div className={`w-10 h-10 ${c.color} rounded-xl flex items-center justify-center`}>
                  <span className="text-white font-bold text-sm">{c.initial}</span>
                </div>
                <div>
                  <div className="font-bold text-gray-900">{c.name}</div>
                  <div className="text-gray-400 text-xs">{c.sub}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-5">
                {c.stats.map((s) => (
                  <div key={s.label}>
                    <div className={`text-2xl font-black ${c.textColor}`}>{s.val}</div>
                    <div className="text-xs text-gray-500">{s.label}</div>
                  </div>
                ))}
              </div>
              <p className="text-gray-600 text-sm leading-relaxed">&quot;{c.quote}&quot;</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
