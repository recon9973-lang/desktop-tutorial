import Link from "next/link";

const SPECIALTIES = [
  { emoji: "🦷", title: "치과마케팅", sub: "임플란트·교정·미백 특화", href: "/hospital-marketing/dental" },
  { emoji: "✨", title: "피부과마케팅", sub: "레이저·보톡스·필러 특화", href: "/hospital-marketing/dermatology" },
  { emoji: "🦴", title: "정형외과마케팅", sub: "도수치료·비수술 특화", href: "/hospital-marketing/orthopedics" },
  { emoji: "🌿", title: "한의원마케팅", sub: "침·추나·다이어트 특화", href: "/hospital-marketing/oriental" },
  { emoji: "💉", title: "성형외과마케팅", sub: "쌍꺼풀·코·윤곽 특화", href: "/hospital-marketing/plastic-surgery" },
  { emoji: "🫀", title: "내과마케팅", sub: "건강검진·만성질환 특화", href: "/hospital-marketing/internal-medicine" },
  { emoji: "👁️", title: "안과마케팅", sub: "라식·라섹·백내장 특화", href: "/hospital-marketing/ophthalmology" },
  { emoji: "🔬", title: "의료기기마케팅", sub: "B2B 병원 대상 특화", href: "/hospital-marketing/medical-device" },
];

export default function SpecialtySection() {
  return (
    <section className="py-24 bg-white section-fade">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold mb-4">
            병과별 전문 마케팅
          </span>
          <h2 className="text-3xl lg:text-4xl font-black text-gray-900 mb-4">
            담당 병과를 선택하세요
          </h2>
          <p className="text-gray-500 text-lg">
            병과별 환자 검색 패턴과 경쟁 환경이 다릅니다. 맞춤 전략이 필요합니다.
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {SPECIALTIES.map((s) => (
            <Link
              key={s.title}
              href={s.href}
              className="card-hover text-center bg-white border border-gray-200 rounded-2xl p-6 hover:border-blue-400 hover:shadow-lg hover:shadow-blue-500/10 transition"
            >
              <div className="text-4xl mb-3">{s.emoji}</div>
              <h3 className="font-bold text-gray-900 mb-1 text-sm">{s.title}</h3>
              <p className="text-gray-400 text-xs">{s.sub}</p>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
