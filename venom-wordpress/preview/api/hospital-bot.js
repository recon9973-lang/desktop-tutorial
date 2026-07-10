'use strict';

/**
 * 베노미(Venomi) — 병원명 한 줄 진단 API + 카카오 오픈빌더 스킬 서버
 *
 *  GET  /api/hospital-bot            → 상태(연동 키·화이트리스트 모드)
 *  POST /api/hospital-bot
 *    ① 순수 API:   { hospital, region? }            → 진단서 JSON(내부·테스트)
 *    ② 카카오 스킬: { userRequest, action, bot, ... } → SkillResponse v2.0
 *
 *  카카오 흐름:
 *    · 직원 화이트리스트(userRequest.user.id) 대조 — 미허용 시 정중 거절.
 *    · 발화 파싱 → 병원명 + 뷰(seo/geo/광고/플레이스/심의/상담).
 *    · 5초 타임아웃 대응: callbackUrl 있으면 즉시 ack(useCallback) 후
 *      진단 완료 시 callbackUrl로 최종 SkillResponse를 POST.
 *
 *  코어 로직: hospital-bot/lib/diagnose.js (API 없이도 로컬 검증 가능)
 */

const path = require('path');
const https = require('https');
const CB = path.join(__dirname, '..', 'hospital-bot', 'lib');
const { diagnose } = require(path.join(CB, 'diagnose'));
const kf = require(path.join(CB, 'kakao-format'));
const whitelist = require(path.join(CB, 'whitelist'));

async function readBody(req) {
  let body = req.body;
  if (body && typeof body === 'object' && !Array.isArray(body)) return body;
  const chunks = [];
  await new Promise((resolve, reject) => {
    req.on('data', (c) => chunks.push(c));
    req.on('end', resolve);
    req.on('error', reject);
  });
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) { return {}; }
}

// 카카오 콜백 URL로 최종 SkillResponse POST
function postCallback(url, payload) {
  return new Promise((resolve) => {
    let u;
    try { u = new URL(url); } catch (e) { return resolve({ ok: false, error: 'bad callbackUrl' }); }
    const data = Buffer.from(JSON.stringify(payload), 'utf8');
    const req = https.request(
      { hostname: u.hostname, path: u.pathname + u.search, method: 'POST', port: u.port || 443,
        headers: { 'Content-Type': 'application/json', 'Content-Length': data.length } },
      (res) => { res.on('data', () => {}); res.on('end', () => resolve({ ok: res.statusCode < 300, status: res.statusCode })); }
    );
    req.on('error', (e) => resolve({ ok: false, error: e.message }));
    req.setTimeout(8000, () => { req.destroy(); resolve({ ok: false, error: 'callback timeout' }); });
    req.write(data); req.end();
  });
}

function isKakaoSkill(body) {
  return !!(body && body.userRequest && body.action);
}

// 카카오 스킬 요청 처리
async function handleKakao(res, body) {
  const user = (body.userRequest && body.userRequest.user) || {};
  const gate = whitelist.check(user.id);
  if (!gate.allowed) { res.status(200).json(kf.renderRefusal()); return; }

  const utter = (body.userRequest && body.userRequest.utterance) || '';
  const cmd = kf.parseCommand(utter);

  if (cmd.view === 'contact') { res.status(200).json(kf.renderContact()); return; }
  if (!cmd.hospital) { res.status(200).json(kf.renderAsk()); return; }

  const callbackUrl = body.userRequest && body.userRequest.callbackUrl;

  // 'geo' 뷰만 실 프로빙(느림·유료). 나머지는 light.
  const diagOpts = { region: '', now: Date.now(), geoMode: cmd.view === 'geo' ? 'full' : 'light' };

  if (callbackUrl) {
    // 5초 내 ack → 진단 완료 시 콜백으로 최종 응답(서버리스는 반환 promise까지 살아있음)
    res.status(200).json({ version: '2.0', useCallback: true, data: kf.ackData(cmd.hospital) });
    try {
      const report = await diagnose(cmd.hospital, diagOpts);
      await postCallback(callbackUrl, kf.render(report, cmd.view));
    } catch (e) {
      await postCallback(callbackUrl, kf.renderError(e.message)).catch(() => {});
    }
    return;
  }

  // 콜백 미설정 → 동기 응답(캐시·빠른 경로 가정, 5초 초과 시 오픈빌더가 타임아웃)
  try {
    const report = await diagnose(cmd.hospital, diagOpts);
    res.status(200).json(kf.render(report, cmd.view));
  } catch (e) {
    res.status(200).json(kf.renderError(e.message));
  }
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  if (req.method === 'GET') {
    res.status(200).json({
      service: 'venomi-hospital-bot',
      phase: 'P0 + 카카오 연동(#2)',
      config: {
        naverOpenapi: !!(process.env.NAVER_CLIENT_ID && process.env.NAVER_CLIENT_SECRET),
        naverSearchAd: !!(process.env.NAVER_AD_API_KEY || process.env.NAVER_ACCESS_LICENSE),
        psi: !!process.env.PSI_KEY,
        whitelistMode: whitelist.isConfigured() ? 'enforced' : 'open',
      },
      reused: ['naver-searchad', 'psi', 'medical-ad-validator', 'naver-openapi', 'geo-probe(stub)'],
      note: '순수 API: POST { hospital, region? } · 카카오 스킬: userRequest/action 페이로드',
    });
    return;
  }

  if (req.method !== 'POST') { res.status(405).json({ error: 'Method Not Allowed' }); return; }

  try {
    const body = await readBody(req);

    if (isKakaoSkill(body)) { await handleKakao(res, body); return; }

    // 순수 API(내부·테스트)
    const hospital = (body.hospital || body.query || body.message || '').toString().trim();
    if (!hospital) { res.status(400).json({ error: '병원명(hospital)이 필요합니다.' }); return; }
    const report = await diagnose(hospital, { region: (body.region || '').toString().trim(), now: Date.now() });
    res.status(200).json(report);
  } catch (e) {
    res.status(500).json({ error: '진단 처리 오류', detail: e.message });
  }
};

// 테스트 노출
module.exports._internal = { isKakaoSkill, postCallback };
