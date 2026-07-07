'use strict';

/**
 * LLM-as-Judge — 챗봇 답변 품질을 Claude로 채점한다.
 *
 * 주어진 [질문]·[검색된 근거]·[챗봇 답변]에 대해 근거충실도·법적정확성·인용정확성을
 * 1~5로 채점하고, 근거에 없는 내용을 지어냈는지(할루시네이션)와 합격 여부를 판정한다.
 * 채점은 답변 생성보다 가벼워도 되므로 기본 모델을 빠른 모델로 둔다(ANTHROPIC_JUDGE_MODEL).
 *
 * 개발환경엔 키가 없어 실행되지 않는다 → 배포(Vercel, ANTHROPIC_API_KEY)에서 동작.
 */

let anthropic = null;
try { anthropic = require('../../lib/anthropic-client'); } catch (e) {}

const JUDGE_SYSTEM = [
  '당신은 한국 의료광고법·의료광고심의 채점관이다.',
  '아래 [질문], [검색된 근거], [챗봇 답변]을 보고 답변 품질을 엄격히 채점한다.',
  '판단은 반드시 [검색된 근거]와 한국 의료법(제56·57조)·표시광고법·심의기준에 근거한다.',
  '특히 다음 오류를 잡아낸다: (1) 근거에 있는 예외·단서를 누락(예: 심의 대상 매체라도 정보성 항목만이면 제57조 제3항에 따라 심의 면제), (2) 근거에 없는 내용을 지어냄, (3) 근거 조항 오인용, (4) 과도한 단정.',
  '출력은 아래 JSON 한 개만. 설명·코드펜스 없이 순수 JSON.',
  '{"grounding":1-5,"correctness":1-5,"citation":1-5,"hallucination":true|false,"verdict":"pass"|"fail","reason":"한 줄 근거"}',
  'grounding=근거 충실도, correctness=법적 정확성, citation=근거조항 인용 정확성. 하나라도 심각히 틀리면 verdict=fail.',
].join('\n');

function parseJudge(text) {
  let t = String(text).trim().replace(/^```(json)?/i, '').replace(/```$/,'').trim();
  const m = t.match(/\{[\s\S]*\}/);
  if (m) t = m[0];
  const j = JSON.parse(t);
  const clamp = n => Math.max(1, Math.min(5, Number(n) || 1));
  return {
    grounding: clamp(j.grounding),
    correctness: clamp(j.correctness),
    citation: clamp(j.citation),
    hallucination: !!j.hallucination,
    verdict: j.verdict === 'pass' ? 'pass' : 'fail',
    reason: String(j.reason || '').slice(0, 300),
  };
}

/**
 * 답변 1건 채점.
 * @param {{question, answer, context}} arg  context=검색된 근거 텍스트 블록
 * @returns {Promise<{grounding,correctness,citation,hallucination,verdict,reason}>}
 */
async function judgeAnswer({ question, answer, context }) {
  if (!anthropic || !process.env.ANTHROPIC_API_KEY) {
    throw new Error('ANTHROPIC_API_KEY 없음 — 채점은 배포(Vercel)에서 실행하세요.');
  }
  const model = process.env.ANTHROPIC_JUDGE_MODEL || 'claude-haiku-4-5';
  const userPrompt =
    `[질문]\n${question}\n\n[검색된 근거]\n${context || '(근거 없음)'}\n\n[챗봇 답변]\n${answer}\n\n` +
    `위 답변을 채점해 JSON으로만 답하라.`;
  const { text } = await anthropic.chatComplete(JUDGE_SYSTEM, userPrompt, { model, max_tokens: 400 });
  return parseJudge(text);
}

module.exports = { judgeAnswer, parseJudge, JUDGE_SYSTEM };
