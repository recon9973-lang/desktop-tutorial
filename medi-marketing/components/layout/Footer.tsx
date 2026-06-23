import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-gray-950 text-gray-400 pt-16 pb-8">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">M</span>
              </div>
              <span className="font-bold text-lg text-white">메디마케팅</span>
            </Link>
            <p className="text-sm leading-relaxed mb-4">병원 성장을 위한<br />AI 기반 통합 마케팅 파트너</p>
            <div className="flex gap-3">
              {["facebook", "instagram", "youtube"].map((sns) => (
                <a key={sns} href="#" aria-label={sns}
                  className="w-8 h-8 bg-gray-800 hover:bg-blue-600 rounded-lg flex items-center justify-center transition text-xs font-bold text-white">
                  {sns[0].toUpperCase()}
                </a>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">병원마케팅</h4>
            <ul className="space-y-2 text-sm">
              {["치과마케팅","피부과마케팅","정형외과마케팅","한의원마케팅","성형외과마케팅"].map(l => (
                <li key={l}><a href="#" className="hover:text-white transition">{l}</a></li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">온라인마케팅</h4>
            <ul className="space-y-2 text-sm">
              {["파워링크","브랜드검색광고","인스타그램","당근마켓","언론홍보"].map(l => (
                <li key={l}><a href="#" className="hover:text-white transition">{l}</a></li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">홈페이지 제작</h4>
            <ul className="space-y-2 text-sm">
              {["기본형","중급형","고급형","SEO 패키지","반응형/적응형"].map(l => (
                <li key={l}><a href="#" className="hover:text-white transition">{l}</a></li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">AI마케팅</h4>
            <ul className="space-y-2 text-sm">
              {["GEO 최적화","AEO 최적화","SEO 최적화","콘텐츠 SEO","테크니컬 SEO"].map(l => (
                <li key={l}><a href="#" className="hover:text-white transition">{l}</a></li>
              ))}
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-800 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-start gap-4">
            <div className="text-xs space-y-1">
              <p>회사명: (주)메디마케팅 | 대표자: 홍길동 | 사업자등록번호: 000-00-00000</p>
              <p>주소: 서울특별시 강남구 테헤란로 000, 00층 | 대표전화: 02-0000-0000</p>
              <p className="text-gray-600">
                자료 출처:{" "}
                <a href="https://health.kdca.go.kr/healthinfo/" target="_blank" rel="noopener noreferrer"
                  className="text-blue-500 hover:underline">
                  질병관리청 국가건강정보포털
                </a>
              </p>
            </div>
            <div className="flex gap-4 text-xs">
              <a href="#" className="hover:text-white transition">개인정보처리방침</a>
              <a href="#" className="hover:text-white transition">이용약관</a>
              <a href="#" className="hover:text-white transition">자료실</a>
            </div>
          </div>
          <p className="text-xs text-gray-600 mt-4">© 2024 메디마케팅. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
