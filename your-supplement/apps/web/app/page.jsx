import Link from 'next/link';

const FEATURES = [
  { emoji: '⭐', title: '근거 등급제', body: '모든 추천에 출처(식약처·NIH·논문)와 신뢰도 ⭐⭐⭐를 표기. 광고·후기가 아닌 검증된 데이터.' },
  { emoji: '⏱️', title: '복용 기간 가이드', body: '🟢 지속 / 🟡 점검 / 🔴 주기 — "평생 먹어야 하나?" 불안을 데이터로 해소.' },
  { emoji: '🔗', title: '상호작용 엔진', body: '성분 시너지·길항·의약품 경고 자동 반영. 내 조합에 맞는 복용 스케줄까지 제시.' },
  { emoji: '💰', title: '함량당 최저가', body: '단순 가격이 아닌 유효성분 mg당 가성비 랭킹. 진짜 저렴한 제품을 찾아드려요.' },
  { emoji: '💬', title: '카카오톡 전송', body: '추천 결과와 복용 알람을 카카오톡으로 받아보세요. 앱 없이도 관리 가능.' },
  { emoji: '📦', title: '내 영양제 관리', body: '먹는 영양제를 등록하고 섭취 시간 알람 설정. 점검 알림으로 과잉 복용 예방.' },
];

// 히어로 배경 이미지(맞춤 생성) — 자체 호스팅. 파일: apps/web/public/hero.png
const HERO_IMG = '/hero.png';

const TRUST = [
  ['17', '성분 근거 코퍼스'],
  ['0', '광고·협찬'],
  ['100%', '출처 표시'],
];

const STEPS = [
  { n: '1', icon: '📝', title: '1분 설문', body: '고민·나이·복용약·식단을 선택하면 끝' },
  { n: '2', icon: '🔬', title: '근거 대조', body: '식약처·NIH·논문 데이터와 자동으로 대조' },
  { n: '3', icon: '💊', title: '맞춤 추천', body: '근거 등급·상호작용·복용법까지 한 번에' },
];

