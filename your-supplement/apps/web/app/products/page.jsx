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
  const [safety, setSafety] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run(ingredientId, query) {
    setLoading(true); setData(null); setSafety(null); setEvidence(null);
    const qs = ingredientId ? `ingredient_id=${ingredientId}` : `q=${encodeURIComponent(query)}`;
    try {
      const res = await fetch(`/api/products?${qs}`);
      setData(await res.json());
    } catch { setData({ error: '검색 실패' }); }
    setLoading(false);
    // 이상사례(openFDA)·임상연구(PubMed)는 비차단으로 뒤따라 로드
    fetch(`/api/safety?${qs}`).then((r) => r.json()).then(setSafety).catch(() => {});
    fetch(`/api/evidence-search?${qs}`).then((r) => r.json()).then(setEvidence).catch(() => {});
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
            {/* 🛒 국내에서 찾기 — 항상 최상단(어떤 검색어든 동작) */}
            <h2 className="title" style={{ marginBottom: 4 }}>🛒 {data.name_ko} 제품 보기</h2>
            <p style={{ fontSize: 13, color: 'var(--ink-faint)', marginBottom: 12 }}>국내 쇼핑·해외직구·식약처에서 바로 찾기</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>
              {(data.kr_search || []).map((k) => (
                <a key={k.vendor} href={k.url} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 14, fontWeight: 600, textDecoration: 'none', borderRadius: 'var(--r-full)', padding: '10px 18px',
                    ...(k.primary
                      ? { background: 'var(--primary)', color: '#fff' }
                      : { background: 'var(--surface)', color: 'var(--primary)', border: '1.5px solid var(--hairline)' }) }}>
                  {k.vendor} →
                </a>
              ))}
            </div>

            {/* 국내 식약처 품목(설정 시) */}
            {data.kr_products?.products?.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                  <h2 className="title">🇰🇷 국내 건강기능식품</h2>
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-green)', background: 'rgba(22,163,74,0.1)', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>식약처 품목</span>
                </div>
                <div className="card" style={{ borderRadius: 'var(--r-xl)' }}>
                  {data.kr_products.products.map((p, i) => (
                    <div key={i} style={{ padding: '10px 0', borderBottom: i < data.kr_products.products.length - 1 ? '1px solid var(--hairline)' : 'none' }}>
                      <strong style={{ fontSize: 15 }}>{p.name}</strong>
                      {p.brand && <span style={{ fontSize: 13, color: 'var(--ink-faint)', marginLeft: 8 }}>{p.brand}</span>}
                      {p.no && <span style={{ fontSize: 11, color: 'var(--ink-faint)', marginLeft: 8 }}>신고 {p.no}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 이상사례 신호(openFDA) */}
            {safety?.source === 'openfda' && safety.total > 0 && (
              <div style={{ background: '#fff8f0', border: '1px solid rgba(217,119,6,0.3)', borderRadius: 'var(--r-xl)', padding: '14px 18px', marginBottom: 24 }}>
                <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--accent-orange)' }}>⚠️ FDA 이상사례 보고 {safety.total.toLocaleString()}건</p>
                {safety.top_reactions?.length > 0 && (
                  <p style={{ fontSize: 13, color: 'var(--ink-secondary)', marginTop: 6 }}>
                    자주 보고된 증상: {safety.top_reactions.map((r) => r.term).slice(0, 5).join(', ')}
                  </p>
                )}
                <p style={{ fontSize: 11.5, color: 'var(--ink-faint)', marginTop: 6 }}>{safety.disclaimer}</p>
              </div>
            )}

            {/* 관련 임상연구(PubMed) */}
            {evidence?.source === 'pubmed' && evidence.articles?.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <h2 className="title" style={{ marginBottom: 12 }}>📚 관련 임상연구 (PubMed)</h2>
                <div className="card" style={{ borderRadius: 'var(--r-xl)' }}>
                  {evidence.articles.map((a, i) => (
                    <a key={a.pmid} href={a.url} target="_blank" rel="noopener noreferrer"
                      style={{ display: 'block', padding: '10px 0', borderBottom: i < evidence.articles.length - 1 ? '1px solid var(--hairline)' : 'none', textDecoration: 'none' }}>
                      <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>{a.title}</p>
                      <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 2 }}>{a.journal} {a.pubdate && `· ${a.pubdate}`} · PMID {a.pmid} →</p>
                    </a>
                  ))}
                </div>
                {evidence.total > evidence.articles.length && (
                  <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 6 }}>총 {evidence.total.toLocaleString()}건 중 상위 {evidence.articles.length}건 (RCT·메타분석 우선)</p>
                )}
              </div>
            )}

            {/* 🌎 해외 시판 제품(NIH DSLD) — 실제 결과가 있을 때만 표시 */}
            {data.global?.source === 'dsld' && data.global.products?.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                  <h2 className="title">🌎 해외 시판 제품 (참고)</h2>
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-green)', background: 'rgba(22,163,74,0.1)', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>NIH DSLD 실시간</span>
                </div>
                <div className="card" style={{ borderRadius: 'var(--r-xl)' }}>
                  {data.global.products.map((p, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, padding: '10px 0', borderBottom: i < data.global.products.length - 1 ? '1px solid var(--hairline)' : 'none' }}>
                      <div>
                        <strong style={{ fontSize: 15 }}>{p.name}</strong>
                        {p.brand && <span style={{ fontSize: 13, color: 'var(--ink-faint)', marginLeft: 8 }}>{p.brand}</span>}
                      </div>
                      {p.url && <a href={p.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none', whiteSpace: 'nowrap' }}>라벨 →</a>}
                    </div>
                  ))}
                </div>
              </div>
            )}
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
