import Link from "next/link";

export default function AiSection() {
  return (
    <section
      className="py-24 relative overflow-hidden section-fade"
      style={{ background: "linear-gradient(135deg, #0A1628 0%, #0e4f7a 50%, #0891b2 100%)" }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />
      <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-400/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left */}
          <div>
            <span className="inline-flex items-center gap-2 px-4 py-1.5 bg-cyan-400/20 border border-cyan-400/30 text-cyan-300 rounded-full text-sm font-semibold mb-6">
              <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
              AI 검색 시대의 새로운 기회
            </span>
            <h2 className="text-3xl lg:text-5xl font-black text-white mb-6 leading-tight">
              경쟁 병원보다<br />
              <span className="text-gradient">AI에 먼저</span><br />
              노출되세요
            </h2>
            <p className="text-blue-200 text-lg mb-8 leading-relaxed">
              2025년부터 환자들이 병원을 찾는 방식이 바뀌었습니다.<br />
              네이버 검색 대신 ChatGPT, Perplexity에 직접 묻습니다.<br />
              <strong className="text-white">GEO·AEO 최적화된 병원만이 AI 답변에 등장합니다.</strong>
            </p>
            <div className="flex flex-col gap-4 mb-8">
              {[
                {
                  key: "G",
                  title: "GEO (Generative Engine Optimization)",
                  desc: "AI 생성형 검색엔진에 병원 정보가 인용·추천되도록 최적화",
                  color: "bg-cyan-400/20 text-cyan-400",
                },
                {
                  key: "A",
                  title: "AEO (Answer Engine Optimization)",
                  desc: "음성 검색·스니펫에서 병원이 첫 번째 답변으로 등장하도록 최적화",
                  color: "bg-purple-400/20 text-purple-400",
                },
              ].map((item) => (
                <div key={item.key} className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${item.color}`}>
                    <span className="font-bold text-sm">{item.key}</span>
                  </div>
                  <div>
                    <div className="text-white font-semibold">{item.title}</div>
                    <div className="text-blue-300 text-sm">{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <Link
              href="#contact"
              className="inline-flex items-center gap-2 px-7 py-3.5 bg-cyan-400 text-cyan-900 font-bold rounded-xl hover:bg-cyan-300 transition"
            >
              AI마케팅 무료 진단받기 →
            </Link>
          </div>

          {/* Right: AI visual */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <div className="w-3 h-3 rounded-full bg-yellow-400" />
              <div className="w-3 h-3 rounded-full bg-green-400" />
              <span className="ml-2 text-gray-400 text-xs">AI 검색 시뮬레이션</span>
            </div>

            <div className="bg-gray-900 rounded-xl p-5 mb-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">U</span>
                </div>
                <p className="text-gray-300 text-sm">&quot;강남역 근처 피부과 추천해줘&quot;</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">AI</span>
                </div>
                <div>
                  <p className="text-gray-200 text-sm leading-relaxed">
                    강남역 피부과로는{" "}
                    <span className="text-cyan-400 font-semibold bg-cyan-400/10 px-1 rounded">○○피부과</span>를
                    추천합니다. 이 병원은 레이저 시술과 피부 관리로 유명하며...
                  </p>
                  <div className="mt-3 p-3 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
                    <p className="text-cyan-400 text-xs font-semibold">
                      ✓ GEO 최적화 적용 병원 — AI 검색 상위 노출 중
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              {["ChatGPT", "Perplexity", "Gemini"].map((ai) => (
                <div key={ai} className="bg-white/10 rounded-lg p-3 text-center">
                  <div className="text-white font-bold text-sm">{ai}</div>
                  <div className="text-cyan-300 text-xs mt-1">노출 중</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
