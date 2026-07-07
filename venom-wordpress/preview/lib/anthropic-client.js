'use strict';

const https = require('https');

/**
 * Anthropic Messages API 호출 (Claude 두뇌)
 *
 *  - 엔드포인트: POST https://api.anthropic.com/v1/messages
 *  - 헤더: x-api-key, anthropic-version, content-type
 *  - 기본 모델: claude-opus-4-8 (ANTHROPIC_MODEL 환경변수로 교체 가능)
 *
 * ⚠️ Opus 4.8 계열은 temperature/top_p/top_k 를 보내면 400 오류가 나므로 전송하지 않는다.
 *
 * @param {string} systemPrompt
 * @param {string} userPrompt
 * @param {object} opts  { model, max_tokens }
 * @returns {Promise<{text, usage}>}
 */
function chatComplete(systemPrompt, userPrompt, opts = {}) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error('ANTHROPIC_API_KEY 환경변수가 없습니다.');

  const model = opts.model || process.env.ANTHROPIC_MODEL || 'claude-opus-4-8';
  const body = JSON.stringify({
    model,
    max_tokens: opts.max_tokens ?? 2000,
    system: systemPrompt,
    messages: [
      { role: 'user', content: userPrompt },
    ],
  });

  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: 'api.anthropic.com',
        path: '/v1/messages',
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'content-length': Buffer.byteLength(body),
        },
      },
      (res) => {
        // 청크를 Buffer로 모아 마지막에 한 번에 UTF-8 디코딩.
        // data += c 방식은 한글(3바이트)이 청크 경계에서 잘려 깨짐(�)이 발생함.
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const data = Buffer.concat(chunks).toString('utf8');
          try {
            const json = JSON.parse(data);
            if (json.error) return reject(new Error(json.error.message || JSON.stringify(json.error)));
            const block = Array.isArray(json.content) && json.content.find(b => b.type === 'text');
            if (!block) {
              return reject(new Error('Anthropic 응답에 text 블록 없음: ' + data.slice(0, 200)));
            }
            resolve({
              text: block.text.trim(),
              usage: json.usage || { input_tokens: 0, output_tokens: 0 },
            });
          } catch (e) {
            reject(e);
          }
        });
      }
    );
    req.on('error', reject);
    req.setTimeout(60000, () => { req.destroy(); reject(new Error('Anthropic 텍스트 생성 타임아웃(60초)')); });
    req.write(body);
    req.end();
  });
}

module.exports = { chatComplete };
