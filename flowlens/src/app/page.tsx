import Link from "next/link";
import { getCurrentUser } from "@/lib/session";
import { PLANS } from "@/lib/plans";
import DiagnoseWidget from "@/components/DiagnoseWidget";
import CookieConsent from "@/components/CookieConsent";

export const dynamic = "force-dynamic";

const STEPS = [
  { t: "스크립트 한 줄 설치", d: "발급된 추적 코드를 사이트 head에 넣거나 워드프레스 플러그인을 설치합니다." },
  { t: "방문자 행동 자동 수집", d: "클릭·스크롤·체류·좌절클릭을 개인정보 안전하게 수집합니다." },
  { t: "개선 리포트 자동 생성", d: "히트맵·퍼널·전후 비교와 한국어 개선 과제를 자동으로 받아봅니다." },
];

// 혜택 4종 (간결한 인라인 SVG 아이콘 — 이모지 대신)
const BENEFITS = [
  { t: "전환율 향상", d: "왜 안 사는지 짚어 실제로 고칩니다", bg: "#e7f6ee", fg: "#0e7c50", d1: "M3 17l6-6 4 4 8-8", d2: "M21 7h-5m5 0v5" },
  { t: "광고비 효율", d: "들어온 사람을 놓치지 않게", bg: "#e6f0fb", fg: "#0075de", d1: "M12 3a9 9 0 100 18 9 9 0 000-18z", d2: "M12 8a4 4 0 100 8 4 4 0 000-8z", circle: true },
  { t: "시간 절감", d: "개선 과제를 자동으로 정리", bg: "#fdf0e2", fg: "#b5590a", d1: "M12 7v5l3 2", d2: "M12 3a9 9 0 100 18 9 9 0 000-18z" },
  { t: "안전한 데이터", d: "입력값·IP 미수집", bg: "#eef0fb", fg: "#3a3f9e", d1: "M6 11V8a6 6 0 1112 0v3", d2: "M5 11h14v9H5z" },
];

