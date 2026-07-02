'use strict';

const { generateImageB64 } = require('../lib/image-generator');

// 원고 스튜디오 "AI 이미지 생성" 툴 전용 엔드포인트.
// GitHub 저장 없이 base64를 바로 반환 → 화면에 즉시 표시·다운로드.
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
  if (!process.env.OPENAI_API_KEY) {
    return res.status(500).json({ error: 'OPENAI_API_KEY 환경변수가 설정되지 않았습니다.' });
  }

  const { prompt, style, aspect, extra } = req.body || {};
  if (!prompt) return res.status(400).json({ error: 'prompt 필수' });

  try {
    const r = await generateImageB64(prompt, { style, aspect, extra });
    if (!r.b64) return res.status(500).json({ error: r.error });
    // data URL로 바로 표시할 수 있게 반환
    return res.status(200).json({
      ok: true,
      model: r.model,
      mime: r.mime,
      dataUrl: `data:${r.mime};base64,${r.b64}`,
    });
  } catch (e) {
    console.error('[generate-image]', e);
    return res.status(500).json({ error: e.message });
  }
};
