'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · 주간 리포트 생성 (규칙 기반, 결정적)
//   설계: docs/plans/geo-ops-os-design.md §1.1 Report, P1 #7
//   원칙(정직성): 통계를 지어내지 않는다. 실제 수집된 성과/실측/업무 데이터에서만 도출.
//   상대지표(delta·완료율·노출률 추세)만 사용. 절대 인용% 하드코딩 없음.
//   buildReport 는 순수 함수 → 오프라인 단위 테스트 대상. LLM 요약은 선택(주입 가능).
// ─────────────────────────────────────────────────────────────────────────

const LABEL = { clicks: '클릭', impressions: '노출', ctr: 'CTR', position: '평균순위', sessions: '세션', conversions: '전환' };
// position 은 낮을수록 좋음 → 개선=delta<0. 그 외는 높을수록 좋음.
function improved(name, delta) {
  if (delta == null) return null;
  return name === 'position' ? delta < 0 : delta > 0;
}

function taskStats(tasks) {
  const t = tasks || [];
  const by = {};
  t.forEach((x) => { const s = x.status || 'backlog'; by[s] = (by[s] || 0) + 1; });
  const done = by.done || 0;
  return {
    total: t.length, done, byStatus: by,
    completionRate: t.length ? Math.round(done / t.length * 100) : 0,
    approvalPending: t.filter((x) => x.approvalStatus === 'pending').length,
    failed: by.failed || 0,
  };
}

// input: { client, period, metricsSummary:[{metricName,latest,prev,delta}], exposure:{tot_pct,disc_pct,errors}|null, tasks:[] }
function buildReport(input, nowIso) {
  input = input || {};
  const client = input.client || {};
  const ms = input.metricsSummary || [];
  const ex = input.exposure || null;
  const ts = taskStats(input.tasks);

  const keyWins = [], risks = [], nextActions = [];

  // 성과 델타
  ms.forEach((m) => {
    const lab = LABEL[m.metricName] || m.metricName;
    const imp = improved(m.metricName, m.delta);
    if (imp === true) keyWins.push(`${lab} 개선: ${m.latest} (직전 대비 ${m.delta > 0 ? '+' : ''}${m.delta})`);
    else if (imp === false) risks.push(`${lab} 악화: ${m.latest} (직전 대비 ${m.delta > 0 ? '+' : ''}${m.delta})`);
  });

  // AI 인용(실측)
  if (ex) {
    if (typeof ex.disc_pct === 'number') {
      if (ex.disc_pct === 0) { risks.push('발견형(신환) 질문에서 AI 미노출'); nextActions.push('지역·증상 키워드 질문형 콘텐츠 발행 + 플레이스/홈페이지 구조화'); }
      else keyWins.push(`발견형(신환) AI 노출률 ${ex.disc_pct}%`);
    }
    if (typeof ex.tot_pct === 'number' && ex.tot_pct > 0) keyWins.push(`전체 AI 노출률 ${ex.tot_pct}%`);
    if (typeof ex.sov_pct === 'number') {
      if (ex.sov_pct >= 50) keyWins.push(`경쟁사 대비 SOV ${ex.sov_pct}% (우위)`);
      else { risks.push(`경쟁사 대비 SOV ${ex.sov_pct}% (열세)`); nextActions.push('경쟁사 우위 채널 분석 → 해당 채널 콘텐츠 강화'); }
    }
    if (ex.errors) risks.push(`AI 측정불가 ${ex.errors}건 — 재측정 필요`);
  } else {
    nextActions.push('AI 인용 실측 미실행 — 프롬프트셋 등록 후 첫 측정');
  }

  // 업무
  if (ts.approvalPending) nextActions.push(`승인 대기 업무 ${ts.approvalPending}건 처리`);
  if (ts.failed) risks.push(`실패/재작업 업무 ${ts.failed}건`);
  if (ts.total) keyWins.push(`업무 완료율 ${ts.completionRate}% (${ts.done}/${ts.total})`);
  else nextActions.push('채널 플레이북에서 업무 생성');

  if (!nextActions.length) nextActions.push('현 채널 최적화 지속 · 분기 콘텐츠 갱신');

  const summary = assembleSummary(client, ms, ex, ts);

  return {
    id: 'rpt_' + (client.id || 'x') + '_' + (input.period || 'period'),
    clientId: client.id || null,
    clientName: client.name || '',
    reportPeriod: input.period || '',
    reportType: 'weekly',
    summary, keyWins, risks, nextActions,
    data: { metricsSummary: ms, exposure: ex, taskStats: ts },
    generatedAt: nowIso || null,
  };
}

function assembleSummary(client, ms, ex, ts) {
  const parts = [];
  parts.push(`${client.name || '거래처'} · ${client.region || ''} ${client.industry || ''}`.trim());
  if (ex && typeof ex.tot_pct === 'number') parts.push(`AI 노출 전체 ${ex.tot_pct}%·발견형 ${ex.disc_pct != null ? ex.disc_pct + '%' : '—'}${typeof ex.sov_pct === 'number' ? '·SOV ' + ex.sov_pct + '%' : ''}`);
  if (ms.length) {
    const up = ms.filter((m) => improved(m.metricName, m.delta) === true).length;
    const down = ms.filter((m) => improved(m.metricName, m.delta) === false).length;
    parts.push(`성과지표 ${ms.length}종(개선 ${up}·악화 ${down})`);
  }
  if (ts.total) parts.push(`업무 완료율 ${ts.completionRate}%`);
  return parts.join(' · ');
}

module.exports = { buildReport, taskStats, LABEL, improved };
