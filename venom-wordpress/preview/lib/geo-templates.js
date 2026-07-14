'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · 채널 플레이북 템플릿 → Task 인스턴스화
//   원천: content/geo/checklist-templates.json (docs/plans/geo-ops-os-channel-playbooks.md)
//   설계: 채널의 cap(자동화 상한)을 초과하는 단계 레벨은 cap 으로 클램프.
//         (예: wikipedia cap=C → step.level=A/B 여도 실제 Task 는 C 로 강등 = 자동 실행 원천 차단)
//   buildTasksFromTemplate 는 순수 함수 → 오프라인 단위 테스트 대상.
// ─────────────────────────────────────────────────────────────────────────

const TPL_PATH = 'venom-wordpress/preview/content/geo/checklist-templates.json';
let backend = require('./github-store');
function _setBackend(b) { backend = b; }

// 자동화 강도: A(최대자동) > B > C > D(안내만). cap 초과(더 자동)면 cap 으로 강등.
const RANK = { A: 4, B: 3, C: 2, D: 1 };
function clampLevel(level, cap) {
  const l = RANK[level] || 1, c = RANK[cap] || 1;
  return l > c ? cap : (level || cap);
}

async function loadTemplates() {
  const f = await backend.getJsonFile(TPL_PATH, { templates: [] });
  const c = f && f.content;
  return c && Array.isArray(c.templates) ? c.templates : [];
}

// 템플릿 1개 → 거래처의 Task[] (steps 또는 variants 모두 지원)
function buildTasksFromTemplate(tpl, clientId) {
  if (!tpl || !clientId) return [];
  const cap = tpl.cap || 'D';
  const src = Array.isArray(tpl.steps) ? tpl.steps
    : Array.isArray(tpl.variants) ? tpl.variants.map((v) => ({ step: v.step, level: v.level, channelType: v.channelType }))
    : [];
  return src.map((s) => {
    const level = clampLevel(s.level, cap);
    return {
      clientId,
      channelType: s.channelType || tpl.channelType,
      templateId: tpl.id,
      taskType: tpl.id,
      title: (tpl.id ? tpl.id + ' · ' : '') + (s.step || ''),
      automationLevel: level,
      status: 'backlog',
      // 반자동(B)만 승인 큐 대상. A=자동실행, C/D=인간직접이라 승인 게이트 불필요.
      approvalStatus: level === 'B' ? 'pending' : 'none',
      guard: s.guard || null,
      evidenceField: s.evidence || null,
    };
  });
}

module.exports = { TPL_PATH, RANK, clampLevel, loadTemplates, buildTasksFromTemplate, _setBackend };
