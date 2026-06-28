import Link from 'next/link';

const FEATURES = [
  { emoji: '⭐', title: '근거 등급제', body: '모든 추천에 출처(식약처·NIH·논문)와 신뢰도 ⭐⭐⭐를 표기. 광고·후기가 아닌 검증된 데이터.' },
  { emoji: '⏱️', title: '복용 기간 가이드', body: '🟢 지속 / 🟡 점검 / 🔴 주기 — "평생 먹어야 하나?" 불안을 데이터로 해소.' },
  { emoji: '🔗', title: '상호작용 엔진', body: '성분 시너지·길항·의약품 경고 자동 반영. 내 조합에 맞는 복용 스케줄까지 제시.' },
  { emoji: '💰', title: '함량당 최저가', body: '단순 가격이 아닌 유효성분 mg당 가성비 랭킹. 진짜 저렴한 제품을 찾아드려요.' },
  { emoji: '💬', title: '카카오톡 전송', body: '추천 결과와 복용 알람을 카카오톡으로 받아보세요. 앱 없이도 관리 가능.' },
  { emoji: '📦', title: '내 영양제 관리', body: '먹는 영양제를 등록하고 섭취 시간 알람 설정. 점검 알림으로 과잉 복용 예방.' },
];

const CONCERNS = [
  { emoji: '😴', label: '피로 / 기력 저하' },
  { emoji: '🌙', label: '수면 / 스트레스' },
  { emoji: '👁️', label: '눈 피로 / 눈 건강' },
  { emoji: '❤️', label: '혈관 / 혈중 지질' },
  { emoji: '🦴', label: '뼈 / 관절' },
  { emoji: '🛡️', label: '면역력' },
];

export default function LandingPage() {
  return (
    <>
      {/* Hero — dark indigo band (Notion secondary) */}
      <section style={{
        background: 'var(--secondary)', color: 'var(--on-primary)',
        padding: '80px var(--sp-lg) 96px', textAlign: 'center',
      }}>
        <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 24, display: 'inline-flex' }}>
          식약처 인정 근거 기반 추천
        </span>

        <h1 style={{ fontSize: 52, fontWeight: 700, lineHeight: 1.08, letterSpacing: -1.875, marginBottom: 20 }}>
          내 몸에 맞는 영양제,<br />
          <span style={{ color: 'var(--accent-sky)' }}>근거로 찾아드립니다</span>
        </h1>

        <p style={{ fontSize: 18, lineHeight: 1.6, color: 'rgba(255,255,255,0.75)', maxWidth: 520, margin: '0 auto 40px' }}>
          광고도, 주관적 후기도 아닙니다.<br />
          식약처·NIH·논문 근거만으로 당신의 영양제를 추천해요.
        </p>

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link href="/survey" className="btn-primary" style={{ fontSize: 17, padding: '12px 32px' }}>
            1분 설문 시작하기 →
          </Link>
          <a href="#how" className="btn-secondary" style={{ fontSize: 17, padding: '12px 32px' }}>
            어떻게 추천하나요?
          </a>
        </div>

        {/* Concern chips decoration */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap', marginTop: 48 }}>
          {CONCERNS.map((c) => (
            <span key={c.label} style={{
              background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: 'var(--r-full)', padding: '6px 14px', fontSize: 14, color: 'rgba(255,255,255,0.85)',
            }}>
              {c.emoji} {c.label}
            </span>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" style={{ maxWidth: 900, margin: '80px auto', padding: '0 var(--sp-lg)' }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <span className="badge" style={{ marginBottom: 16, display: 'inline-flex' }}>추천 방식</span>
          <h2 className="heading-1" style={{ marginBottom: 12 }}>왜 다른가요?</h2>
          <p className="body-md" style={{ color: 'var(--ink-muted)', maxWidth: 480, margin: '0 auto' }}>
            고약사처럼 논문을 근거로 — 모든 추천에 출처와 신뢰도 등급을 붙입니다
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
          {FEATURES.map((f) => (
            <div key={f.title} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <span style={{ fontSize: 28 }}>{f.emoji}</span>
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
          <div className="card-elevated" style={{ borderRadius: 'var(--r-xl)' }}>
            <div style={{ borderBottom: '1px solid var(--hairline)', paddingBottom: 16, marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h3 className="title">🧬 OO님의 영양제</h3>
              <span className="badge">34세 여성 · 피로 · 눈</span>
            </div>

            {[
              { name: '비타민D', stars: 3, dur: '🟡 3개월 후 점검', func: '칼슘 흡수·뼈 형성에 필요', warn: null },
              { name: '루테인', stars: 3, dur: '🟢 지속 복용 가능', func: '노화로 인한 눈 건강 유지에 도움', warn: null },
              { name: '오메가3', stars: 3, dur: '🟢 지속 복용 가능', func: '혈중 중성지방 개선, 혈행 개선', warn: '⚠️ 와파린 복용자 상담 필요' },
            ].map((item, i) => (
              <div key={item.name} style={{
                padding: '14px 0', borderBottom: i < 2 ? '1px solid var(--hairline)' : 'none',
                display: 'flex', alignItems: 'flex-start', gap: 14,
              }}>
                <span style={{
                  width: 32, height: 32, background: 'var(--canvas-soft)', borderRadius: 'var(--r-md)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0,
                }}>
                  {i + 1}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <strong className="body-md">{item.name}</strong>
                    <span style={{ color: '#f5b800', fontSize: 12 }}>{'⭐'.repeat(item.stars)}</span>
                    <span style={{ fontSize: 12, color: 'var(--ink-muted)' }}>{item.dur}</span>
                  </div>
                  <p className="body-sm" style={{ color: 'var(--ink-muted)' }}>{item.func}</p>
                  {item.warn && <p style={{ fontSize: 13, color: 'var(--accent-orange)', marginTop: 4 }}>{item.warn}</p>}
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--primary)' }}>최저 ₩21,900</p>
                  <p style={{ fontSize: 11, color: 'var(--ink-faint)' }}>mg당 ₩0.24</p>
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
