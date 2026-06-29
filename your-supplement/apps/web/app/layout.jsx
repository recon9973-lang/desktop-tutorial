import './globals.css';

export const metadata = {
  title: '당신의영양제',
  description: '식약처·논문 근거로 내 몸에 맞는 영양제를 추천받고, 최저가와 복용 알람까지.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        {/* Nav */}
        <nav style={{
          background: 'var(--canvas)', borderBottom: '1px solid var(--hairline)',
          padding: '0 var(--sp-lg)', position: 'sticky', top: 0, zIndex: 50,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56,
        }}>
          <a href="/" style={{ fontWeight: 700, fontSize: 18, color: 'var(--ink)', textDecoration: 'none', letterSpacing: -0.5 }}>
            🧬 당신의영양제
          </a>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <a href="/nearby" style={{ fontSize: 15, color: 'var(--ink-secondary)', textDecoration: 'none', fontWeight: 500 }}>
              🗺️ 약국·병원 찾기
            </a>
            <a href="/survey" className="btn-primary" style={{ padding: '6px 20px', fontSize: 15 }}>
              무료로 시작하기
            </a>
          </div>
        </nav>

        <main>{children}</main>

        {/* Footer */}
        <footer style={{
          background: 'var(--canvas-soft)', borderTop: '1px solid var(--hairline)',
          padding: 'var(--sp-xxl) var(--sp-lg)', marginTop: 80, textAlign: 'center',
          color: 'var(--ink-secondary)',
        }}>
          <p className="caption">
            ⚠️ 질병의 진단·치료가 아닌 <strong>정보 제공 서비스</strong>입니다. 복용 전 의사·약사 상담을 권장합니다.
          </p>
          <p className="caption" style={{ marginTop: 8, color: 'var(--ink-faint)' }}>
            근거 출처: 식약처 건강기능식품 기능성 원료 고시 · NIH Office of Dietary Supplements · PubMed
          </p>
        </footer>
      </body>
    </html>
  );
}
