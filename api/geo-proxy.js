import https from 'https';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const { query } = req.query;
  if (!query) { res.status(400).json({ error: 'query parameter required' }); return; }

  const key = process.env.PSI_KEY;
  if (!key) { res.status(500).json({ error: 'PSI_KEY not configured' }); return; }

  const apiPath = `/v1/entities:search?query=${encodeURIComponent(query)}&key=${key}&limit=5&languages=ko&languages=en`;

  try {
    const data = await new Promise((resolve, reject) => {
      https.get(`https://kgsearch.googleapis.com${apiPath}`, (r) => {
        let body = '';
        r.on('data', chunk => body += chunk);
        r.on('end', () => {
          try { resolve({ status: r.statusCode, data: JSON.parse(body) }); }
          catch(e) { reject(new Error('JSON parse error')); }
        });
      }).on('error', reject);
    });
    res.status(data.status).json(data.data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
