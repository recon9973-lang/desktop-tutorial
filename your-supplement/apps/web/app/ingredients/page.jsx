'use client';
import { useState } from 'react';
import { ingredients, evById, topBenefit, doseLine, STRENGTH, DUR_LABEL } from '../../lib/kb';

export default function IngredientsPage() {
  const [open, setOpen] = useState(null);

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 24px 28px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 14, display: 'inline-flex' }}>
            {ingredients.length}개 성분
          </span>
          <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.6, marginBottom: 6 }}>📖 성분 사전</h1>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.72)' }}>효능·근거·용량·주의를 출처와 함께</p>
        </div>
      </div>

      <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px' }}>
        {ingredients.map((i) => {
          const e = evById[i.id];
          const tb = topBenefit(i.id);
          const st = tb ? STRENGTH[tb.evidence_strength] : null;
          const kr = e && e.kr_source;
          const isOpen = open === i.id;
          const dose = doseLine(i.id);
          return (
            <div key={i.id} className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 12 }}>
              <div onClick={() => setOpen(isOpen ? null : i.id)} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <strong style={{ fontSize: 16 }}>{i.name_ko}</strong>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: '#f5b800', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>{'⭐'.repeat(i.evidence?.level || 0)}</span>
                {st && <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: st[1], borderRadius: 'var(--r-full)', padding: '2px 8px' }}>{st[0]}</span>}
                <span style={{ marginLeft: 'auto', color: 'var(--ink-faint)' }}>{isOpen ? '▴' : '▾'}</span>
              </div>
              <p style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 4 }}>{(i.functions || []).join(' · ')}</p>

              {isOpen && (
                <div style={{ marginTop: 8 }}>
                  {kr && kr.mfds_function && (
                    <div style={{ fontSize: 12.5, marginTop: 8 }}>
                      🇰🇷 <strong>{kr.verified ? '식약처 인정' : '식약처 고시 기능성'}</strong>{' '}
                      {!kr.verified && <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: '#0d9488', borderRadius: 'var(--r-full)', padding: '1px 7px' }}>고시 표준문구</span>}{' '}
                      “{kr.mfds_function}”{' '}
                      {kr.verified && kr.url && (
                        <a href={kr.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', fontWeight: 600, textDecoration: 'none' }}>원문 →</a>
                      )}
                    </div>
                  )}
                  {(e?.benefits || []).map((b, k) => {
                    const s2 = STRENGTH[b.evidence_strength];
                    return (
                      <div key={k} style={{ marginTop: 6, fontSize: 13 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: s2[1], borderRadius: 'var(--r-full)', padding: '2px 8px' }}>{s2[0]}</span>{' '}
                        <span style={{ color: 'var(--ink-muted)' }}>{b.claim}</span>{' '}
                        {b.citation?.url && (
                          <a href={b.citation.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', fontWeight: 600, textDecoration: 'none' }}>{b.citation.source} →</a>
                        )}
                      </div>
                    );
                  })}
                  {dose && <p style={{ fontSize: 12.5, color: 'var(--ink-muted)', marginTop: 6 }}>📐 {dose}</p>}
                  <p style={{ fontSize: 12.5, color: 'var(--ink-muted)', marginTop: 4 }}>💊 제품 표기 {i.daily_dose} · {DUR_LABEL[i.duration_type]}</p>
                  {i.cautions?.length > 0 && <p style={{ fontSize: 12.5, color: 'var(--ink-muted)', marginTop: 4 }}>주의: {i.cautions.join(' · ')}</p>}
                  <a href={`/products?ingredient_id=${i.id}`} style={{ display: 'inline-block', marginTop: 10, fontSize: 13, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none', border: '1px solid var(--hairline)', borderRadius: 'var(--r-full)', padding: '6px 14px' }}>🔎 이 성분 제품 찾기 →</a>
                </div>
              )}
            </div>
          );
        })}
        <p className="caption" style={{ color: 'var(--ink-faint)', textAlign: 'center', marginTop: 20, lineHeight: 1.6 }}>
          근거 출처: 식약처 · NIH ODS · NCCIH · PubMed. 질병 진단·치료가 아닌 정보 제공.
        </p>
      </div>
    </div>
  );
}
