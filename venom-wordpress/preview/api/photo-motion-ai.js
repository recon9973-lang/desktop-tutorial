'use strict';

/**
 * 사진 한 장 → 움직이는 GIF/WebP 도구(tools/photo-motion.html)의 AI 도우미
 *
 *  POST /api/photo-motion-ai  { image: "data:image/jpeg;base64,...", purpose?: string, tone?: 'calm'|'bright'|'short' }
 *    → { captions: string[3], preset: string, focus: {x,y}, reason: string, provider }
 *  GET  /api/photo-motion-ai  → { llm: boolean, provider }
 *
 * 키가 있는 회사 순서: Anthropic(Claude) → OpenAI. 둘 다 없으면 503.
 * 자막은 의료광고(의료법 제56조) 기준으로 쓰도록 지시한다. 저장소 관례대로 SDK 없이 fetch 로 호출한다(가볍게).
 */

const PRESETS = ['kenburns', 'zoomin', 'zoomout', 'panlr', 'panrl', 'panud', 'breathe', 'sway', 'handheld'];
const MAX_IMAGE_BYTES = 1.5 * 1024 * 1024; // 화면 쪽에서 640px 로 줄여 보내므로 넉넉하다
const RATE = { windowMs: 60 * 60 * 1000, max: 30 }; // 한 주소당 시간당 30번(서버가 살아 있는 동안만 기억)
const hits = new Map();

function pickKey(reList) {
  for (const re of reList) for (const k of Object.keys(process.env)) if (re.test(k) && process.env[k]) return process.env[k];
  return '';
}
const anthropicKey = () => pickKey([/^ANTHROPIC_API_KEY$/, /ANTHROPIC.*KEY$/, /^CLAUDE_API_KEY$/]);
const openaiKey = () => process.env.OPENAI_API_KEY || '';
function provider() { return anthropicKey() ? 'anthropic' : openaiKey() ? 'openai' : null; }

async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  const chunks = [];
  await new Promise((resolve, reject) => { req.on('data', c => chunks.push(c)); req.on('end', resolve); req.on('error', reject); });
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) { return {}; }
}

function rateLimited(ip) {
  const now = Date.now(); const arr = (hits.get(ip) || []).filter(t => now - t < RATE.windowMs);
  if (arr.length >= RATE.max) { hits.set(ip, arr); return true; }
  arr.push(now); hits.set(ip, arr); return false;
}

function buildPrompt(purpose, tone) {
  const toneWord = { calm: '차분하고 신뢰감 있는', bright: '밝고 친근한', short: '짧고 강한' }[tone] || '차분하고 신뢰감 있는';
  return `너는 한국 병원·의원 홍보물의 자막을 쓰는 카피라이터다. 첨부한 사진 한 장으로 짧게 움직이는 GIF를 만들고 그 위에 자막을 얹는다.
쓰임새: ${purpose || '(적지 않음 — 사진을 보고 판단)'}
말투: ${toneWord} 말투. 한국어. 각 자막은 18자 이내, 줄바꿈이 필요하면 \\n 으로 표시(최대 2줄).
지켜야 할 법: 의료광고(의료법 제56조). 효과·완치 보장, 전후 비교, "최고·유일·1등" 같은 최상급, 환자 후기 인용, 가격 할인 유도 문구는 쓰지 않는다. 사진 속 사람의 외모를 평가하지 않는다.
사진에서 가장 눈길이 가는 주인공(사람 얼굴·손·장비·간판 등)의 위치를 사진 전체 기준 0~1 좌표(x=왼쪽0·오른쪽1, y=위0·아래1)로 찍는다.
움직임은 다음 중 하나로 고른다: ${PRESETS.join(', ')} (kenburns=살짝 이동하며 확대, zoomin=확대, zoomout=멀어지기, panlr/panrl=가로 훑기, panud=세로 훑기, breathe=숨쉬듯 반복, sway=살랑 기울기, handheld=손떨림).
반드시 아래 JSON 하나만 출력한다(설명·코드 울타리 없이):
{"captions":["...","...","..."],"preset":"kenburns","focus":{"x":0.5,"y":0.4},"reason":"한 문장"}`;
}

