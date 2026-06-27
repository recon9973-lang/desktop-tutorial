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
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            if (json.error) return reject(new Error(json.error.message));
            resolve(json.choices[0].message.content.trim());
          } catch (e) {
            reject(e);
          }
        });
      }
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

module.exports = { chatComplete };
