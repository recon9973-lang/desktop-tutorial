'use strict';

const https = require('https');

/**
 * OpenAI Chat Completions 호출
 * @param {string} systemPrompt
 * @param {string} userPrompt
 * @param {object} opts  { model, temperature, max_tokens }
 * @returns {Promise<string>}
 */
function chatComplete(systemPrompt, userPrompt, opts = {}) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error('OPENAI_API_KEY 환경변수가 없습니다.');

  const model = opts.model || process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini';
  const body = JSON.stringify({
    model,
    temperature: opts.temperature ?? 0.7,
    max_tokens: opts.max_tokens ?? 2000,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ],
  });

  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: 'api.openai.com',
        path: '/v1/chat/completions',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
          'Content-Length': Buffer.byteLength(body),
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
            if (json.error) return reject(new Error(json.error.message));
            const choice = json.choices && json.choices[0];
            if (!choice || !choice.message) {
              return reject(new Error('OpenAI 응답에 choices 없음: ' + data.slice(0, 200)));
            }
            resolve({
              text: choice.message.content.trim(),
              usage: json.usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
            });
          } catch (e) {
            reject(e);
          }
        });
      }
    );
    req.on('error', reject);
    req.setTimeout(60000, () => { req.destroy(); reject(new Error('OpenAI 텍스트 생성 타임아웃(60초)')); });
    req.write(body);
    req.end();
  });
}

module.exports = { chatComplete };
