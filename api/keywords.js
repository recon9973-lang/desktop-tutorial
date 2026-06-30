'use strict';

const { researchKeywords } = require('../lib/keyword-research');

// 원고 스튜디오 "키워드 리서치(검색량)" 툴 전용 엔드포인트.
// 네이버/구글 자동완성 + 네이버 검색광고(월 검색량) 기반 연관키워드·질문 반환.
module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  const secret = process.env.ADMIN_SECRET;
  if (secret) {
    const auth = (req.headers['authorization'] || '').replace('Bearer ', '').trim();
    if (auth !== secret) return res.status(401).json({ error: 'ADMIN_SECRET 불일치.' });
  }

  const { keyword, region } = req.body || {};
  if (!keyword) return res.status(400).json({ error: 'keyword 필수' });

  try {
    const r = await researchKeywords(keyword, { region: region || '' });
    return res.status(200).json({
      ok: true,
      related: r.related || [],
      questions: r.questions || [],
      volumes: r.volumes || [],   // [{keyword, volume}] — 실제 월 검색량(검색광고 키 설정 시)
      sources: r.sources || {},   // {naver, google, searchad} 각 소스 결과 수
    });
  } catch (e) {
    console.error('[keywords]', e);
    return res.status(500).json({ error: e.message });
  }
};