export default async function Landing() {
  const user = await getCurrentUser();

  return (
    <>
      {/* 상단 네비 */}
      <div style={{ borderBottom: "1px solid var(--border)", background: "var(--surface)", position: "sticky", top: 0, zIndex: 30 }}>
        <nav className="lp-nav">
          <div className="brand"><span className="dot" /> FlowLens</div>
          <div className="lp-menu">
            <a href="#service">기능</a>
            <a href="#why">왜 중요한가</a>
            <a href="#pricing">요금제</a>
          </div>
          <div className="row">
            {user ? (
              <Link href="/dashboard" className="btn primary pill sm">대시보드로 →</Link>
            ) : (
              <>
                <Link href="/login" className="btn sm">로그인</Link>
                <Link href="/signup" className="btn primary pill sm">무료로 시작</Link>
              </>
            )}
          </div>
        </nav>
      </div>

      {/* 히어로 — "내 홈페이지에서 고객 행동 패턴을 분석한다" (소유자 관점) */}
      <section className="tl-hero">
        <div className="tl-hero-inner">
          <span className="tl-eyebrow"><span className="live" aria-hidden />내 홈페이지 고객 행동 패턴 · 개인정보 미수집</span>
          <h1>내 홈페이지 고객의<br />행동 패턴이 보입니다</h1>
          <p className="tl-hero-sub">
            고객이 어디를 클릭하고, 어디서 멈추고, 어디서 떠나는지 — 실제 내 화면 위에서 확인하고 무엇을 고칠지 제안받으세요.
          </p>
          <div className="tl-hero-diag">
            <DiagnoseWidget />
          </div>
          <div className="tl-hero-trust"><b>1,000+</b> 홈페이지가 고객 행동을 보고 있습니다</div>
        </div>

        {/* 히어로 이미지 — 내 홈페이지 위에 고객 행동(클릭·궤적·열지도·인사이트)이 겹쳐 보임 */}
        <div className="tl-stage" aria-hidden>
          <div className="tl-hp">
            <div className="tl-hp-bar">
              <i /><i /><i /><span className="tl-hp-url">mysite.co.kr</span>
              <span className="tl-hp-live"><span className="d" />지금 8명 행동 분석 중</span>
            </div>
            <div className="tl-hp-body">
              {/* 실제 같은 내 홈페이지 (쇼핑몰) */}
              <div className="rl-site">
                <div className="rl-nav">
                  <div className="rl-brand"><span className="b" />라온</div>
                  <div className="rl-menu"><span>신상품</span><span>베스트</span><span>세일</span></div>
                  <div className="rl-cart" />
                </div>
                <div className="rl-banner">
                  <div className="tag">SUMMER SALE</div>
                  <div className="ttl">여름 시즌 오프<br />최대 40% 할인</div>
                  <span className="cta">지금 쇼핑하기</span>
                </div>
                <div className="rl-grid">
                  <div className="rl-prod"><div className="thumb" /><div className="nm">린넨 오버셔츠</div><div className="pr"><span className="off">40%</span>39,000원</div></div>
                  <div className="rl-prod"><div className="thumb" /><div className="nm">코튼 와이드팬츠</div><div className="pr"><span className="off">30%</span>45,000원</div></div>
                  <div className="rl-prod"><div className="thumb" /><div className="nm">캔버스 토트백</div><div className="pr"><span className="off">25%</span>29,000원</div></div>
                </div>
              </div>

              {/* 고객 행동 오버레이 */}
              <svg className="tl-move" viewBox="0 0 700 300" preserveAspectRatio="none">
                <path d="M70 40 C 200 50, 150 130, 300 120 S 470 150, 560 200" fill="none" stroke="var(--accent)" strokeWidth="2" strokeOpacity="0.5" strokeDasharray="5 5" strokeLinecap="round" />
              </svg>
              <div className="tl-heatb" style={{ width: 108, height: 66, left: "20%", top: 92, background: "radial-gradient(circle,rgba(239,68,68,.68),rgba(234,179,8,.4) 46%,rgba(59,130,246,.16) 76%,transparent)" }} />
              <div className="tl-heatb" style={{ width: 66, height: 50, left: "8%", top: 214, background: "radial-gradient(circle,rgba(239,68,68,.5),rgba(34,197,94,.34) 55%,transparent 80%)" }} />
              <span className="tl-click" style={{ left: "23%", top: "44%", background: "var(--red)" }} />
              <span className="tl-click c2" style={{ left: "12%", top: "80%", background: "var(--accent)" }} />
              <span className="tl-click c3" style={{ left: "52%", top: "82%", background: "var(--accent)" }} />
              {/* 인사이트 말풍선 */}
              <div className="tl-insight" style={{ left: "27%", top: "36%" }}><span className="dot" style={{ background: "var(--red)" }} />“지금 쇼핑하기” 잘 눌러요</div>
              <div className="tl-insight i2" style={{ right: "5%", top: "70%" }}><span className="dot" style={{ background: "var(--amber)" }} />토트백에서 3.2초 머묾</div>
            </div>
          </div>
        </div>
      </section>
      <div style={{ height: 70, background: "var(--bg)" }} />

      {/* 기능 1 — 실제 화면 위 히트맵 (텍스트 좌 · 스크린샷 우) */}
      <section id="service">
        <div className="tl-feat">
          <div className="tl-feat-copy">
            <div className="tl-feat-eyebrow">실제 화면 위 히트맵</div>
            <h2>회색 목업이 아니라,<br />진짜 그 페이지 위에서 봅니다</h2>
            <p>방문자가 어디를 눌렀는지, 어디서 멈췄는지를 실제 사이트 화면 위에 얹어 보여줍니다. 기기별로 자동 캡처해 모바일·데스크톱을 따로 봅니다.</p>
            <p className="tl-note">클릭맵 · 무브맵 · 스크롤맵 · 셀렉터 · 제스처</p>
          </div>
          <div className="tl-shot" aria-hidden>
            <div className="tl-shot-bar"><i /><i /><i /><span className="u">라온몰 · 상품 상세</span></div>
            <div className="tl-shot-body">
              <div className="rl-site">
                <div className="rl-grid" style={{ gridTemplateColumns: "1.1fr 1fr", gap: 14, alignItems: "start" }}>
                  <div className="rl-prod"><div className="thumb" style={{ height: 120 }} /></div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 4 }}>린넨 오버셔츠</div>
                    <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 10 }}><span style={{ color: "var(--red)", marginRight: 6 }}>40%</span>39,000원</div>
                    <div style={{ fontSize: 11.5, color: "var(--text-3)", lineHeight: 1.7, marginBottom: 12 }}>가볍고 시원한 여름 린넨 소재<br />내추럴한 실루엣 · 3color</div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <div className="rl-banner" style={{ padding: "10px 16px", margin: 0, flex: 1, textAlign: "center" }}><span style={{ fontWeight: 800, fontSize: 12.5 }}>장바구니</span></div>
                      <div style={{ padding: "10px 16px", borderRadius: 12, border: "1px solid var(--border)", fontSize: 12.5, fontWeight: 700, color: "var(--text-3)" }}>바로구매</div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="tl-heat" style={{ width: 116, height: 84, right: 30, top: 30, background: "radial-gradient(circle,rgba(239,68,68,.82),rgba(234,179,8,.48) 45%,rgba(59,130,246,.2) 75%,transparent)" }} />
              <div className="tl-heat" style={{ width: 92, height: 60, left: 30, top: 150, background: "radial-gradient(circle,rgba(239,68,68,.66),rgba(34,197,94,.4) 55%,transparent 80%)" }} />
            </div>
          </div>
        </div>
      </section>

      {/* 기능 2 — 한국어 개선 리포트 (스크린샷 좌 · 텍스트 우) */}
      <section id="why">
        <div className="tl-feat rev">
          <div className="tl-feat-copy">
            <div className="tl-feat-eyebrow">한국어 개선 리포트</div>
            <h2>숫자만 던지지 않고,<br />무엇을 고칠지 알려줍니다</h2>
            <p>“모바일에서 핵심 버튼을 보기 전에 이탈합니다 → 상단으로 올리세요” 처럼, 대행사가 고객에게 그대로 내밀 수 있는 <b>할 일 형태</b>의 리포트로 받아봅니다.</p>
            <p className="tl-note">데이터 해석을 대신 하지 않아도 됩니다.</p>
          </div>
          <div className="tl-shot" aria-hidden>
            <div className="tl-shot-bar"><i /><i /><i /><span className="u">개선 리포트</span></div>
            <div className="tl-shot-body">
              <div className="tl-sug"><span className="n">1</span><div><div className="st">모바일 방문자가 핵심 버튼을 보기 전에 이탈합니다</div><div className="sd">첫 화면에 고정 CTA를 추가하세요 · 영향도 높음</div></div></div>
              <div className="tl-sug"><span className="n">2</span><div><div className="st">클릭되지 않는 요소를 누르는 방문자가 있습니다</div><div className="sd">이미지처럼 보이는 영역을 실제 버튼으로 · 34건</div></div></div>
              <div className="tl-sug"><span className="n">3</span><div><div className="st">페이지 중반 이전에 이탈이 많습니다</div><div className="sd">핵심 메시지를 상단으로 · 50% 도달 34%</div></div></div>
            </div>
          </div>
        </div>
      </section>

      {/* 기능 3 — 개인정보 미수집 (텍스트 좌 · 스크린샷 우) */}
      <section>
        <div className="tl-feat">
          <div className="tl-feat-copy">
            <div className="tl-feat-eyebrow">개인정보 미수집</div>
            <h2>안 모으니까,<br />안심하고 제안할 수 있습니다</h2>
            <p>입력값·비밀번호는 <b>아예 받지 않고</b>, IP는 저장하지 않고 해시만. 민감정보는 자동으로 가립니다. 병원·쇼핑몰처럼 개인정보에 민감한 업종에 안전하게 쓸 수 있습니다.</p>
            <p className="tl-note">폼 입력값 · 비밀번호 · 원문 IP 미저장</p>
          </div>
          <div className="tl-shot" aria-hidden>
            <div className="tl-shot-bar"><i /><i /><i /><span className="u">수집 정책</span></div>
            <div className="tl-shot-body" style={{ minHeight: 200 }}>
              {[["이름 입력값", "미수집"], ["전화번호", "미수집"], ["비밀번호", "미수집"], ["원문 IP", "해시만 저장"], ["클릭·스크롤 좌표", "수집 (익명)"]].map(([k, v]) => (
                <div key={k} className="between" style={{ padding: "11px 12px", border: "1px solid var(--border)", borderRadius: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 13.5, fontWeight: 600 }}>{k}</span>
                  <span className="badge" style={{ background: v.includes("미수집") || v.includes("해시") ? "#e7f6ee" : "var(--accent-soft)", color: v.includes("미수집") || v.includes("해시") ? "var(--green)" : "var(--accent)" }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 혜택 아이콘 줄 */}
      <section className="tl-bench">
        <h2>방문자 행동을 이해하면 이렇게 달라집니다</h2>
        <div className="tl-bench-grid">
          {BENEFITS.map((b) => (
            <div key={b.t} className="tl-bench-item">
              <div className="tl-bench-ic" style={{ background: b.bg, color: b.fg }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d={b.d1} />{b.d2 && <path d={b.d2} />}{b.circle && <circle cx="12" cy="12" r="3" />}
                </svg>
              </div>
              <div className="bt">{b.t}</div>
              <div className="bd">{b.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 이렇게 동작합니다 */}
      <section className="lp-section" style={{ paddingTop: 20 }}>
        <h2>이렇게 동작합니다</h2>
        <p className="lead">설치는 5분, 나머지는 자동입니다.</p>
        <div className="grid grid-3">
          {STEPS.map((s, i) => (
            <div key={s.t} className="card card-pad">
              <div className="row" style={{ marginBottom: 12 }}>
                <span className="lp-step-num">{i + 1}</span>
                <b>{s.t}</b>
              </div>
              <p className="muted small" style={{ margin: 0 }}>{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 설치 가능 범위 — 되는 곳 / 안 되는 곳 (가입 전 기대치 명시) */}
      <section className="tl-scope" id="install-scope">
        <h2>어디에 설치할 수 있나요?</h2>
        <p className="lead">내 홈페이지 소스에 <b>스크립트 한 줄</b>을 넣을 수 있는 곳이면 됩니다.</p>
        <div className="tl-scope-grid">
          <div className="tl-scope-card ok">
            <span className="hd">설치 가능</span>
            <ul>
              <li><b>자사몰</b> — 카페24 · 아임웹 · 고도몰 · 메이크샵 · 식스샵</li>
              <li><b>홈페이지·랜딩</b> — 워드프레스 · 윅스 · 직접 만든 사이트</li>
              <li><b>구글 태그 매니저(GTM)</b>를 넣을 수 있는 모든 사이트</li>
            </ul>
          </div>
          <div className="tl-scope-card no">
            <span className="hd">설치 불가</span>
            <ul>
              <li><b>오픈마켓</b> — 쿠팡 · 지마켓 · 옥션 · 11번가</li>
              <li><b>네이버쇼핑 · 스마트스토어</b></li>
              <li><b>네이버 블로그·카페 · 인스타 · 유튜브</b></li>
            </ul>
            <p className="note">외부 스크립트를 넣을 수 없는 남의 플랫폼은 지원되지 않습니다. (마켓 셀러도 <b>광고로 유입되는 자사몰·랜딩</b>은 분석할 수 있습니다.)</p>
          </div>
        </div>
      </section>

      {/* 요금제 */}
      <section className="lp-section" style={{ paddingTop: 0 }} id="pricing">
        <h2>요금제</h2>
        <p className="lead">무료로 시작하고, 필요할 때 올리세요. 대행사는 다중 고객·화이트라벨.</p>
        <div className="grid grid-3">
          {PLANS.filter((p) => ["FREE", "GROWTH", "AGENCY"].includes(p.key)).map((p) => (
            <div key={p.key} className="card card-pad" style={p.key === "GROWTH" ? { borderColor: "var(--accent)", borderWidth: 2 } : {}}>
              <div className="between" style={{ marginBottom: 6 }}>
                <b style={{ fontSize: 17 }}>{p.name}</b>
                {p.key === "GROWTH" && <span className="badge low">인기</span>}
              </div>
              <div style={{ fontSize: 24, fontWeight: 800, marginBottom: 2 }}>{p.priceLabel}<span className="muted" style={{ fontSize: 12, fontWeight: 500 }}> /월</span></div>
              <div className="muted small" style={{ marginBottom: 12 }}>{p.target}</div>
              <ul className="small muted" style={{ margin: "0 0 16px", paddingLeft: 16, lineHeight: 1.9 }}>
                {p.highlights.map((h) => <li key={h}>{h}</li>)}
              </ul>
              <Link href="/signup" className={`btn sm pill ${p.key === "GROWTH" ? "primary" : ""}`} style={{ width: "100%", justifyContent: "center" }}>
                {p.price === 0 ? "무료로 시작" : "시작하기"}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* 마지막 CTA — 밝은 카드 (어두운 밴드 대신) */}
      <section className="tl-final">
        <div className="tl-final-card">
          <h2>지금 무료로 시작하세요</h2>
          <p>카드 없이 가입 · 스크립트 한 줄 설치 · 며칠이면 첫 리포트</p>
          <Link href="/signup" className="btn primary pill" style={{ padding: "13px 28px", fontWeight: 700 }}>대행사 워크스페이스 무료로 만들기 →</Link>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="row" style={{ justifyContent: "center", gap: 14, marginBottom: 8 }}>
          <Link href="/privacy" style={{ color: "var(--text-2)" }}>개인정보처리방침</Link>
          <Link href="/terms" style={{ color: "var(--text-2)" }}>이용약관</Link>
        </div>
        FlowLens · 개인정보 보호형 웹 행동 분석 · 폼 입력값·비밀번호 미수집, 민감정보 자동 마스킹
      </footer>

      <CookieConsent />
    </>
  );
}
