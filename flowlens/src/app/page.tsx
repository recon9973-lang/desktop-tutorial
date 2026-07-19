import Link from "next/link";
import { getCurrentUser } from "@/lib/session";
import { PLANS } from "@/lib/plans";
import DiagnoseWidget from "@/components/DiagnoseWidget";
import CookieConsent from "@/components/CookieConsent";

export const dynamic = "force-dynamic";

// 모던 쇼핑몰 목업용 상품 (가상 브랜드/가격 · 상품사진은 자체 생성한 스튜디오 컷)
const MALL_PRODUCTS = [
  { br: "마지아룩", nm: "여름버전 밴딩 와이드 팬츠", off: 41, price: "28,700", rt: "4.5 (1,159)", img: "/landing/mall/m1.webp" },
  { br: "룸메어", nm: "모브 린넨100 세미와이드 팬츠", off: 63, price: "44,251", rt: "4.6 (1,402)", img: "/landing/mall/m2.webp" },
  { br: "플로레센스", nm: "미루나 하늘하늘 티블라우스", off: 53, price: "36,800", rt: "3.4 (68)", tag: "1+1", img: "/landing/mall/m3.webp" },
  { br: "하루메이비", nm: "핀턱셔링 포인트 여름 셔츠", off: 44, price: "30,200", rt: "4.6 (1,991)", img: "/landing/mall/m4.webp" },
  { br: "키스해링", nm: "썸머 시어 여름 가디건", off: 51, price: "38,935", rt: "5.0 (3)", img: "/landing/mall/m5.webp" },
];

