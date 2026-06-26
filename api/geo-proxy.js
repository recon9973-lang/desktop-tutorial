const https = require('https');

module.exports = function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const query = req.query.query;
  if (!query) { res.status(400).json({ error: 'query parameter required' }); return; }

  const key = process.env.PSI_KEY;
  if (!key) { res.status(500).json({ error: 'PSI_KEY not configured' }); return; }

  const apiPath = '/v1/entities:search?query=' + encodeURIComponent(query)
    + '&key=' + key + '&limit=5&languages=ko&languages=en';

  https.get('https://kgsearch.googleapis.com' + apiPath, function(r) {
    var body = '';
    r.on('data', function(chunk) { body += chunk; });
    r.on('end', function() {
      try {
        var data = JSON.parse(body);
        res.status(r.statusCode).json(data);
      } catch(e) {
        res.status(500).json({ error: 'Parse error' });
      }
    });
  }).on('error', function(e) {
    res.status(500).json({ error: e.message });
  });
};
