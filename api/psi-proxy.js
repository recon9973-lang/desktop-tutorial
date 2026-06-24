export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const { url } = req.query;
  if (!url) { res.status(400).json({ error: 'url parameter required' }); return; }

  const key = process.env.PSI_KEY;
  if (!key) { res.status(500).json({ error: 'PSI_KEY not configured' }); return; }

  const apiUrl = `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=${encodeURIComponent(url)}&key=${key}&strategy=mobile&category=seo&category=performance&category=best-practices&category=accessibility`;

  try {
    const r = await fetch(apiUrl);
    const data = await r.json();
    res.status(r.status).json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
