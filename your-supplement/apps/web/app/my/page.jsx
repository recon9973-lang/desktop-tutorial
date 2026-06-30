'use client';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  loadRoutine, saveRoutine, removeItem, toggleCheck,
  computeStreak, todayProgress, todayBySlot,
  setCheckin, getCheckin, recentCheckins, reviewDue,
} from '../../lib/routine';

const SLOT_LABEL = { morning: '☀️ 아침', evening: '🌙 저녁' };
const DUR_REVIEW = { monitor: '🟡 3개월 점검형', cyclic: '🔴 주기형(8주)' };
// 컨디션 5단계 (1 나쁨 → 5 좋음)
const CONDITION = [
  { v: 1, e: '😣', c: '#d63b3b' },
  { v: 2, e: '😕', c: '#d97706' },
  { v: 3, e: '😐', c: '#9aa8a0' },
  { v: 4, e: '🙂', c: '#0d9488' },
  { v: 5, e: '😄', c: '#059669' },
];
const condColor = (v) => CONDITION.find((c) => c.v === v)?.c || 'var(--hairline)';

export default function MyRoutinePage() {
  const [state, setState] = useState(null); // null = 로딩 중(SSR 안전)
  const [notifyPerm, setNotifyPerm] = useState('default');

  useEffect(() => {
    setState(loadRoutine());
    if (typeof Notification !== 'undefined') setNotifyPerm(Notification.permission);
  }, []);

  const update = useCallback((next) => { setState(next); saveRoutine(next); }, []);

  // 리마인더: 알림 허용 + 켜짐일 때, 페이지가 열려 있는 동안 오늘 남은 시간에 알림.
  // (앱을 닫아도 오는 백그라운드 푸시는 카카오 알림톡/PWA로 별도 — P-later)
  useEffect(() => {
    if (!state?.reminders?.enabled || notifyPerm !== 'granted') return;
    const timers = [];
    const now = new Date();
    for (const slot of ['morning', 'evening']) {
      const [h, m] = (state.reminders[slot] || '').split(':').map(Number);
      if (Number.isNaN(h)) continue;
      const at = new Date(); at.setHours(h, m, 0, 0);
      const delay = at.getTime() - now.getTime();
      if (delay <= 0 || delay > 12 * 3600 * 1000) continue;
      timers.push(setTimeout(() => {
        const due = todayBySlot(loadRoutine()).find((g) => g.slot === slot);
        const left = due?.items.filter((it) => !it.checked).map((it) => it.name) || [];
        if (left.length && typeof Notification !== 'undefined') {
          new Notification('💊 복용 시간이에요', { body: `${SLOT_LABEL[slot]}: ${left.join(', ')}` });
        }
      }, delay));
    }
    return () => timers.forEach(clearTimeout);
  }, [state, notifyPerm]);

  async function enableReminders() {
    if (typeof Notification === 'undefined') {
      update({ ...state, reminders: { ...state.reminders, enabled: !state.reminders.enabled } });
      return;
    }
    let perm = Notification.permission;
    if (perm === 'default') perm = await Notification.requestPermission();
    setNotifyPerm(perm);
    update({ ...state, reminders: { ...state.reminders, enabled: perm === 'granted' } });
  }

  if (!state) {
    return <div style={{ textAlign: 'center', padding: '120px 24px', color: 'var(--ink-muted)' }}>불러오는 중…</div>;
  }

  const streak = computeStreak(state);
  const { done, total } = todayProgress(state);
  const groups = todayBySlot(state);
  const empty = state.items.length === 0;
  const due = reviewDue(state);
  const checkinToday = getCheckin(state);
  const trend = recentCheckins(state, 14);

  return (
    <div style={{ background: 'var(--canvas-soft)', minHeight: '100vh' }}>
      {/* Hero — streak + today progress */}
      <div style={{ background: 'var(--secondary)', color: '#fff', padding: '40px 24px 32px' }}>
        <div style={{ maxWidth: 680, margin: '0 auto' }}>
          <span className="badge" style={{ background: 'rgba(255,255,255,0.12)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)', marginBottom: 14, display: 'inline-flex' }}>
            내 루틴
          </span>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.6, marginBottom: 6 }}>
            {empty ? '🧬 내 영양제를 등록해보세요' : `🔥 ${streak}일 연속 복용 중`}
          </h1>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.72)' }}>
            {empty
              ? '추천 결과에서 추가하면 매일 챙김·알림을 받을 수 있어요'
              : total ? `오늘 ${done}/${total} 완료 ${done === total ? '· 다 챙기셨어요! 🎉' : ''}` : '오늘 복용할 항목이 없어요'}
          </p>
          {!empty && total > 0 && (
            <div style={{ marginTop: 14, height: 8, background: 'rgba(255,255,255,0.15)', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{ width: `${Math.round((done / total) * 100)}%`, height: '100%', background: 'var(--accent-sky)', transition: 'width 0.3s' }} />
            </div>
          )}
        </div>
      </div>

      <div style={{ maxWidth: 680, margin: '0 auto', padding: '24px' }}>
        {empty ? (
          <div className="card" style={{ borderRadius: 'var(--r-xl)', textAlign: 'center', padding: '40px 24px' }}>
            <p style={{ fontSize: 40, marginBottom: 12 }}>📦</p>
            <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>아직 등록된 영양제가 없어요</p>
            <p style={{ fontSize: 14, color: 'var(--ink-muted)', marginBottom: 20 }}>1분 설문으로 추천받고, 결과에서 “내 영양제에 추가”를 눌러주세요</p>
            <Link href="/survey" className="btn-primary" style={{ fontSize: 15, padding: '11px 28px' }}>1분 설문 시작하기 →</Link>
          </div>
        ) : (
          <>
            {/* P3: 점검 리마인드 — monitor/cyclic 경과 시 */}
            {due.length > 0 && (
              <div style={{ background: '#fff8f0', border: '1px solid rgba(217,119,6,0.3)', borderRadius: 'var(--r-xl)', padding: '16px 20px', marginBottom: 20 }}>
                <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--accent-orange)', marginBottom: 8 }}>🔔 점검할 때가 됐어요</p>
                {due.map((it) => (
                  <p key={it.id} style={{ fontSize: 13.5, color: 'var(--ink-secondary)', marginTop: 4 }}>
                    <strong>{it.name}</strong> {DUR_REVIEW[it.duration_type]} · 복용 {it.sinceDays}일째 — 상태를 점검하고 지속 여부를 정하세요.
                  </p>
                ))}
                <Link href="/survey" className="btn-primary" style={{ fontSize: 14, padding: '9px 22px', marginTop: 12 }}>다시 추천받기 →</Link>
              </div>
            )}

            {/* P3: 오늘 컨디션 체크인 + 추세 */}
            <div className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 20 }}>
              <p style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>📊 오늘 컨디션은 어때요?</p>
              <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                {CONDITION.map((c) => (
                  <button key={c.v} onClick={() => update(setCheckin(state, c.v))}
                    style={{
                      flex: 1, padding: '8px 0', borderRadius: 'var(--r-lg)', cursor: 'pointer',
                      border: checkinToday === c.v ? `2px solid ${c.c}` : '1.5px solid var(--hairline)',
                      background: checkinToday === c.v ? `${c.c}14` : 'var(--surface)',
                      fontSize: 24,
                    }}>{c.e}</button>
                ))}
              </div>
              {/* 14일 추세 */}
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 56 }}>
                {trend.map((d, i) => (
                  <div key={d.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', height: '100%' }}>
                    <div title={d.date} style={{
                      height: d.score ? `${(d.score / 5) * 100}%` : '6px',
                      background: d.score ? condColor(d.score) : 'var(--hairline)',
                      borderRadius: 'var(--r-xs)', minHeight: 6,
                      opacity: i === trend.length - 1 ? 1 : 0.85,
                    }} />
                  </div>
                ))}
              </div>
              <p style={{ fontSize: 11.5, color: 'var(--ink-faint)', marginTop: 6, textAlign: 'right' }}>최근 14일 컨디션 추세</p>
            </div>

            {/* Reminder toggle */}
            <div className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <p style={{ fontWeight: 700, fontSize: 15 }}>⏰ 복용 시간 알림</p>
                <p style={{ fontSize: 13, color: 'var(--ink-muted)', marginTop: 2 }}>
                  {state.reminders.enabled && notifyPerm === 'granted'
                    ? `아침 ${state.reminders.morning} · 저녁 ${state.reminders.evening} 알림 켜짐`
                    : '브라우저 알림으로 챙김을 도와드려요'}
                </p>
              </div>
              <button onClick={enableReminders}
                style={{
                  border: 'none', borderRadius: 'var(--r-full)', padding: '9px 20px', cursor: 'pointer',
                  fontWeight: 700, fontSize: 14,
                  background: state.reminders.enabled && notifyPerm === 'granted' ? 'var(--canvas-soft)' : 'var(--primary)',
                  color: state.reminders.enabled && notifyPerm === 'granted' ? 'var(--ink-muted)' : '#fff',
                }}>
                {state.reminders.enabled && notifyPerm === 'granted' ? '끄기' : '알림 켜기'}
              </button>
            </div>
            {state.reminders.enabled && notifyPerm === 'granted' && (
              <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
                {['morning', 'evening'].map((slot) => (
                  <label key={slot} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, color: 'var(--ink-secondary)' }}>
                    {SLOT_LABEL[slot]}
                    <input type="time" value={state.reminders[slot]}
                      onChange={(e) => update({ ...state, reminders: { ...state.reminders, [slot]: e.target.value } })}
                      style={{ border: '1px solid var(--hairline)', borderRadius: 'var(--r-md)', padding: '6px 10px', fontSize: 14 }} />
                  </label>
                ))}
              </div>
            )}
            {notifyPerm === 'denied' && (
              <p style={{ fontSize: 12.5, color: 'var(--accent-orange)', marginBottom: 16 }}>
                브라우저 알림이 차단돼 있어요. 주소창 옆 설정에서 허용하면 알림을 받을 수 있어요.
              </p>
            )}

            {/* Today checklist */}
            <h2 className="title" style={{ marginBottom: 12 }}>오늘 복용 체크</h2>
            {groups.map((g) => (
              <div key={g.slot} className="card" style={{ borderRadius: 'var(--r-xl)', marginBottom: 12 }}>
                <p style={{ fontWeight: 700, fontSize: 14, color: 'var(--ink-secondary)', marginBottom: 10 }}>{SLOT_LABEL[g.slot]}</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {g.items.map((it) => (
                    <button key={it.id} onClick={() => update(toggleCheck(state, it.id, g.slot))}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 12, textAlign: 'left',
                        background: it.checked ? 'rgba(5,150,105,0.08)' : 'var(--surface)',
                        border: `1.5px solid ${it.checked ? 'var(--primary)' : 'var(--hairline)'}`,
                        borderRadius: 'var(--r-lg)', padding: '12px 14px', cursor: 'pointer',
                      }}>
                      <span style={{
                        width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                        background: it.checked ? 'var(--primary)' : 'transparent',
                        border: it.checked ? 'none' : '2px solid var(--hairline)',
                        color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
                      }}>{it.checked ? '✓' : ''}</span>
                      <span style={{ fontSize: 15, fontWeight: 600, color: it.checked ? 'var(--ink-muted)' : 'var(--ink)', textDecoration: it.checked ? 'line-through' : 'none' }}>
                        {it.name}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}

            {/* My supplements (manage) */}
            <h2 className="title" style={{ margin: '24px 0 12px' }}>내 영양제 ({state.items.length})</h2>
            <div className="card" style={{ borderRadius: 'var(--r-xl)' }}>
              {state.items.map((it, i) => (
                <div key={it.id} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                  padding: '10px 0', borderBottom: i < state.items.length - 1 ? '1px solid var(--hairline)' : 'none',
                }}>
                  <div>
                    <strong style={{ fontSize: 15 }}>{it.name}</strong>
                    <span style={{ fontSize: 12, color: 'var(--ink-faint)', marginLeft: 8 }}>
                      {it.slots.map((s) => SLOT_LABEL[s]).join(' · ')}
                    </span>
                  </div>
                  <button onClick={() => update(removeItem(state, it.id))}
                    style={{ background: 'none', border: 'none', color: 'var(--ink-faint)', cursor: 'pointer', fontSize: 13, textDecoration: 'underline' }}>
                    삭제
                  </button>
                </div>
              ))}
            </div>

            <p className="caption" style={{ color: 'var(--ink-faint)', textAlign: 'center', marginTop: 20, lineHeight: 1.6 }}>
              기록은 이 기기에 저장돼요(localStorage). 앱을 닫아도 오는 알림은 추후 카카오 알림톡으로 지원 예정.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
