import { prisma } from "@/lib/db";
import DemoLiveCount from "@/components/DemoLiveCount";

export const dynamic = "force-dynamic";

// 추적 SDK를 실제로 로드해 이벤트가 수집되는지 확인하는 데모 페이지.
export default async function DemoPage() {
  const site = await prisma.site.findFirst({ orderBy: { createdAt: "asc" } });
  const siteKey = site?.siteKey ?? "";

  // 동적으로 t.js를 삽입 (currentScript에 data-site가 정확히 잡히도록 appendChild 방식 사용)
  const loader = `(function(){var s=document.createElement('script');s.async=true;s.src='/t.js';s.setAttribute('data-site','${siteKey}');document.head.appendChild(s);})();`;

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "28px 20px 80px" }}>
      <script dangerouslySetInnerHTML={{ __html: loader }} />

      <div className="brand" style={{ marginBottom: 8 }}><span className="dot" /> FlowLens 추적 데모</div>
      <div className="notice" style={{ marginBottom: 20 }}>
        이 페이지에는 실제 추적 스크립트(<code>/t.js</code>)가 설치되어 있습니다. 아래 요소를 클릭·스크롤하면
        그 행동이 <b>실시간으로 감지</b>됩니다(위 카운터). 이름·연락처 등 입력값과 IP는 수집하지 않습니다.
      </div>

      <DemoLiveCount />

      {/* 가짜 상품 랜딩 */}
      <div className="card card-pad" style={{ marginTop: 20 }}>
        <h2 style={{ fontSize: 22, marginBottom: 8 }}>여름 리넨 셔츠</h2>
        <p className="muted">가볍고 시원한 소재. 지금 20% 할인 중.</p>
        <div style={{ height: 180, background: "linear-gradient(135deg,#eef2fb,#e4ecfb)", borderRadius: 12, margin: "16px 0", display: "grid", placeItems: "center", color: "#7c88a3" }}>
          상품 이미지 (클릭해도 반응 없음 → dead click 유발)
        </div>
        <div className="row">
          <button className="btn primary" data-cta>구매하기</button>
          <button className="btn">장바구니</button>
          <a className="btn" href="#reviews">리뷰 보기</a>
        </div>
      </div>

      {/* 스크롤 유도용 긴 콘텐츠 */}
      <div className="card card-pad" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 8 }}>상세 설명</h3>
        <p className="muted">아래로 스크롤하면 스크롤 도달 이벤트가 수집됩니다.</p>
        {Array.from({ length: 6 }).map((_, i) => (
          <p key={i} className="muted small" style={{ lineHeight: 2 }}>
            소재와 핏, 세탁 방법에 대한 설명 문단 {i + 1}. 방문자가 어디까지 읽는지 스크롤 도달률로 측정합니다.
            핵심 정보가 너무 아래에 있으면 개선 제안이 자동으로 생성됩니다.
          </p>
        ))}
      </div>

      {/* 폼 (입력값은 수집되지 않음) */}
      <div className="card card-pad" id="reviews" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 8 }}>문의하기</h3>
        <p className="muted small" style={{ marginTop: 0 }}>입력 내용은 수집되지 않습니다. 폼 시작/제출 신호만 기록됩니다.</p>
        <form onSubmit={undefined} action="#reviews" method="get">
          <div className="field"><label>이름</label><input name="name" placeholder="홍길동" /></div>
          <div className="field"><label>이메일</label><input name="email" placeholder="test@example.com" /></div>
          <button className="btn primary" type="submit" data-cta>문의 보내기</button>
        </form>
      </div>

      <p className="muted small" style={{ marginTop: 20, textAlign: "center" }}>
        여러 번 클릭하고 스크롤한 뒤 <a href="/dashboard" style={{ color: "var(--accent)" }}>대시보드</a>에서 확인하세요.
      </p>
    </div>
  );
}
