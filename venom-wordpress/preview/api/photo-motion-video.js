'use strict';

/**
 * 사진 한 장 → AI 로 「말하는 영상」 (tools/photo-motion.html 의 「AI 영상 만들기」 단추)
 *
 *  GET  /api/photo-motion-video                → { configured, provider }          서버에 키가 있는지
 *  POST /api/photo-motion-video  { image, script, duration }  → { id, provider }   영상 만들기 시작
 *  GET  /api/photo-motion-video?id=…&provider=… → { status: 'queued'|'running'|'done'|'failed', video_url?, error? }
 *  GET  /api/photo-motion-video?proxy=<video_url> → 영상 파일을 그대로 흘려보냄(브라우저가 CORS 로 못 받을 때)
 *
 * 키(둘 중 하나, Vercel 환경변수):
 *   HIGGSFIELD_API_KEY = "키ID:키비밀"  (cloud.higgsfield.ai 에서 발급 · 사용량 과금)  ← 우선
 *   MINIMAX_API_KEY    = "…"            (platform.minimax.io 에서 발급 · 사용량 과금)
 * 선택: HIGGSFIELD_VIDEO_PATH (기본 /minimax/hailuo-2.3/standard/image-to-video), MINIMAX_VIDEO_MODEL (기본 MiniMax-Hailuo-2.3)
 *
 * 카메라 고정 · 인터뷰하듯 말하는 장면. 소리는 쓰지 않는다(자막으로 처리). 저장소 관례대로 SDK 없이 fetch.
 */

const HF_BASE = 'https://api.higgsfield.ai';
const MM_BASE = 'https://api.minimax.io';
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;
const PROXY_HOSTS = /(\.cloudfront\.net|\.higgsfield\.ai|higgsfield-ai\.com|\.minimax\.io|\.minimaxi\.com|minimax\.chat)$/i;
const RATE = { windowMs: 60 * 60 * 1000, max: 12 };
const hits = new Map();

function hfKey() { return (process.env.HIGGSFIELD_API_KEY || '').trim(); }
function mmKey() { return (process.env.MINIMAX_API_KEY || '').trim(); }
function provider() { return hfKey() ? 'higgsfield' : mmKey() ? 'minimax' : null; }

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

function buildPrompt(script) {
  const line = String(script || '').replace(/\s+/g, ' ').trim();
  return 'Static locked-off camera, no camera movement, no zoom. Interview style: the same person from the photo, face and appearance unchanged, ' +
    'answering an interviewer\'s question. They talk naturally in Korean with clear lip movement, natural blinks, small nods and gentle head gestures, warm calm expression. ' +
    (line ? `They say in Korean: "${line.slice(0, 300)}". ` : '') +
    'Same background as in the photo. No subtitles, no text, no logos.';
}

// ---------- Higgsfield (api.higgsfield.ai) ----------
async function hfSubmit(image, prompt, duration) {
  const path = process.env.HIGGSFIELD_VIDEO_PATH || '/minimax/hailuo-2.3/standard/image-to-video';
  const r = await fetch(HF_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Key ' + hfKey() },
    body: JSON.stringify({ prompt, image_url: image, duration }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`Higgsfield ${r.status}: ${JSON.stringify(j).slice(0, 300)}`);
  const id = j.request_id || j.id;
  if (!id) throw new Error('Higgsfield 응답에 request_id 가 없습니다: ' + JSON.stringify(j).slice(0, 200));
  return { id: String(id), status_url: j.status_url || '' };
}
async function hfStatus(id, statusUrl) {
  const url = statusUrl && statusUrl.startsWith(HF_BASE) ? statusUrl : `${HF_BASE}/requests/${encodeURIComponent(id)}/status`;
  const r = await fetch(url, { headers: { Authorization: 'Key ' + hfKey() } });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`Higgsfield ${r.status}: ${JSON.stringify(j).slice(0, 300)}`);
  const s = String(j.status || '').toLowerCase();
  const videoUrl = (j.video && j.video.url) || (j.result && j.result.video && j.result.video.url) || (j.videos && j.videos[0] && j.videos[0].url) || '';
  if (s === 'completed' || s === 'succeeded' || videoUrl) return { status: 'done', video_url: videoUrl };
  if (s === 'failed' || s === 'nsfw' || s === 'cancelled' || s === 'error') return { status: 'failed', error: j.error || j.message || s };
  return { status: s === 'queued' ? 'queued' : 'running' };
}

