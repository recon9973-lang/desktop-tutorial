'use strict';

// 자동발행 글 → 영문 번역 (방안 A). OpenAI 사용. 본문(HTML)은 평문으로,
// 메타(제목·설명·키워드)는 작은 JSON으로 분리 호출해 대용량 HTML의 JSON 깨짐을 방지.

const https = require('https');

function chat(messages, { max_tokens, json } = {}) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return Promise.reject(new Error('OPENAI_API_KEY 없음'));
  const body = JSON.stringify({
    model: process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini',
    messages,
    temperature: 0.3,
    ...(json ? { response_format: { type: 'json_object' } } : {}),
    ...(max_tokens ? { max_tokens } : {}),
  });
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'api.openai.com', path: '/v1/chat/completions', method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + key,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        try {
          const j = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          if (j.error) return reject(new Error(j.error.message || 'OpenAI 오류'));
          resolve((j.choices && j.choices[0] && j.choices[0].message.content) || '');
        } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.setTimeout(100000, () => { req.destroy(); reject(new Error('translate timeout')); });
    req.write(body); req.end();
  });
}

const SYS_META = 'You are a professional Korean→English translator for VENOM, a hospital/clinic marketing agency. Translate the given fields to natural, professional English (medical-marketing tone). Keep 베놈→VENOM, 병원마케팅 베놈→VENOM Hospital Marketing. Return STRICT JSON with exactly these keys: title, metaDesc, keywords. No commentary.';

const SYS_HTML = 'You are a professional Korean→English translator for VENOM, a hospital/clinic marketing agency. Translate the Korean text in the following HTML to natural, professional English (medical-marketing tone). Preserve EVERY HTML tag, attribute, inline style, class, id, and URL EXACTLY — translate only human-visible Korean text (including Korean inside alt/title attributes). Keep 베놈→VENOM, 병원마케팅 베놈→VENOM Hospital Marketing. Output ONLY the translated HTML — no markdown code fences, no commentary.';

// 한글 포스트 객체 → 영문 포스트 객체(같은 id/slug/cat/date/status, 내용만 영문)
async function translatePostToEnglish(post) {
  // 1) 메타(작은 JSON)
  let meta = {};
  try {
    const out = await chat([
      { role: 'system', content: SYS_META },
      { role: 'user', content: JSON.stringify({
        title: post.title || '',
        metaDesc: post.metaDesc || post.meta || '',
        keywords: post.keywords || '',
      }) },
    ], { json: true, max_tokens: 700 });
    meta = JSON.parse(out);
  } catch (e) { meta = {}; }

  // 2) 본문 HTML(평문으로 받아 JSON 이스케이프 이슈 회피)
  let html = post.html || '';
  if (html) {
    let t = await chat([
      { role: 'system', content: SYS_HTML },
      { role: 'user', content: html },
    ], { max_tokens: 14000 });
    t = String(t || '').trim().replace(/^```html\s*/i, '').replace(/```$/,'').trim();
    if (t) html = t;
  }

  return {
    ...post,
    lang: 'en',
    title: meta.title || post.title,
    metaDesc: meta.metaDesc || post.metaDesc,
    meta: meta.metaDesc || post.meta,
    keywords: meta.keywords || post.keywords,
    html,
  };
}

module.exports = { translatePostToEnglish };
