'use client';
import { useState } from 'react';

const SHAPES = ['원형', '타원형', '장방형', '반원형', '삼각형', '사각형', '마름모형', '기타'];
const COLORS = [
  ['하양', '#f5f5f5'], ['노랑', '#f5d033'], ['주황', '#ef8a3a'], ['분홍', '#f19bb0'],
  ['빨강', '#e0503a'], ['갈색', '#8a5a3a'], ['초록', '#3aa873'], ['파랑', '#3a7bd5'],
  ['보라', '#8a63c4'], ['회색', '#9aa8a0'], ['검정', '#333'], ['투명', '#e3eae5'],
];

const chip = (on) => ({
  padding: '7px 13px', borderRadius: 'var(--r-full)', cursor: 'pointer', fontSize: 14, margin: 0,
  border: on ? '2px solid var(--primary)' : '1.5px solid var(--hairline)',
  background: on ? 'rgba(5,150,105,0.08)' : 'var(--surface)',
  color: on ? 'var(--primary)' : 'var(--ink)', fontWeight: on ? 600 : 400,
});

export default function DrugPage() {
  const [q, setQ] = useState('');
  const [shape, setShape] = useState('');
  const [color, setColor] = useState('');
  const [imprint, setImprint] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (!q && !shape && !color && !imprint) return;
    setLoading(true); setData(null);
    const qs = new URLSearchParams();
    if (q) qs.set('q', q);
    if (shape) qs.set('shape', shape);
    if (color) qs.set('color', color);
    if (imprint) qs.set('imprint', imprint);
    try {
      const res = await fetch(`/api/drug/search?${qs.toString()}`);
      setData(await res.json());
    } catch { setData({ error: '검색 실패', results: [] }); }
    setLoading(false);
  }

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 24px 28px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 14, display: 'inline-flex' }}>식약처 낱알식별</span>
          <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.6, marginBottom: 6 }}>💊 약 검색·식별</h1>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.72)' }}>이름을 모르면 <strong>모양·색·각인</strong>으로 찾고, 내 영양제와 궁합까지 확인</p>
        </div>
      </div>

      <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px' }}>
        {/* 이름/성분 + 각인 */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && run()}
            placeholder="약 이름·성분 (예: 타이레놀, 아세트아미노펜)"
            style={{ flex: '1 1 200px', border: '1px solid var(--hairline)', borderRadius: 'var(--r-lg)', padding: '11px 14px', fontSize: 15, outline: 'none' }} />
          <input value={imprint} onChange={(e) => setImprint(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && run()}
            placeholder="각인/식별문자 (예: TYLENOL)"
            style={{ flex: '1 1 160px', border: '1px solid var(--hairline)', borderRadius: 'var(--r-lg)', padding: '11px 14px', fontSize: 15, outline: 'none' }} />
        </div>

        {/* 모양 */}
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-secondary)', margin: '8px 0 6px' }}>모양</p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
          {SHAPES.map((s) => <button key={s} onClick={() => setShape(shape === s ? '' : s)} style={chip(shape === s)}>{s}</button>)}
        </div>
        {/* 색 */}
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-secondary)', margin: '8px 0 6px' }}>색상</p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {COLORS.map(([c, hex]) => (
            <button key={c} onClick={() => setColor(color === c ? '' : c)} style={{ ...chip(color === c), display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 13, height: 13, borderRadius: '50%', background: hex, border: '1px solid var(--hairline)', display: 'inline-block' }} />{c}
            </button>
          ))}
        </div>

        <button onClick={run} className="btn-primary" style={{ width: '100%', padding: '12px', fontSize: 16 }}>🔎 약 검색</button>

        {loading && <p style={{ textAlign: 'center', color: 'var(--ink-muted)', padding: 40 }}>검색 중…</p>}

        {data && !data.error && (
          <div style={{ marginTop: 24 }}>
            {data.source === 'mfds' && data.results.length > 0 && (
              <>
                <h2 className="title" style={{ marginBottom: 12 }}>검색 결과 <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-green)', background: 'rgba(22,163,74,0.1)', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>식약처 실데이터</span></h2>
                {data.results.map((r, i) => (
                  <div key={i} className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 12, display: 'flex', gap: 14 }}>
                    {r.image && <img src={r.image} alt={r.name} style={{ width: 72, height: 44, objectFit: 'contain', borderRadius: 8, background: '#fff', flexShrink: 0 }} />}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <strong style={{ fontSize: 15 }}>{r.name}</strong>
                      <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>{r.company}</p>
                      <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginTop: 2 }}>
                        {[r.shape, r.color, r.imprint && `각인 ${r.imprint}`, r.form].filter(Boolean).join(' · ')}
                      </p>
                      <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                        <a href={`/analyze`} style={{ fontSize: 13, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none', border: '1px solid var(--hairline)', borderRadius: 'var(--r-full)', padding: '5px 12px' }}>🧪 내 영양제와 궁합 보기</a>
                        {r.item_seq && <a href={`https://nedrug.mfds.go.kr/pbp/CCBBB01/getItemDetailCache?cacheSeq=${r.item_seq}`} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none', border: '1px solid var(--hairline)', borderRadius: 'var(--r-full)', padding: '5px 12px' }}>상세정보 →</a>}
                      </div>
                    </div>
                  </div>
                ))}
              </>
            )}

            {(data.source !== 'mfds' || data.results.length === 0) && (
              <div className="card" style={{ borderRadius: 'var(--r-xl)', textAlign: 'center', padding: '28px 20px' }}>
                <div style={{ fontSize: 32 }}>💊</div>
                <p style={{ fontSize: 15, fontWeight: 600, marginTop: 6 }}>식약처 낱알식별 검색은 배포+키 설정 시 실데이터로 동작해요</p>
                <p style={{ fontSize: 13, color: 'var(--ink-muted)', margin: '6px 0 16px' }}>지금은 의약품안전나라에서 바로 찾아보세요.</p>
                {data.nedrug_search && (
                  <a href={data.nedrug_search} target="_blank" rel="noopener noreferrer" className="btn-primary" style={{ padding: '10px 22px', fontSize: 15, textDecoration: 'none' }}>의약품안전나라에서 찾기 →</a>
                )}
              </div>
            )}
          </div>
        )}

        <p className="caption" style={{ color: 'var(--ink-faint)', textAlign: 'center', marginTop: 20, lineHeight: 1.6 }}>
          ⚠️ AI·검색 결과는 참고용입니다. <strong>최종 확인은 약사·의사</strong>에게. 데이터: 식약처 의약품 낱알식별 정보.
        </p>
      </div>
    </div>
  );
}
