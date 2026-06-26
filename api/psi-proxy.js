const https = require('https');

module.exports = function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const url = req.query.url;
  if (!url) { res.status(400).json({ error: 'url parameter required' }); return; }

  const key = process.env.PSI_KEY;
  if (!key) { res.status(500).json({ error: 'PSI_KEY not configured' }); return; }

  const apiPath = '/pagespeedonline/v5/runPagespeed?url=' + encodeURIComponent(url)
    + '&key=' + key
    + '&strategy=mobile&category=seo&category=performance&category=best-practices&category=accessibility';

  https.get('https://www.googleapis.com' + apiPath, function(r) {
    var body = '';
    r.on('data', function(chunk) { body += chunk; });
    r.on('end', function() {
      try {
        var data = JSON.parse(body);
        res.status(r.statusCode).json(data);
      } catch(e) {
        res.status(500).json({ error: 'Parse error', raw: body.slice(0, 300) });
      }
    });
  }).on('error', function(e) {
    res.status(500).json({ error: e.message });
  });
};
