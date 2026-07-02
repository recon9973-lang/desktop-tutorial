'use strict';

const https = require('https');

/**
 * Anthropic Messages API 호출 — openai-client.js 와 동일한 반환 형식
 * @param {string} systemPrompt
 * @param {string} userPrompt
 * @param {object} opts  { model, temperature, max_tokens }
 * @returns {Promise<{text:string, usage:{prompt_tokens:number,completion_tokens:number,total_tokens:number}}>}
 */
function chatComplete(systemPrompt, userPrompt, opts = {}) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error('ANTHROPIC_API_KEY 환경변수가 없습니다.');

  const model = opts.model || process.env.CLAUDE_TEXT_MODEL || 'claude-haiku-4-5-20251001';
  const body = JSON.stringify({
    model,
    max_tokens: opts.max_tokens ?? 2000,
    system: systemPrompt,
    messages: [{ role: 'user', content: userPrompt }],
  });

  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: 'api.anthropic.com',
        path: '/v1/messages',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'Content-Length': Buffer.byteLength(body),
        },
      },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const data = Buffer.concat(chunks).toString('utf8');
          try {
            const json = JSON.parse(data);
            if (json.error) return reject(new Error(json.error.message));
            const block = json.content && json.content.find(b => b.type === 'text');
            if (!block) {
              return reject(new Error('Anthropic 응답에 text block 없음: ' + data.slice(0, 200)));
            }
            const usage = json.usage || {};
            resolve({
              text: block.text.trim(),
              usage: {
                prompt_tokens:     usage.input_tokens  || 0,
                completion_tokens: usage.output_tokens || 0,
                total_tokens:      (usage.input_tokens || 0) + (usage.output_tokens || 0),
              },
            });
          } catch (e) {
            reject(e);
          }
        });
      }
    );
    req.on('error', reject);
    req.setTimeout(90000, () => { req.destroy(); reject(new Error('Claude 텍스트 생성 타임아웃(90초)')); });
    req.write(body);
    req.end();
  });
}

module.exports = { chatComplete };
