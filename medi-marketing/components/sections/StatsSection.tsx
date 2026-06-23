const STATS = [
  { value: "500+", label: "누적 파트너 병원" },
  { value: "8년", label: "병원마케팅 전문 운영" },
  { value: "92%", label: "목표 달성률" },
  { value: "1위", label: "GEO·AEO 병원 적용" },
];

export default function StatsSection() {
  return (
    <section className="py-16 bg-white section-fade">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 text-center">
          {STATS.map((s) => (
            <div key={s.label}>
              <div className="text-4xl lg:text-5xl font-black text-blue-600 mb-2">{s.value}</div>
              <div className="text-gray-500 text-sm font-medium">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
