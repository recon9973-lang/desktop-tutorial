import Link from "next/link";
import { getCurrentUser } from "@/lib/session";
import { PLANS } from "@/lib/plans";
import DiagnoseWidget from "@/components/DiagnoseWidget";
import CookieConsent from "@/components/CookieConsent";

export const dynamic = "force-dynamic";

const SERVICES = ["클릭 히트맵", "스크롤맵 · 셀렉터", "세션 리플레이", "전환 퍼널", "전/후 비교", "한국어 개선 리포트", "화이트라벨 공유", "모바일 제스처"];

const STEPS = [
  { t: "스크립트 한 줄 설치", d: "발급된 추적 코드를 사이트 head에 넣거나 워드프레스 플러그인을 설치합니다." },
  { t: "방문자 행동 자동 수집", d: "클릭·스크롤·체류·좌절클릭을 개인정보 안전하게 수집합니다." },
  { t: "개선 리포트 자동 생성", d: "히트맵·퍼널·전후 비교와 한국어 개선 과제를 자동으로 받아봅니다." },
];

// 원형 다이어그램 노드 (중심 주변 배치)
const ORBIT = [
  { t: "전환율 향상", x: 50, y: 4 },
  { t: "이탈 원인 파악", x: 89, y: 22 },
  { t: "광고비 효율", x: 93, y: 66 },
  { t: "개선 과제 자동화", x: 50, y: 96 },
  { t: "시간·비용 절감", x: 9, y: 66 },
  { t: "데이터 기반 의사결정", x: 8, y: 22 },
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
              <Link href="/dashboard" className="btn primary sm">대시보드로 →</Link>
            ) : (
              <>
                <Link href="/login" className="btn sm">로그인</Link>
                <Link href="/signup" className="btn primary sm">무료로 시작</Link>
              </>
            )}
          </div>
        </nav>
      </div>

      {/* 히어로 (분할) */}
      <section className="lp-hero2">
        <div className="lp-hero2-inner">
          {/* 좌: 카피 + 무료 진단 */}
          <div className="lp-hero-card">
            <span className="lp-eyebrow">✨ 개인정보 보호형 행동 분석 SaaS</span>
            <h1>광고비는 쓰는데<br /><span className="hl">왜 안 팔리는지</span> 보입니다</h1>
            <p className="muted" style={{ fontSize: 15, marginTop: 0, marginBottom: 22 }}>
              방문자의 클릭·스크롤·망설임을 분석해 매출과 문의 전환을 높일 개선점을 자동으로 제안합니다. 먼저, 내 사이트를 무료로 진단해 보세요.
            </p>
            <DiagnoseWidget />
            <div className="avatars">
              <div className="stack-imgs">
                <span className="av" /><span className="av" /><span className="av" /><span className="av" />
              </div>
              <div className="small muted"><b style={{ color: "var(--text)" }}>1,000+</b> 대행사·쇼핑몰이 신뢰합니다</div>
            </div>
          </div>

          {/* 우: 대시보드 + 히트맵 목업 */}
          <div className="lp-visual">
            <div className="lp-mock">
              <div className="lp-mock-bar"><i /><i /><i /><span className="small muted" style={{ marginLeft: 8 }}>mysite.co.kr — FlowLens</span></div>
              <div className="lp-mock-body">
                <div className="lp-mock-tiles">
                  <div className="lp-mock-tile"><b>2,107</b><span>세션</span></div>
                  <div className="lp-mock-tile"><b>19%</b><span>이탈률</span></div>
                  <div className="lp-mock-tile"><b>147</b><span>전환</span></div>
                </div>
                <div className="lp-mock-chart">
                  <div style={{ height: "40%" }} /><div style={{ height: "62%" }} /><div style={{ height: "48%" }} /><div style={{ height: "80%" }} /><div style={{ height: "70%" }} /><div style={{ height: "95%" }} /><div style={{ height: "60%" }} />
                </div>
                {/* 히트맵이 화면과 어우러지도록 오버레이 */}
                <div className="lp-heatblob" style={{ width: 120, height: 80, right: 26, top: 60, background: "radial-gradient(circle,rgba(239,68,68,.8),rgba(234,179,8,.45) 45%,rgba(59,130,246,.2) 75%,transparent)" }} />
                <div className="lp-heatblob" style={{ width: 90, height: 60, left: 40, top: 120, background: "radial-gradient(circle,rgba(239,68,68,.7),rgba(34,197,94,.4) 55%,transparent 80%)" }} />
              </div>
            </div>
            <div className="hero-badge">
              <div className="ic">🩺</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 13 }}>무료 진단</div>
                <div className="muted small">가입 없이 즉시 · 카드 필요 없음</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 우리가 하는 일 (벤토) */}
      <section className="lp-section" id="service" style={{ paddingTop: 68 }}>
        <p className="lead" style={{ marginBottom: 6, textAlign: "left", maxWidth: "none", color: "var(--accent)", fontWeight: 700, fontSize: 13 }}>우리가 하는 일</p>
        <h2 style={{ textAlign: "left", marginBottom: 26, maxWidth: 760 }}>기능 수가 아니라, 국내 대행사·쇼핑몰이 실제로 개선하게 만드는 운영 경험에 집중합니다</h2>
        <div className="bento">
          <div className="cell">
            <div className="between" style={{ marginBottom: 12 }}><span className="badge low">FlowLens 소개</span><span className="cell-arrow">↗</span></div>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>행동 분석 SaaS</div>
            <p className="muted small" style={{ margin: 0 }}>클릭·스크롤·좌절을 수집해 히트맵과 한국어 개선 리포트로. 스크립트 한 줄이면 시작합니다.</p>
          </div>
          <div className="cell tint" style={{ display: "grid", placeItems: "center" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 30 }}>🔥</div>
              <div style={{ fontWeight: 700, marginTop: 6 }}>실사이트 위 히트맵</div>
              <div className="muted small">회색 목업이 아닌 진짜 화면 위</div>
            </div>
          </div>
          <div className="cell rows">
            <div className="between" style={{ marginBottom: 12 }}><b>제공 기능</b><span className="cell-arrow">↗</span></div>
            <div className="svc-list">
              {SERVICES.map((s) => (
                <div key={s} className="svc-pill"><span className="d" />{s}</div>
              ))}
            </div>
          </div>
          <div className="cell tint" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ fontSize: 24 }}>🔒</div>
            <div style={{ fontWeight: 700, margin: "8px 0 4px" }}>개인정보 보호 우선</div>
            <p className="muted small" style={{ margin: 0 }}>입력값·비밀번호 미수집, 민감정보 자동 마스킹, IP 미저장.</p>
          </div>
          <div className="cell span2" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
            <div>
              <span className="badge medium" style={{ marginBottom: 8 }}>무료 진단</span>
              <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 4 }}>가입 없이 내 사이트 기본 점검</div>
              <p className="muted small" style={{ margin: 0 }}>모바일 대응·CTA·폼·속도까지 즉시 진단하고, 설치하면 실제 행동 데이터가 쌓입니다.</p>
            </div>
            <Link href="/signup" className="btn primary" style={{ whiteSpace: "nowrap" }}>무료로 시작 →</Link>
          </div>
        </div>
      </section>

      {/* 왜 중요한가 (원형 다이어그램) */}
      <section className="lp-section" id="why" style={{ paddingTop: 20 }}>
        <p className="lead" style={{ marginBottom: 6, color: "var(--accent)", fontWeight: 700, fontSize: 13 }}>왜 이게 중요한가</p>
        <h2>방문자 행동을 이해하면<br />전환·광고효율·의사결정이 달라집니다</h2>
        <div className="orbit">
          <svg className="orbit-ring" viewBox="0 0 100 74" preserveAspectRatio="none" aria-hidden>
            <ellipse cx="50" cy="37" rx="46" ry="34" fill="none" stroke="var(--border)" strokeWidth="0.4" strokeDasharray="1.4 1.4" />
          </svg>
          <div className="orbit-center">
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 30 }}>📈</div>
              <div style={{ fontWeight: 700, fontSize: 13, marginTop: 2 }}>전환 개선</div>
            </div>
          </div>
          {ORBIT.map((n) => (
            <div key={n.t} className="orbit-node" style={{ left: `${n.x}%`, top: `${n.y}%` }}>{n.t}</div>
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
              <Link href="/signup" className={`btn sm ${p.key === "GROWTH" ? "primary" : ""}`} style={{ width: "100%", justifyContent: "center" }}>
                {p.price === 0 ? "무료로 시작" : "시작하기"}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* 마지막 CTA */}
      <section className="lp-section" style={{ paddingTop: 0 }}>
        <div className="lp-cta">
          <h2 style={{ marginBottom: 10 }}>지금 무료로 시작하세요</h2>
          <p style={{ opacity: 0.9, marginBottom: 22 }}>카드 없이 가입 · 스크립트 한 줄 설치 · 며칠이면 첫 리포트</p>
          <Link href="/signup" className="btn white" style={{ padding: "13px 28px", fontWeight: 700 }}>대행사 워크스페이스 무료로 만들기 →</Link>
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
