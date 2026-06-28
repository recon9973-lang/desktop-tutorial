'use client';
import { useEffect, useState } from 'react';

const TABS = [
  { id: 'pharmacy', label: '💊 문 연 약국', desc: '지금 영업 중인 약국' },
  { id: 'er',       label: '🚨 응급실',     desc: '24시간 응급의료' },
  { id: 'kids',     label: '🌙 야간 소아',  desc: '달빛어린이병원' },
];

// 현재 시각 기준 영업 여부 계산 (HH:MM 문자열 비교)
function openStatus(item) {
  if (item.is24h) return { open: true, label: '24시간' };
  if (!item.open || !item.close) return { open: null, label: '시간 정보 없음' };
  const now = new Date();
  const cur = now.getHours() * 60 + now.getMinutes();
  const [oh, om] = item.open.split(':').map(Number);
  let [ch, cm] = item.close.split(':').map(Number);
  const openMin = oh * 60 + om;
  let closeMin = ch * 60 + cm;
  if (closeMin === 0) closeMin = 24 * 60; // 24:00 처리
  const isOpen = cur >= openMin && cur < closeMin;
  return { open: isOpen, label: isOpen ? `영업 중 · ${item.close}까지` : `영업 종료 · ${item.open} 오픈` };
}

const kakaoDirections = (it) =>
  `https://map.kakao.com/link/to/${encodeURIComponent(it.name)},${it.lat},${it.lng}`;

export default function NearbyPage() {
  const [tab, setTab] = useState('pharmacy');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/nearby?type=${tab}`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [tab]);

  const current = TABS.find((t) => t.id === tab);

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      {/* Hero */}
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 24px 28px' }}>
        <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 14, display: 'inline-flex' }}>
          공공데이터 기반
        </span>
        <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.6, marginBottom: 6 }}>🗺️ 가까운 의료기관</h1>
        <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.72)' }}>지금 문 연 약국 · 응급실 · 야간 소아진료를 찾아보세요</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, padding: '16px 24px 0', maxWidth: 720, margin: '0 auto', flexWrap: 'wrap' }}>
        {TABS.map((t) => {
          const active = t.id === tab;
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                flex: '1 1 0', minWidth: 130, padding: '12px 10px', borderRadius: 'var(--r-lg)',
                border: active ? '2px solid var(--primary)' : '1.5px solid var(--hairline)',
                background: active ? 'rgba(0,117,222,0.06)' : 'var(--surface)',
                cursor: 'pointer', textAlign: 'center',
              }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: active ? 'var(--primary)' : 'var(--ink)' }}>{t.label}</div>
              <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 2 }}>{t.desc}</div>
            </button>
          );
        })}
      </div>

      {/* List */}
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '20px 24px 48px' }}>
        {/* Location note */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
          <p style={{ fontSize: 14, color: 'var(--ink-muted)' }}>📍 서울 강남구 기준</p>
          {data?.source === 'sample'
            ? <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-faint)', background: 'var(--hairline)', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>샘플 데이터</span>
            : <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-green)', background: 'rgba(26,174,57,0.1)', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>실시간 공공데이터</span>}
        </div>

        {loading && <p style={{ textAlign: 'center', color: 'var(--ink-muted)', padding: 40 }}>불러오는 중...</p>}

        {!loading && data?.items?.map((it, i) => {
          const st = openStatus(it);
          return (
            <div key={i} className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                    <strong style={{ fontSize: 17 }}>{it.name}</strong>
                    {(it.tags || []).map((tag) => (
                      <span key={tag} style={{ fontSize: 11, fontWeight: 600, color: 'var(--primary)', background: 'rgba(0,117,222,0.08)', borderRadius: 'var(--r-full)', padding: '2px 8px' }}>{tag}</span>
                    ))}
                  </div>
                  {/* 영업 상태 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: st.open ? 'var(--accent-green)' : st.open === false ? '#d63b3b' : 'var(--ink-faint)',
                    }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: st.open ? 'var(--accent-green)' : st.open === false ? '#d63b3b' : 'var(--ink-muted)' }}>
                      {st.label}
                    </span>
                    {it.beds != null && (
                      <span style={{ fontSize: 12, color: 'var(--ink-muted)', marginLeft: 6 }}>· 가용 병상 {it.beds}</span>
                    )}
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--ink-muted)' }}>📍 {it.addr}</p>
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <a href={`tel:${it.tel}`}
                  style={{ flex: 1, textAlign: 'center', padding: '9px 0', borderRadius: 'var(--r-full)', background: 'var(--primary)', color: '#fff', fontWeight: 600, fontSize: 14, textDecoration: 'none' }}>
                  📞 전화
                </a>
                {it.lat && it.lng && (
                  <a href={kakaoDirections(it)} target="_blank" rel="noopener noreferrer"
                    style={{ flex: 1, textAlign: 'center', padding: '9px 0', borderRadius: 'var(--r-full)', background: 'var(--surface)', color: 'var(--ink)', border: '1.5px solid var(--hairline)', fontWeight: 600, fontSize: 14, textDecoration: 'none' }}>
                    🧭 길찾기
                  </a>
                )}
              </div>
            </div>
          );
        })}

        {!loading && (!data?.items || data.items.length === 0) && (
          <p style={{ textAlign: 'center', color: 'var(--ink-faint)', padding: 40 }}>표시할 곳이 없어요.</p>
        )}

        {/* Disclaimer */}
        <p className="caption" style={{ color: 'var(--ink-faint)', textAlign: 'center', marginTop: 24, lineHeight: 1.6 }}>
          ⚠️ 영업시간·응급실 병상은 변동될 수 있어요. 방문 전 <strong>전화로 확인</strong>하세요.<br />
          응급상황은 <strong>119</strong>에 먼저 연락하세요.
        </p>
      </div>
    </div>
  );
}