function parseResult(text) {
  const m = String(text || '').match(/\{[\s\S]*\}/);
  if (!m) throw new Error('AI 답에서 JSON 을 찾지 못했습니다');
  const j = JSON.parse(m[0]);
  const clamp = (v) => Math.max(0, Math.min(1, v));
  const captions = (Array.isArray(j.captions) ? j.captions : []).map(s => String(s).replace(/\\n/g, '\n').trim()).filter(Boolean).slice(0, 3);
  const fx = Number(j.focus && j.focus.x), fy = Number(j.focus && j.focus.y);
  return {
    captions,
    preset: PRESETS.includes(j.preset) ? j.preset : 'kenburns',
    focus: { x: Number.isFinite(fx) ? clamp(fx) : 0.5, y: Number.isFinite(fy) ? clamp(fy) : 0.5 },
    reason: String(j.reason || '').slice(0, 200),
  };
}

async function askAnthropic(b64, mediaType, prompt) {
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': anthropicKey(), 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({
      model: process.env.ANTHROPIC_MODEL || 'claude-opus-5',
      max_tokens: 600,
      output_config: { effort: 'low' },
      messages: [{ role: 'user', content: [
        { type: 'image', source: { type: 'base64', media_type: mediaType, data: b64 } },
        { type: 'text', text: prompt },
      ] }],
    }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j.error && j.error.message) || ('Anthropic HTTP ' + r.status));
  if (j.stop_reason === 'refusal') throw new Error('AI가 이 사진에는 답하지 않았습니다');
  return (j.content || []).filter(b => b.type === 'text').map(b => b.text).join('');
}

async function askOpenAI(dataUrl, prompt) {
  const r = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + openaiKey() },
    body: JSON.stringify({
      model: process.env.OPENAI_VISION_MODEL || process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini',
      max_tokens: 400,
      messages: [{ role: 'user', content: [
        { type: 'image_url', image_url: { url: dataUrl, detail: 'low' } },
        { type: 'text', text: prompt },
      ] }],
    }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j.error && j.error.message) || ('OpenAI HTTP ' + r.status));
  return (j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content) || '';
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const prov = provider();
  if (req.method === 'GET') return res.status(200).json({ service: '사진 → 움직이는 GIF/WebP AI 도우미', llm: !!prov, provider: prov, presets: PRESETS });
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
  if (!prov) return res.status(503).json({ error: 'AI 키(ANTHROPIC_API_KEY 또는 OPENAI_API_KEY)가 서버에 없습니다. 화면의 「AI 연결 설정」에 본인 키를 넣어 쓰세요.' });

  const ip = String(req.headers['x-forwarded-for'] || req.socket?.remoteAddress || 'unknown').split(',')[0].trim();
  if (rateLimited(ip)) return res.status(429).json({ error: '너무 자주 눌렀습니다. 잠시 뒤 다시 시도해 주세요.' });

  try {
    const body = await readBody(req);
    const image = String(body.image || '');
    const m = image.match(/^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/);
    if (!m) return res.status(400).json({ error: 'image 는 data:image/jpeg;base64,... 형식이어야 합니다.' });
    if (m[2].length * 0.75 > MAX_IMAGE_BYTES) return res.status(413).json({ error: '사진이 너무 큽니다(1.5MB 이하).' });
    const purpose = String(body.purpose || '').slice(0, 200);
    const tone = ['calm', 'bright', 'short'].includes(body.tone) ? body.tone : 'calm';
    const prompt = buildPrompt(purpose, tone);
    const text = prov === 'anthropic' ? await askAnthropic(m[2], m[1], prompt) : await askOpenAI(image, prompt);
    const out = parseResult(text);
    return res.status(200).json({ ...out, provider: prov });
  } catch (e) {
    console.error('photo-motion-ai error:', e.message);
    return res.status(500).json({ error: e.message });
  }
};

module.exports._internal = { buildPrompt, parseResult, PRESETS };
