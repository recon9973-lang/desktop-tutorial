'use strict';

/**
 * 베노미(Venomi) — 병원명 한 줄 진단 API (P0 코어 엔진)
 *
 *  GET  /api/hospital-bot            → 상태(연동 키 설정 여부, 재사용 자산)
 *  POST /api/hospital-bot  { hospital, region? }
 *                                    → 6대 진단서 JSON  { summary, seo, geo, local, ads, adLaw }
 *
 *  · 카카오 오픈빌더 스킬 연동/직원 화이트리스트는 P0 다음 단계(#2)에서 이 위에 얹는다.
 *  · 코어 로직은 hospital-bot/lib/diagnose.js — API 없이도 로컬 검증 가능.
 */

const path = require('path');
const { diagnose } = require(path.join(__dirname, '..', 'hospital-bot', 'lib', 'diagnose'));

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

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  if (req.method === 'GET') {
    res.status(200).json({
      service: 'venomi-hospital-bot',
      phase: 'P0 (core engine)',
      config: {
        naverOpenapi: !!(process.env.NAVER_CLIENT_ID && process.env.NAVER_CLIENT_SECRET),
        naverSearchAd: !!(process.env.NAVER_AD_API_KEY || process.env.NAVER_ACCESS_LICENSE),
        psi: !!process.env.PSI_KEY,
      },
      reused: ['naver-searchad', 'psi', 'medical-ad-validator', 'naver-openapi', 'geo-probe(stub)'],
      note: 'POST { hospital, region? } 로 진단서를 받습니다.',
    });
    return;
  }

  if (req.method !== 'POST') { res.status(405).json({ error: 'Method Not Allowed' }); return; }

  try {
    const body = await readBody(req);
    const hospital = (body.hospital || body.query || body.message || '').toString().trim();
    if (!hospital) { res.status(400).json({ error: '병원명(hospital)이 필요합니다.' }); return; }

    const report = await diagnose(hospital, { region: (body.region || '').toString().trim(), now: Date.now() });
    res.status(200).json(report);
  } catch (e) {
    res.status(500).json({ error: '진단 처리 오류', detail: e.message });
  }
};
