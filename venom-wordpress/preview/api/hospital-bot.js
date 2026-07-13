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
const D = require(path.join(CB, 'diagnose'));
const { diagnose } = D;
const kf = require(path.join(CB, 'kakao-format'));
const whitelist = require(path.join(CB, 'whitelist'));

function getQuery(req) {
  if (req.query && typeof req.query === 'object') return req.query;
  try {
    const u = new URL(req.url, 'http://localhost');
    const o = {}; u.searchParams.forEach((v, k) => { o[k] = v; });
    return o;
  } catch (e) { return {}; }
}

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
  const utter = (body.userRequest && body.userRequest.utterance) || '';
  const cmd = kf.parseCommand(utter);

  // 온보딩/도움말: 화이트리스트와 무관하게 허용(등록 전이라도 확인 가능)
  if (cmd.view === 'myid') { res.status(200).json(kf.renderMyId(user.id)); return; }
  if (cmd.view === 'help') { res.status(200).json(kf.renderHelp()); return; }

  const gate = whitelist.check(user.id);
  if (!gate.allowed) { res.status(200).json(kf.renderRefusal(user.id)); return; }

  if (cmd.view === 'contact') { res.status(200).json(kf.renderContact()); return; }
  if (!cmd.hospital) { res.status(200).json(kf.renderAsk()); return; }

  // 항상 지역+병원명 — 지역(구·동)이 없으면 되물어 정확도를 높인다.
  const parsed = D.parseInput(cmd.hospital);
  if (!parsed.region) { res.status(200).json(kf.renderAskRegion()); return; }

  // 업체 확인(하나씩 확인 진입점) — 종합 진단 없이 네이버 탐지만(빠름) + 항목 버튼.
  if (cmd.view === 'confirm') {
    try {
      const info = await Promise.race([
        D.resolvePlace(cmd.hospital, { now: Date.now() }),
        new Promise((resolve) => setTimeout(() => resolve(null), 3500)),
      ]);
      if (!info) { res.status(200).json(kf.renderSlow(parsed.name)); return; }
      res.status(200).json(kf.renderConfirm(info));
    } catch (e) { res.status(200).json(kf.renderError(e.message)); }
    return;
  }

  const callbackUrl = body.userRequest && body.userRequest.callbackUrl;

  // 'geo' 뷰만 실 프로빙(느림·유료), 'compete' 뷰만 경쟁 비교(로컬 다중호출). 나머지는 light.
  const diagOpts = { region: '', now: Date.now(),
    geoMode: cmd.view === 'geo' ? 'full' : 'light',
    compete: cmd.view === 'compete' || cmd.view === 'proposal',
    proposal: cmd.view === 'proposal' };

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

  // 콜백 미설정 → 동기 응답. 카톡 5초 타임아웃 방지: 4.5초 내 미완료면
  // '무응답' 대신 재시도 안내를 보낸다(콜드스타트·느린 홈페이지 대비).
  try {
    const report = await Promise.race([
      diagnose(cmd.hospital, diagOpts),
      new Promise((resolve) => setTimeout(() => resolve(null), 4000)),
    ]);
    if (!report) { res.status(200).json(kf.renderSlow(cmd.hospital)); return; }
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
    // 웹 리포트용 라이브 진단: /api/hospital-bot?hospital=..&geo=1
    const q = getQuery(req);
    const hospital = (q.hospital || q.q || '').toString().trim();
    if (hospital) {
      try {
        const report = await diagnose(hospital, {
          region: (q.region || '').toString().trim(),
          now: Date.now(),
          geoMode: String(q.geo || '') === '1' ? 'full' : 'light',
          compete: String(q.compete || '') === '1' || String(q.proposal || '') === '1',
          proposal: String(q.proposal || '') === '1',
          cache: String(q.cache || '') !== '0', // ?cache=0 → 강제 갱신
        });
        res.status(200).json(report);
      } catch (e) {
        res.status(500).json({ error: '진단 처리 오류', detail: e.message });
      }
      return;
    }
    res.status(200).json({
      service: 'venomi-hospital-bot',
      phase: '운영(내부) · 전업종 진단(의료광고법 조건부)',
      build: 'v7-2026-07-14',
      features: ['confirm-first(업체확인 우선)', '항목별 진단(하나씩)', 'region-required(지역필수)', 'seo-url(주소입력)', 'onpage-seo(seo-engine)', 'trust-confidence(오탐방지)', 'gsc-live(관리고객 실측)', 'myid(내키)', 'help(도움말)', 'law-locate(심의위치)'],
      config: {
        naverOpenapi: !!(process.env.NAVER_CLIENT_ID && process.env.NAVER_CLIENT_SECRET),
        naverSearchAd: !!(process.env.NAVER_AD_API_KEY || process.env.NAVER_ACCESS_LICENSE),
        psi: !!process.env.PSI_KEY,
        gsc: !!(process.env.GSC_SERVICE_ACCOUNT_JSON || (process.env.GSC_CLIENT_EMAIL && process.env.GSC_PRIVATE_KEY)) && !!(process.env.GSC_SITE_URL || process.env.SITE_URL),
        onpageSeo: (function () { try { require(path.join(__dirname, '..', 'seo', 'seo-engine.js')); return true; } catch (e) { return false; } })(),
        whitelistMode: whitelist.isConfigured() ? 'enforced' : 'open',
        cache: require(path.join(__dirname, '..', 'lib', 'cache')).configured() ? '24h(KV)' : 'off',
      },
      reused: ['seo-engine(온페이지)', 'search-console(GSC)', 'naver-searchad', 'psi', 'medical-ad-validator', 'naver-openapi', 'geo-probe(stub)'],
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
module.exports._internal = { isKakaoSkill, postCallback, getQuery };
