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
    const clean = (s) => String(s || '').trim().replace(/^```html\s*/i, '').replace(/```$/, '').trim();
    const koRatio = (s) => {
      const v = String(s || '').replace(/<[^>]+>/g, ' ');           // 태그 제거 후 가시 텍스트
      const ko = (v.match(/[가-힣]/g) || []).length, en = (v.match(/[A-Za-z]/g) || []).length;
      return (ko + en) ? ko / (ko + en) : 0;
    };
    let t = clean(await chat([{ role: 'system', content: SYS_HTML }, { role: 'user', content: html }], { max_tokens: 14000 }));
    // 모델이 한글을 그대로 반환(에코)하거나 일부만 번역한 경우 1회 재시도
    if (!t || koRatio(t) > 0.3) {
      t = clean(await chat([
        { role: 'system', content: SYS_HTML + ' The previous attempt left Korean untranslated; translate ALL Korean to English this time.' },
        { role: 'user', content: html },
      ], { max_tokens: 14000 }));
    }
    // 재시도 후에도 한글이 많으면 실패로 간주 → 한글을 영문으로 저장하지 않음(호출부가 EN 저장 스킵)
    if (!t || koRatio(t) > 0.3) throw new Error('영문 번역 실패: 한글 잔존(' + Math.round(koRatio(t) * 100) + '%)');
    html = t;
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
