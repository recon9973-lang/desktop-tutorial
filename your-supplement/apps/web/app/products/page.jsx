'use client';
import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import ingredientsData from '../../data/ingredients.json';

const INGREDIENTS = ingredientsData.ingredients.map((i) => ({ id: i.id, name: i.name_ko }));

function ProductsInner() {
  const params = useSearchParams();
  const [sel, setSel] = useState(params.get('ingredient_id') || '');
  const [q, setQ] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run(ingredientId, query) {
    setLoading(true); setData(null);
    const qs = ingredientId ? `ingredient_id=${ingredientId}` : `q=${encodeURIComponent(query)}`;
    try {
      const res = await fetch(`/api/products?${qs}`);
      setData(await res.json());
    } catch { setData({ error: '검색 실패' }); }
    setLoading(false);
  }

  // 진입 시 ingredient_id 있으면 자동 검색
  useEffect(() => { if (sel) run(sel); /* eslint-disable-next-line */ }, []);

  const pick = (id) => { setSel(id); setQ(''); run(id); };

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 24px 28px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 14, display: 'inline-flex' }}>
            제품 찾기
          </span>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.6, marginBottom: 6 }}>🔎 이 성분이 든 영양제</h1>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.72)' }}>성분을 고르면 실제 시판 제품을 찾아드려요 (해외 NIH DSLD 20만건+ · 국내 쇼핑 검색)</p>
        </div>
      </div>

      <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px' }}>
        {/* free search */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input value={q} onChange={(e) => { setQ(e.target.value); setSel(''); }}
            onKeyDown={(e) => e.key === 'Enter' && q && run('', q)}
            placeholder="성분·제품명 검색 (예: vitamin d, omega-3)"
            style={{ flex: 1, border: '1px solid var(--hairline)', borderRadius: 'var(--r-lg)', padding: '11px 14px', fontSize: 15, outline: 'none' }} />
          <button onClick={() => q && run('', q)} className="btn-primary" style={{ padding: '0 22px', fontSize: 15 }}>검색</button>
        </div>

        {/* ingredient chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 24 }}>
          {INGREDIENTS.map((it) => (
            <button key={it.id} onClick={() => pick(it.id)}
              style={{
                padding: '7px 14px', borderRadius: 'var(--r-full)', cursor: 'pointer', fontSize: 14,
                border: sel === it.id ? '2px solid var(--primary)' : '1.5px solid var(--hairline)',
                background: sel === it.id ? 'rgba(5,150,105,0.08)' : 'var(--surface)',
                color: sel === it.id ? 'var(--primary)' : 'var(--ink)', fontWeight: sel === it.id ? 600 : 400,
              }}>{it.name}</button>
          ))}
        </div>

        {loading && <p style={{ textAlign: 'center', color: 'var(--ink-muted)', padding: 40 }}>제품 검색 중…</p>}

        {data && !data.error && (
          <>
            {/* 해외 시판 제품(DSLD) */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
              <h2 className="title">🌎 시판 제품 — {data.name_ko}</h2>
              <span style={{ fontSize: 11, fontWeight: 600, borderRadius: 'var(--r-full)', padding: '2px 8px', ...(data.global?.source === 'dsld'
                ? { color: 'var(--accent-green)', background: 'rgba(22,163,74,0.1)' }
                : { color: 'var(--ink-faint)', background: 'var(--hairline)' }) }}>
                {data.global?.source === 'dsld' ? 'NIH DSLD 실시간' : '예시(배포 시 실데이터)'}
              </span>
            </div>
            <div className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 24 }}>
              {(data.global?.products || []).length ? (data.global.products.map((p, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, padding: '10px 0', borderBottom: i < data.global.products.length - 1 ? '1px solid var(--hairline)' : 'none' }}>
                  <div>
                    <strong style={{ fontSize: 15 }}>{p.name}</strong>
                    {p.brand && <span style={{ fontSize: 13, color: 'var(--ink-faint)', marginLeft: 8 }}>{p.brand}</span>}
                  </div>
                  {p.url && <a href={p.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none', whiteSpace: 'nowrap' }}>라벨 →</a>}
                </div>
              ))) : <p style={{ fontSize: 14, color: 'var(--ink-faint)', padding: '8px 0' }}>표시할 제품이 없어요. 국내 검색을 이용해보세요.</p>}
            </div>

            {/* 국내에서 찾기 */}
            <h2 className="title" style={{ marginBottom: 12 }}>🇰🇷 국내에서 찾기</h2>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
              {(data.kr_search || []).map((k) => (
                <a key={k.vendor} href={k.url} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 14, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none', border: '1px solid var(--hairline)', borderRadius: 'var(--r-full)', padding: '8px 16px' }}>
                  {k.vendor} →
                </a>
              ))}
            </div>
            {data.note && <p className="caption" style={{ color: 'var(--ink-faint)', lineHeight: 1.6 }}>{data.note}</p>}
          </>
        )}

        {!data && !loading && (
          <p style={{ textAlign: 'center', color: 'var(--ink-faint)', padding: 40 }}>성분을 고르거나 검색해보세요.</p>
        )}
      </div>
    </div>
  );
}

export default function ProductsPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: 'center', padding: '120px 24px', color: 'var(--ink-muted)' }}>불러오는 중…</div>}>
      <ProductsInner />
    </Suspense>
  );
}
