import https from 'https';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const { url } = req.query;
  if (!url) { res.status(400).json({ error: 'url parameter required' }); return; }

  const key = process.env.PSI_KEY;
  if (!key) { res.status(500).json({ error: 'PSI_KEY not configured' }); return; }

  const apiPath = `/pagespeedonline/v5/runPagespeed?url=${encodeURIComponent(url)}&key=${key}&strategy=mobile&category=seo&category=performance&category=best-practices&category=accessibility`;

  try {
    const data = await new Promise((resolve, reject) => {
      https.get(`https://www.googleapis.com${apiPath}`, (r) => {
        let body = '';
        r.on('data', chunk => body += chunk);
        r.on('end', () => {
          try { resolve({ status: r.statusCode, data: JSON.parse(body) }); }
          catch(e) { reject(new Error('JSON parse error: ' + body.slice(0, 200))); }
        });
      }).on('error', reject);
    });
    res.status(data.status).json(data.data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
