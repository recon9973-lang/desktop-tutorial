'use client';
import { ingredients, rankScore } from '../../lib/kb';

export default function RankPage() {
  const scored = ingredients
    .map((i) => ({ i, ...rankScore(i) }))
    .sort((a, b) => b.score - a.score || (b.i.evidence?.level || 0) - (a.i.evidence?.level || 0));

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 24px 28px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 14, display: 'inline-flex' }}>
            후기·광고 아님
          </span>
          <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.6, marginBottom: 6 }}>🏆 근거 기반 성분 랭킹</h1>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.72)' }}>
            사용자 후기·판매량이 아니라 <strong>인정등급 × 활용도(고민 수)</strong> 기준
          </p>
        </div>
      </div>

      <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px' }}>
        {scored.map((x, idx) => (
          <div key={x.i.id} className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 12, display: 'flex', gap: 14, alignItems: 'flex-start' }}>
            <span style={{
              width: 32, height: 32, flexShrink: 0, borderRadius: 'var(--r-md)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 700, color: '#fff', background: idx < 3 ? 'var(--primary)' : '#cbd5cf',
            }}>{idx + 1}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <strong style={{ fontSize: 16 }}>{x.i.name_ko}</strong>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: '#f5b800', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>{'⭐'.repeat(x.i.evidence?.level || 0)}</span>
              </div>
              <p style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 3 }}>{(x.i.functions || []).slice(0, 2).join(' · ')}</p>
              <div style={{ marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {x.cs.map((c) => (
                  <span key={c.id} style={{ fontSize: 11, fontWeight: 600, color: 'var(--pa, #047857)', background: 'rgba(5,150,105,0.12)', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>{c.emoji} {c.label}</span>
                ))}
              </div>
              <a href={`/ingredients`} style={{ display: 'inline-block', marginTop: 8, fontSize: 13, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none', border: '1px solid var(--hairline)', borderRadius: 'var(--r-full)', padding: '5px 12px' }}>성분 사전에서 자세히 →</a>
            </div>
          </div>
        ))}
        <p className="caption" style={{ color: 'var(--ink-faint)', textAlign: 'center', marginTop: 20, lineHeight: 1.6 }}>
          ⚠️ 이 랭킹은 <strong>사용자 후기·판매량이 아니라</strong> 식약처 인정등급과 활용 고민 수로 계산한 <strong>근거 지표</strong>입니다.
        </p>
      </div>
    </div>
  );
}