export default function LandingPage() {
  return (
    <>
      {/* Hero — photo-led (맞춤 생성 이미지 + 그린 오버레이) */}
      <section style={{
        position: 'relative', color: '#fff',
        backgroundImage: `linear-gradient(100deg, rgba(11,59,45,0.95) 0%, rgba(11,59,45,0.86) 34%, rgba(11,59,45,0.55) 62%, rgba(6,95,70,0.28) 100%), url("${HERO_IMG}")`,
        backgroundSize: 'cover', backgroundPosition: 'center right',
        padding: '96px var(--sp-lg) 88px',
      }}>
        <div style={{ maxWidth: 1080, margin: '0 auto' }}>
          <div style={{ maxWidth: 580 }}>
            <span className="badge" style={{ background: 'rgba(110,231,183,0.14)', color: '#6ee7b7', border: '1px solid rgba(110,231,183,0.32)', marginBottom: 22, display: 'inline-flex' }}>
              식약처 · NIH · 논문 근거 기반
            </span>

            <h1 style={{ fontSize: 50, fontWeight: 800, lineHeight: 1.12, letterSpacing: -1.6, marginBottom: 20 }}>
              내 몸에 맞는 영양제,<br />
              <span style={{ color: '#6ee7b7' }}>근거로 찾아드립니다</span>
            </h1>

            <p style={{ fontSize: 18, lineHeight: 1.65, color: 'rgba(255,255,255,0.85)', maxWidth: 470, marginBottom: 34 }}>
              광고도, 주관적 후기도 아닙니다. 식약처·NIH·논문 근거만으로 당신의 영양제를 추천해요.
            </p>

            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <Link href="/survey" className="btn-primary" style={{ fontSize: 17, padding: '12px 32px' }}>
                1분 설문 시작하기 →
              </Link>
              <a href="#how" className="btn-secondary" style={{ fontSize: 17, padding: '12px 32px', background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.28)' }}>
                어떻게 추천하나요?
              </a>
            </div>

            <Link href="/drug/scan" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 20, fontSize: 15, fontWeight: 600, color: '#6ee7b7', textDecoration: 'none' }}>
              📷 이 약 뭐지? — 사진으로 알약 찾기 →
            </Link>

            {/* 신뢰 지표 */}
            <div style={{ display: 'flex', gap: 28, marginTop: 38, flexWrap: 'wrap' }}>
              {TRUST.map(([n, l]) => (
                <div key={l}>
                  <div style={{ fontSize: 23, fontWeight: 800, color: '#6ee7b7', letterSpacing: -0.5 }}>{n}</div>
                  <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.72)' }}>{l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* How it works — 3단계 프로세스 */}
      <section id="how" style={{ maxWidth: 960, margin: '84px auto 0', padding: '0 var(--sp-lg)' }}>
        <div style={{ textAlign: 'center', marginBottom: 44 }}>
          <span className="badge" style={{ marginBottom: 16, display: 'inline-flex' }}>작동 방식</span>
          <h2 className="heading-1" style={{ marginBottom: 12 }}>이렇게 추천해요</h2>
          <p className="body-md" style={{ color: 'var(--ink-muted)', maxWidth: 480, margin: '0 auto' }}>
            1분이면 충분해요. 광고가 아니라 <strong style={{ color: 'var(--ink)' }}>근거</strong>로 답합니다.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 16 }}>
          {STEPS.map((s) => (
            <div key={s.n} className="card" style={{ textAlign: 'center', padding: '30px 20px' }}>
              <div style={{ width: 54, height: 54, borderRadius: '50%', background: 'rgba(5,150,105,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 25, margin: '0 auto 14px' }}>{s.icon}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--primary)', marginBottom: 5, letterSpacing: 0.5 }}>STEP {s.n}</div>
              <h3 className="title" style={{ marginBottom: 6 }}>{s.title}</h3>
              <p className="body-sm" style={{ color: 'var(--ink-muted)' }}>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* What's different — 기능 카드 */}
      <section style={{ maxWidth: 960, margin: '64px auto 0', padding: '0 var(--sp-lg)' }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <h2 className="heading-2" style={{ marginBottom: 12 }}>무엇이 다른가요?</h2>
          <p className="body-md" style={{ color: 'var(--ink-muted)', maxWidth: 480, margin: '0 auto' }}>
            모든 추천에 <strong style={{ color: 'var(--ink)' }}>출처와 신뢰도 등급</strong>을 붙입니다
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
          {FEATURES.map((f) => (
            <div key={f.title} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ width: 44, height: 44, borderRadius: 'var(--r-md)', background: 'rgba(5,150,105,0.09)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>{f.emoji}</div>
              <h3 className="title" style={{ color: 'var(--ink)' }}>{f.title}</h3>
              <p className="body-sm" style={{ color: 'var(--ink-muted)' }}>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Result preview */}
      <section style={{ background: 'var(--canvas)', borderTop: '1px solid var(--hairline)', borderBottom: '1px solid var(--hairline)', padding: '72px var(--sp-lg)' }}>
        <div style={{ maxWidth: 700, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <span className="badge" style={{ marginBottom: 16, display: 'inline-flex' }}>결과 미리보기</span>
            <h2 className="heading-1">이런 추천을 받아요</h2>
          </div>

          {/* Sample result card */}
          <div className="card-elevated" style={{ borderRadius: 'var(--r-xl)', overflow: 'hidden', padding: 0 }}>
            {/* 근거 점수 헤더 */}
            <div style={{ background: 'linear-gradient(120deg, #0b3b2d, #065f46)', color: '#fff', padding: '20px 22px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <div style={{ fontSize: 12, color: '#6ee7b7', fontWeight: 700 }}>이번 추천 근거 점수</div>
                <div style={{ fontSize: 30, fontWeight: 800, lineHeight: 1.1 }}>92<span style={{ fontSize: 16 }}>점</span></div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 2 }}>추천 3종 모두 확립·중등도 근거</div>
              </div>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)' }}>34세 여성 · 피로 · 눈</span>
            </div>

            <div style={{ padding: '8px 22px 20px' }}>
              {[
                { name: '비타민D', ev: '확립된 근거', evc: '#047857', dur: '🟡 3개월 후 점검', func: '칼슘 흡수·뼈 형성에 필요', warn: null, price: '21,900', mg: '0.24' },
                { name: '루테인', ev: '중등도 근거', evc: '#0d9488', dur: '🟢 지속 복용 가능', func: '황반색소밀도 유지(눈 건강)', warn: null, price: '18,500', mg: '0.31' },
                { name: '오메가3', ev: '확립된 근거', evc: '#047857', dur: '🟢 지속 복용 가능', func: '혈중 중성지질 개선·혈행 개선', warn: '⚠️ 와파린 복용자 상담 필요', price: '24,900', mg: '0.19' },
              ].map((item, i) => (
                <div key={item.name} style={{
                  padding: '14px 0', borderBottom: i < 2 ? '1px solid var(--hairline)' : 'none',
                  display: 'flex', alignItems: 'flex-start', gap: 14,
                }}>
                  <span style={{
                    width: 30, height: 30, background: i === 0 ? 'var(--primary)' : 'var(--canvas-soft)', color: i === 0 ? '#fff' : 'var(--ink-muted)',
                    borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, flexShrink: 0,
                  }}>
                    {i + 1}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                      <strong className="body-md">{item.name}</strong>
                      <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: item.evc, borderRadius: 'var(--r-full)', padding: '2px 8px' }}>{item.ev}</span>
                      <span style={{ fontSize: 12, color: 'var(--ink-muted)' }}>{item.dur}</span>
                    </div>
                    <p className="body-sm" style={{ color: 'var(--ink-muted)' }}>{item.func}</p>
                    {item.warn && <p style={{ fontSize: 13, color: 'var(--accent-orange)', marginTop: 4 }}>{item.warn}</p>}
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--primary)' }}>최저 ₩{item.price}</p>
                    <p style={{ fontSize: 11, color: 'var(--ink-faint)' }}>mg당 ₩{item.mg}</p>
                  </div>
                </div>
              ))}

              <div style={{ background: 'var(--canvas-soft)', borderRadius: 'var(--r-md)', padding: '12px 14px', marginTop: 16 }}>
                <p className="body-sm" style={{ color: 'var(--ink-secondary)' }}>
                  📅 <strong>복용 스케줄</strong>: 아침 — 비타민D · 루테인 / 저녁 — 오메가3
                </p>
              </div>
            </div>
          </div>

          <p className="body-sm" style={{ textAlign: 'center', color: 'var(--ink-faint)', marginTop: 16 }}>
            ※ 예시 화면입니다. 실제 추천은 설문 결과로 계산돼요.
          </p>
        </div>
      </section>

      {/* 약 알기 — 검색·사진 식별 */}
      <section style={{ maxWidth: 900, margin: '80px auto 0', padding: '0 var(--sp-lg)' }}>
        <div style={{
          borderRadius: 'var(--r-xl)', overflow: 'hidden', border: '1px solid var(--hairline)',
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        }}>
          <div style={{ background: 'var(--canvas)', padding: '40px 32px', display: 'flex', flexDirection: 'column', gap: 16, justifyContent: 'center', order: 1 }}>
            {[
              { emoji: '🔎', title: '이름·성분으로 검색', body: '타이레놀·아세트아미노펜처럼 이름이나 성분으로 바로 조회' },
              { emoji: '🎨', title: '모양·색·각인 필터', body: '이름을 몰라도 알약의 모양·색·각인으로 좁혀서 찾기' },
              { emoji: '📷', title: '사진으로 각인 인식', body: '알약을 촬영하면 각인을 읽어 후보를 추려주는 보조 기능(베타)' },
            ].map((f) => (
              <div key={f.title} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 22, flexShrink: 0 }}>{f.emoji}</span>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 15, color: 'var(--ink)' }}>{f.title}</p>
                  <p style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 2 }}>{f.body}</p>
                </div>
              </div>
            ))}
          </div>
          <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 32px', order: 2 }}>
            <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 16, display: 'inline-flex' }}>
              식약처 낱알식별
            </span>
            <h2 style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.6, marginBottom: 12 }}>
              💊 이 약, 뭘까?
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: 'rgba(255,255,255,0.75)', marginBottom: 28 }}>
              처방받은 알약이 뭔지 궁금할 때. 이름·모양·색·각인으로 찾고,<br />
              사진으로도 확인한 뒤 내 영양제와의 궁합까지 한 번에.
            </p>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <Link href="/drug" className="btn-primary" style={{ fontSize: 16, padding: '12px 26px', background: '#fff', color: 'var(--secondary)' }}>
                약 검색하기 →
              </Link>
              <Link href="/drug/scan" style={{ fontSize: 16, padding: '12px 26px', fontWeight: 600, color: '#fff', textDecoration: 'none', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 'var(--r-full)' }}>
                📷 사진으로 찾기
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 지도 서비스 — 문 연 약국·응급실 찾기 */}
      <section style={{ maxWidth: 900, margin: '80px auto', padding: '0 var(--sp-lg)' }}>
        <div style={{
          borderRadius: 'var(--r-xl)', overflow: 'hidden', border: '1px solid var(--hairline)',
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        }}>
          <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 32px' }}>
            <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 16, display: 'inline-flex' }}>
              공공데이터 기반
            </span>
            <h2 style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.6, marginBottom: 12 }}>
              🗺️ 문 연 약국·응급실 찾기
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: 'rgba(255,255,255,0.75)', marginBottom: 28 }}>
              추천받은 영양제, 어디서 사죠? 지금 영업 중인 약국부터<br />
              24시 응급실·야간 소아진료까지 지도에서 한 번에.
            </p>
            <Link href="/nearby" className="btn-primary" style={{ fontSize: 16, padding: '12px 28px', background: '#fff', color: 'var(--secondary)' }}>
              지도에서 찾기 →
            </Link>
          </div>
          <div style={{ background: 'var(--canvas)', padding: '40px 32px', display: 'flex', flexDirection: 'column', gap: 16, justifyContent: 'center' }}>
            {[
              { emoji: '💊', title: '지금 문 연 약국', body: '영업 중·심야·공휴일 약국을 내 위치 가까운 순으로' },
              { emoji: '🚨', title: '24시 응급실', body: '응급의료기관 위치와 연락처 · 전화·길찾기 바로가기' },
              { emoji: '🌙', title: '야간 소아진료', body: '달빛어린이병원 등 밤에 여는 소아과' },
            ].map((f) => (
              <div key={f.title} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 22, flexShrink: 0 }}>{f.emoji}</span>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 15, color: 'var(--ink)' }}>{f.title}</p>
                  <p style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 2 }}>{f.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ textAlign: 'center', padding: '80px var(--sp-lg)' }}>
        <h2 className="heading-2" style={{ marginBottom: 12 }}>지금 바로 내 영양제를 찾아보세요</h2>
        <p className="body-md" style={{ color: 'var(--ink-muted)', marginBottom: 32 }}>1분 설문 · 무료 · 근거 있는 추천</p>
        <Link href="/survey" className="btn-primary" style={{ fontSize: 17, padding: '14px 40px' }}>
          시작하기 →
        </Link>
      </section>
    </>
  );
}
