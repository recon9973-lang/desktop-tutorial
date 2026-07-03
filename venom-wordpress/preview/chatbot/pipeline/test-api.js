'use strict';

/**
 * 챗봇 API 오프라인 스모크 테스트 — 네트워크·LLM 키 없이 핸들러를 직접 호출해 검증.
 * 실행:  node pipeline/test-api.js
 */

const handler = require('../../api/chatbot.js');

function mockRes() {
  return {
    _status: 0, _json: null, _headers: {},
    setHeader(k, v) { this._headers[k] = v; },
    status(c) { this._status = c; return this; },
    json(o) { this._json = o; return this; },
    end() { return this; },
  };
}
async function call(method, body) {
  const req = { method, body };
  const res = mockRes();
  await handler(req, res);
  return res;
}

(async () => {
  let ok = 0, fail = 0;
  const check = (cond, label) => { if (cond) { ok++; console.log('  ✓', label); } else { fail++; console.log('  ✗', label); } };

  console.log('1) GET 상태');
  const g = await call('GET');
  check(g._status === 200 && g._json.kb.chunks > 0, `지식베이스 ${g._json.kb.chunks}청크, LLM=${g._json.llm}`);

  console.log('2) POST qa — 근거 인용 답변');
  const q = await call('POST', { message: '사전심의 대상 매체 10만명 기준이 뭔가요?' });
  check(q._status === 200 && q._json.grounded && q._json.sources.length > 0,
    `grounded=${q._json.grounded}, 근거 ${q._json.sources.length}건, 최상위=${q._json.sources[0].legalRefs.join(',')}`);
  check(/제57조|10만/.test(q._json.answer), '답변에 제57조/10만 근거 포함');

  console.log('3) POST diagnose — 문구 자가진단');
  const d = await call('POST', { message: '세계 최초, 100% 완치를 보장하는 부작용 없는 시술!', mode: 'diagnose' });
  const diag = d._json.diagnosis;
  check(d._status === 200 && diag.pass === false && diag.forbidden.length > 0,
    `위반 탐지 ${diag.forbidden.length}건: ${diag.forbidden.slice(0, 4).join(', ')}…`);
  check(!!diag.suggestion, `안전 대체안 생성: "${(diag.suggestion || '').slice(0, 40)}…"`);

  console.log('4) 검증 — 빈 message 거부');
  const e = await call('POST', { message: '' });
  check(e._status === 400, '빈 입력 400 반환');

  console.log(`\n결과: ${ok} 통과, ${fail} 실패`);
  process.exit(fail ? 1 : 0);
})();
