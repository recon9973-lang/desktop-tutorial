'use strict';

const { validateMedicalAd } = require('../lib/medical-ad-validator');

module.exports = function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  const { text } = req.body || {};
  if (!text) return res.status(400).json({ error: 'text 필수' });

  const result = validateMedicalAd(text);
  return res.status(200).json(result);
};
