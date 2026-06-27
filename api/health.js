'use strict';

module.exports = function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.status(200).json({
    ok: true,
    hasOpenAI: !!process.env.OPENAI_API_KEY,
    hasGitHub: !!process.env.GITHUB_TOKEN,
    hasAdminSecret: !!process.env.ADMIN_SECRET,
    time: new Date().toISOString(),
  });
};
