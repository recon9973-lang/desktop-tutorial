'use client';
import { useState } from 'react';
import { ingredients, meds, byId, evById, relation, drugCheck } from '../../lib/kb';

const chip = (on) => ({
  padding: '7px 14px', borderRadius: 'var(--r-full)', cursor: 'pointer', fontSize: 14, margin: 0,
  border: on ? '2px solid var(--primary)' : '1.5px solid var(--hairline)',
  background: on ? 'rgba(5,150,105,0.08)' : 'var(--surface)',
  color: on ? 'var(--primary)' : 'var(--ink)', fontWeight: on ? 600 : 400,
});

const realUL = (id) => {
  const ul = evById[id]?.dosing?.ul;
  return ul && ul !== '출처 미확인' ? ul : null;
};

export default function AnalyzePage() {
  const [stack, setStack] = useState([]);
  const [stackMeds, setStackMeds] = useState([]);
  const toggle = (arr, set, v) => set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  // 약물 충돌
  const dconf = [];
  stack.forEach((id) => {
    const dc = drugCheck(id, stackMeds);
    if (dc.action === 'exclude') dconf.push('🚫 ' + byId[id].name_ko + ' — ' + dc.excludeReason);
    dc.warnings.forEach((w) => dconf.push('⚠️ ' + byId[id].name_ko + ' — ' + w));
  });
  // 길항/시너지/모니터
  const ant = [], syn = [], mon = [];
  for (let i = 0; i < stack.length; i++)
    for (let j = i + 1; j < stack.length; j++) {
      const r = relation(stack[i], stack[j]);
      if (!r) continue;
      const a = byId[stack[i]].name_ko, b = byId[stack[j]].name_ko;
      if (r.type === 'antagonism') {
        if (r.mode === 'monitor') mon.push('🩺 ' + a + ' ↔ ' + b + ': ' + r.problem + ' — ' + r.timing);
        else ant.push('⚠️ ' + a + ' ↔ ' + b + ': ' + r.problem + ' (' + r.timing + ')');
      } else syn.push('🔗 ' + a + ' + ' + b + ': ' + r.effect);
    }
  // 상한(UL) 주의
  const ul = stack.map((id) => (realUL(id) ? { n: byId[id].name_ko, ul: realUL(id) } : null)).filter(Boolean);
  // 카테고리 중복
  const cat = {};
  stack.forEach((id) => { const c = byId[id].category || '기타'; (cat[c] = cat[c] || []).push(byId[id].name_ko); });
  const dupCat = Object.entries(cat).filter(([, v]) => v.length > 1);
  // 복용 시간(monitor 제외 길항만 분리)
  const m2 = [], e2 = [];
  stack.forEach((id) => {
    const cf = m2.some((x) => { const r = relation(x, id); return r?.type === 'antagonism' && r.mode !== 'monitor'; });
    (cf ? e2 : m2).push(id);
  });
  const hasRisk = dconf.length || ant.length || mon.length;
  const names = (arr) => arr.map((x) => byId[x].name_ko).join(', ') || '없음';

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 24px 28px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 14, display: 'inline-flex' }}>근거 기반</span>
          <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.6, marginBottom: 6 }}>🧪 내 조합 분석</h1>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.72)' }}>지금 먹는 영양제를 고르면 궁합·과다·약물충돌을 근거로 점검</p>
        </div>
      </div>

      <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px' }}>
        <h2 className="title" style={{ marginBottom: 10 }}>먹는 영양제 선택</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
          {ingredients.map((i) => (
            <button key={i.id} onClick={() => toggle(stack, setStack, i.id)} style={chip(stack.includes(i.id))}>{i.name_ko}</button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 10 }}>
          <h2 className="title" style={{ margin: 0 }}>복용 중인 약 (선택)</h2>
          <a href="/drug" style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--primary)', textDecoration: 'none' }}>
            💊 약 이름 몰라요? 모양·사진으로 찾기 →
          </a>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
          {Object.entries(meds).map(([k, v]) => (
            <button key={k} onClick={() => toggle(stackMeds, setStackMeds, k)} style={chip(stackMeds.includes(k))}>💊 {v.label}</button>
          ))}
        </div>

        {stack.length < 1 ? (
          <p style={{ color: 'var(--ink-muted)' }}>성분을 1개 이상 선택하면 분석이 나와요.</p>
        ) : (
          <>
            <div style={{ borderRadius: 'var(--r-xl)', padding: '14px 18px', marginBottom: 16, ...(hasRisk
              ? { background: '#fff8f0', border: '1px solid rgba(217,119,6,0.3)' }
              : { background: 'rgba(5,150,105,0.06)', border: '1px solid rgba(5,150,105,0.2)' }) }}>
              <p style={{ fontSize: 15, fontWeight: 700, color: hasRisk ? 'var(--accent-orange, #d97706)' : '#047857' }}>
                {hasRisk ? '⚠️ 주의가 필요한 조합이 있어요' : '✅ 큰 충돌은 없어요'}
              </p>
              {dconf.map((x, k) => <p key={k} style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 6 }}>{x}</p>)}
              {ant.map((x, k) => <p key={k} style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 6 }}>{x} — 시간 분리 권장</p>)}
            </div>

            {mon.length > 0 && (
              <div className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 16 }}>
                <strong>🩺 함께 복용 시 점검 권장</strong>
                {mon.map((x, k) => <p key={k} style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 6 }}>{x}</p>)}
              </div>
            )}
            {syn.length > 0 && (
              <div style={{ borderRadius: 'var(--r-xl)', padding: '14px 18px', marginBottom: 16, background: 'rgba(5,150,105,0.06)', border: '1px solid rgba(5,150,105,0.2)' }}>
                <strong style={{ color: '#047857' }}>🔗 함께 먹으면 좋아요</strong>
                {syn.map((x, k) => <p key={k} style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 6 }}>{x}</p>)}
              </div>
            )}
            {ul.length > 0 && (
              <div className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 16 }}>
                <strong>📐 상한(UL) 주의 — 여러 제품 합산 시 초과 주의</strong>
                {ul.map((x, k) => <p key={k} style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 4 }}>{x.n}: 상한 {x.ul}</p>)}
              </div>
            )}
            {dupCat.length > 0 && (
              <div className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 16 }}>
                <strong>🧩 같은 계열 중복</strong>
                {dupCat.map(([c, v]) => <p key={c} style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 4 }}>{c}: {v.join(', ')} — 성분 겹침 확인</p>)}
              </div>
            )}
            <div className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 16 }}>
              <strong>📅 추천 복용 시간</strong>
              <p style={{ fontSize: 13.5, color: 'var(--ink-muted)', marginTop: 6 }}>☀️ 아침: {names(m2)}</p>
              <p style={{ fontSize: 13.5, color: 'var(--ink-muted)' }}>🌙 저녁: {names(e2)}</p>
            </div>
            <p className="caption" style={{ color: 'var(--ink-faint)', lineHeight: 1.6 }}>
              성분 궁합·상한·상호작용은 식약처·NIH 근거 기반. 실제 제품 라벨의 함량 합산은 별도 확인하세요.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