// 모던 쇼핑몰 홈 목업 (퀸잇/무신사 톤)
function MallMock() {
  return (
    <div className="ml">
      <div className="ml-nav">
        <span className="ml-logo">무드몰</span>
        <span className="ml-menu"><span className="on">추천</span><span>여성</span><span>남성</span><span>뷰티</span><span>세일</span></span>
        <span className="ml-search" />
        <span className="ml-ico"><span /><span /><span /></span>
      </div>
      <div className="ml-banners">
        <div className="ml-ban b1"><span className="k">여름 스타일 특가</span><span className="t">오래 사랑받는 옷</span></div>
        <div className="ml-ban b2"><span className="k">시즌 오프</span><span className="t">프리미엄 골프웨어</span></div>
        <div className="ml-ban b3"><span className="k">최대 68% OFF</span><span className="t">가벼운 여름 특가</span></div>
      </div>
      <div className="ml-chips">
        {["실패없는쇼핑", "원피스", "티셔츠", "팬츠", "니트", "가방", "신발", "뷰티"].map((c) => (
          <span key={c} className="ml-chip">{c}</span>
        ))}
      </div>
      <div className="ml-sec"><span className="h">관심 가질 만한 상품</span><span className="ai">AI 추천</span></div>
      <div className="ml-grid">
        {MALL_PRODUCTS.map((p) => (
          <div className="ml-prod" key={p.nm}>
            <div className="th" style={{ backgroundImage: `url(${p.img})` }}>{p.tag && <span className="tag">{p.tag}</span>}</div>
            <div className="br">{p.br}</div>
            <div className="nm">{p.nm}</div>
            <div className="pr"><span className="off">{p.off}%</span>{p.price}</div>
            <div className="rt">★ {p.rt}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// 맵 썸네일용 미니 쇼핑몰 (상품 그리드만)
function MallMini() {
  return (
    <div className="mlm">
      <div className="mlm-grid">
        {Array.from({ length: 6 }).map((_, i) => (
          <div className="mlm-prod" key={i}>
            <div className="th" style={{ backgroundImage: `url(${MALL_PRODUCTS[i % MALL_PRODUCTS.length].img})` }} />
            <div className="ln" style={{ width: "80%" }} />
            <div className="ln p" />
          </div>
        ))}
      </div>
    </div>
  );
}

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
  { t: "안전한 데이터", d: "입력값 미수집·원문 IP 미저장", bg: "#eef0fb", fg: "#3a3f9e", d1: "M6 11V8a6 6 0 1112 0v3", d2: "M5 11h14v9H5z" },
];

// 업종별 활용 시나리오 (실측 수치가 아니라 "이렇게 씁니다" 예시 — 표시광고법 유의)
const USE_CASES = [
  {
    tag: "쇼핑몰 · 자사몰",
    problem: "광고로 들어와도 장바구니·결제에서 빠져나갈 때",
    find: "클릭맵·스크롤맵으로 상품·장바구니·결제 단계의 이탈 지점을 확인",
    act: "이탈 구간의 버튼·문구·순서를 하나씩 바꿔 전후 비교",
    href: "/blog/heatmap-conversion",
  },
  {
    tag: "병원 · 상담",
    problem: "방문은 있는데 예약·전화 문의로 이어지지 않을 때",
    find: "예약 버튼 주목도·의료진 정보 도달률·모바일 전화 편의를 점검",
    act: "예약 CTA를 상단으로, 전화는 탭하면 걸리게 (의료광고 규정 유의)",
    href: "/blog/hospital-conversion",
  },
  {
    tag: "랜딩 · B2B",
    problem: "상담신청 폼 앞에서 방문자가 돌아설 때",
    find: "폼 도달률·입력 중단 지점·좌절 클릭을 확인",
    act: "입력 항목 최소화·신뢰 요소 배치로 문의 전환 점검",
    href: "/blog/form-conversion",
  },
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
            <Link href="/blog">블로그</Link>
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
          <span className="tl-eyebrow"><span className="live" aria-hidden />내 홈페이지 고객 행동 패턴 · 이름·비밀번호·IP 미수집</span>
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
            <div className="tl-hp-body" style={{ position: "relative" }}>
              <MallMock />
              {/* 고객이 마우스로 상품·배너까지 간 궤적 */}
              <svg className="tl-move" viewBox="0 0 900 480" preserveAspectRatio="none">
                <path d="M120 60 C 320 50, 260 230, 430 250 S 600 360, 660 380" fill="none" stroke="var(--accent)" strokeWidth="2.4" strokeOpacity="0.5" strokeDasharray="6 6" strokeLinecap="round" />
              </svg>
              {/* 무지개 히트맵 — 골프 배너·상품 위 */}
              <span className="bt-hot lg" style={{ left: "50%", top: "26%" }} />
              <span className="bt-hot md" style={{ left: "13%", top: "64%" }} />
              <span className="tl-click" style={{ left: "50%", top: "26%", background: "var(--red)" }} />
              <span className="tl-click c2" style={{ left: "13%", top: "64%", background: "var(--red)" }} />
              {/* 인사이트 말풍선 */}
              <div className="tl-insight" style={{ left: "52%", top: "17%" }}><span className="dot" style={{ background: "var(--red)" }} />골프 배너에 클릭 집중</div>
              <div className="tl-insight i2" style={{ left: "2%", top: "52%" }}><span className="dot" style={{ background: "var(--amber)" }} />이 상품에서 평균 4초 체류</div>
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
            <div className="tl-shot-bar"><i /><i /><i /><span className="u">mysite.co.kr</span></div>
            <div className="tl-shot-body" style={{ position: "relative" }}>
              <MallMock />
              {/* 실제 화면 위 히트맵 — 시선·클릭이 몰린 배너·상품 */}
              <span className="bt-hot lg" style={{ left: "50%", top: "26%" }} />
              <span className="bt-hot md" style={{ left: "13%", top: "64%" }} />
              <span className="bt-hot sm" style={{ left: "50%", top: "64%" }} />
            </div>
          </div>
        </div>
      </section>

      {/* 맵 종류 쇼케이스 — 한 번 설치로 5가지 지도 */}
      <section className="maps" aria-label="지도 종류">
        <h2>한 번 설치로, 5가지 지도로 봅니다</h2>
        <p className="lead">같은 방문 데이터를 각도만 바꿔 보여줍니다. 아래는 <b>최근 30일 · 방문 12,480세션</b> 기준 예시입니다.</p>
        <div className="maps-grid">
          {/* 클릭맵 */}
          <div className="map-card">
            <div className="map-thumb">
              <MallMini />
              <div className="map-ov">
                <span className="bt-hot md" style={{ left: "71%", top: "78%" }} />
                <span className="bt-hot sm" style={{ left: "26%", top: "66%" }} />
              </div>
            </div>
            <div className="map-meta"><div className="t">클릭맵</div><div className="d">어디를 눌렀나 — 뜨거울수록 클릭 많음</div></div>
          </div>
          {/* 무브맵 */}
          <div className="map-card">
            <div className="map-thumb">
              <MallMini />
              <div className="map-ov movemap">
                <svg viewBox="0 0 300 128" preserveAspectRatio="none" aria-hidden>
                  <path d="M40 24 C 120 20, 90 80, 160 78 S 230 100, 250 96" fill="none" stroke="rgba(20,22,30,.55)" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <span className="dwell" style={{ left: "53%", top: "61%" }} />
                <span className="dwell" style={{ left: "83%", top: "75%" }} />
              </div>
            </div>
            <div className="map-meta"><div className="t">무브맵</div><div className="d">마우스가 지나간 길 · 시선 흐름</div></div>
          </div>
          {/* 스크롤맵 */}
          <div className="map-card">
            <div className="map-thumb">
              <MallMini />
              <div className="map-ov scrollmap">
                <span className="tick" style={{ top: 4 }}>100%</span>
                <span className="tick" style={{ top: "48%" }}>52%</span>
                <span className="tick" style={{ bottom: 4 }}>18%</span>
              </div>
            </div>
            <div className="map-meta"><div className="t">스크롤맵</div><div className="d">어디까지 내려봤나 — 아래로 갈수록 줄어듦</div></div>
          </div>
          {/* 셀렉터 */}
          <div className="map-card">
            <div className="selrank">
              {[["장바구니 담기", 38], ["상품 이미지", 27], ["여름 특가 배너", 16], ["찜하기", 11]].map(([nm, pct], i) => (
                <div className="selrow" key={nm as string}>
                  <span className="rk">{i + 1}</span>
                  <span className="nm">{nm}</span>
                  <span className="bar"><i style={{ width: `${pct}%` }} /></span>
                  <span className="pct">{pct}%</span>
                </div>
              ))}
            </div>
            <div className="map-meta"><div className="t">셀렉터</div><div className="d">가장 많이 눌린 버튼·링크 순위</div></div>
          </div>
          {/* 제스처 */}
          <div className="map-card">
            <div className="map-thumb">
              <MallMini />
              <div className="map-ov gesture">
                <span className="tap" style={{ left: "30%", top: "55%" }} />
                <span className="tap" style={{ left: "71%", top: "78%" }} />
                <span className="swipe" style={{ left: "40%", top: "40%", width: 70, transform: "rotate(8deg)" }} />
              </div>
            </div>
            <div className="map-meta"><div className="t">제스처</div><div className="d">모바일 탭·더블탭·확대·스와이프</div></div>
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
            <div className="tl-feat-eyebrow">개인정보 보호 설계</div>
            <h2>민감정보는 안 모으니까,<br />안심하고 제안할 수 있습니다</h2>
            <p>입력값·비밀번호는 <b>아예 받지 않고</b>, 원문 IP는 저장하지 않고 해시만. 민감정보는 자동으로 가립니다. 수집하는 행동 데이터는 <b>비식별화</b>해 다루며, 병원·쇼핑몰처럼 개인정보에 민감한 업종에도 보수적으로 설계했습니다.</p>
            <p className="tl-note">폼 입력값 · 비밀번호 · 원문 IP 미저장</p>
          </div>
          <div className="tl-shot" aria-hidden>
            <div className="tl-shot-bar"><i /><i /><i /><span className="u">수집 정책</span></div>
            <div className="tl-shot-body" style={{ minHeight: 200 }}>
              {[["이름 입력값", "미수집"], ["전화번호", "미수집"], ["비밀번호", "미수집"], ["원문 IP", "해시만 저장"], ["클릭·스크롤 좌표", "비식별 처리"]].map(([k, v]) => (
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

      {/* 업종별 활용 시나리오 */}
      <section className="lp-section usecases" style={{ paddingTop: 8 }}>
        <h2>업종별로 이렇게 씁니다</h2>
        <p className="lead">실제 방문 데이터를 각 업종의 목표에 맞춰 봅니다. (아래는 활용 예시입니다)</p>
        <div className="grid grid-3">
          {USE_CASES.map((u) => (
            <Link key={u.tag} href={u.href} className="card card-pad uc-card">
              <span className="uc-tag">{u.tag}</span>
              <div className="uc-row"><span className="uc-k">상황</span><span>{u.problem}</span></div>
              <div className="uc-row"><span className="uc-k find">확인</span><span>{u.find}</span></div>
              <div className="uc-row"><span className="uc-k act">개선</span><span>{u.act}</span></div>
              <span className="uc-more">자세히 보기 →</span>
            </Link>
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
          <Link href="/blog" style={{ color: "var(--text-2)" }}>블로그</Link>
          <Link href="/privacy" style={{ color: "var(--text-2)" }}>개인정보처리방침</Link>
          <Link href="/terms" style={{ color: "var(--text-2)" }}>이용약관</Link>
        </div>
        FlowLens · 개인정보 보호형 웹 행동 분석 · 폼 입력값·비밀번호 미수집, 민감정보 자동 마스킹
        <div style={{ marginTop: 10, fontSize: 12, color: "var(--text-4)", lineHeight: 1.6 }}>
          주식회사 베놈 · 대표 김보형 · 사업자등록번호 291-86-02777<br />
          대구광역시 수성구 용학로25길 54, 4층 · venomad@naver.com · 1661-4142<br />
          © {new Date().getFullYear()} VENOM Inc. All rights reserved.
        </div>
      </footer>

      <CookieConsent />
    </>
  );
}