// ---------- MiniMax (api.minimax.io) ----------
async function mmSubmit(image, prompt, duration) {
  const r = await fetch(MM_BASE + '/v1/video_generation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + mmKey() },
    body: JSON.stringify({ model: process.env.MINIMAX_VIDEO_MODEL || 'MiniMax-Hailuo-2.3', prompt, first_frame_image: image, duration, resolution: '768P' }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || (j.base_resp && j.base_resp.status_code)) throw new Error(`MiniMax ${r.status}: ${JSON.stringify(j.base_resp || j).slice(0, 300)}`);
  if (!j.task_id) throw new Error('MiniMax 응답에 task_id 가 없습니다');
  return { id: String(j.task_id) };
}
async function mmStatus(id) {
  const r = await fetch(`${MM_BASE}/v1/query/video_generation?task_id=${encodeURIComponent(id)}`, { headers: { Authorization: 'Bearer ' + mmKey() } });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`MiniMax ${r.status}`);
  const s = String(j.status || '');
  if (s === 'Success' && j.file_id) {
    const f = await fetch(`${MM_BASE}/v1/files/retrieve?file_id=${encodeURIComponent(j.file_id)}`, { headers: { Authorization: 'Bearer ' + mmKey() } });
    const fj = await f.json().catch(() => ({}));
    const url = fj.file && fj.file.download_url;
    if (!url) throw new Error('MiniMax 파일 주소를 못 받았습니다');
    return { status: 'done', video_url: url };
  }
  if (s === 'Fail') return { status: 'failed', error: (j.base_resp && j.base_resp.status_msg) || 'MiniMax 실패' };
  return { status: s === 'Queueing' || s === 'Preparing' ? 'queued' : 'running' };
}

async function proxyVideo(url, res) {
  let u; try { u = new URL(url); } catch (e) { return res.status(400).json({ error: '주소가 이상합니다' }); }
  if (u.protocol !== 'https:' || !PROXY_HOSTS.test(u.hostname)) return res.status(400).json({ error: '허용되지 않은 주소입니다' });
  const r = await fetch(u.toString());
  if (!r.ok || !r.body) return res.status(502).json({ error: '영상을 받아오지 못했습니다 (' + r.status + ')' });
  res.status(200);
  res.setHeader('Content-Type', r.headers.get('content-type') || 'video/mp4');
  const len = r.headers.get('content-length'); if (len) res.setHeader('Content-Length', len);
  res.setHeader('Cache-Control', 'private, max-age=3600');
  const reader = r.body.getReader();
  for (;;) { const { done, value } = await reader.read(); if (done) break; res.write(Buffer.from(value)); }
  res.end();
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }
  const prov = provider();
  const q = req.query || {};

  try {
    if (req.method === 'GET') {
      if (q.proxy) return await proxyVideo(String(q.proxy), res);
      if (!q.id) return res.status(200).json({ service: '사진 → AI 말하는 영상', configured: !!prov, provider: prov, durations: [6, 10] });
      if (!prov) return res.status(503).json({ error: '서버에 영상 AI 키가 없습니다' });
      const p = String(q.provider || prov);
      const st = p === 'minimax' ? await mmStatus(String(q.id)) : await hfStatus(String(q.id), String(q.status_url || ''));
      return res.status(200).json(st);
    }
    if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
    if (!prov) return res.status(503).json({ error: '서버에 영상 AI 키가 없습니다. Vercel 환경변수 HIGGSFIELD_API_KEY(키ID:비밀) 또는 MINIMAX_API_KEY 를 넣어 주세요.' });

    const ip = String(req.headers['x-forwarded-for'] || (req.socket && req.socket.remoteAddress) || 'unknown').split(',')[0].trim();
    if (rateLimited(ip)) return res.status(429).json({ error: '한 시간에 12번까지만 만들 수 있습니다. 잠시 뒤 다시 해 주세요.' });

    const body = await readBody(req);
    const image = String(body.image || '');
    const m = image.match(/^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/);
    if (!m) return res.status(400).json({ error: 'image 는 data:image/jpeg;base64,... 형식이어야 합니다.' });
    if (m[2].length * 0.75 > MAX_IMAGE_BYTES) return res.status(413).json({ error: '사진이 너무 큽니다(3MB 이하).' });
    const duration = Number(body.duration) === 10 ? 10 : 6;
    const prompt = buildPrompt(body.script);
    const sub = prov === 'minimax' ? await mmSubmit(image, prompt, duration) : await hfSubmit(image, prompt, duration);
    return res.status(200).json({ id: sub.id, provider: prov, status_url: sub.status_url || '', duration });
  } catch (e) {
    console.error('photo-motion-video error:', e.message);
    return res.status(500).json({ error: e.message });
  }
};

module.exports._internal = { buildPrompt, provider, PROXY_HOSTS };
