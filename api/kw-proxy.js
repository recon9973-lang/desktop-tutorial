const https = require('https');
const crypto = require('crypto');

module.exports = function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const keyword = req.query.keyword;
  if (!keyword) { res.status(400).json({ error: 'keyword parameter required' }); return; }

  const customerId = process.env.NAVER_CUSTOMER_ID;
  const accessLicense = process.env.NAVER_ACCESS_LICENSE;
  const secretKey = process.env.NAVER_SECRET_KEY;

  if (!customerId || !accessLicense || !secretKey) {
    res.status(500).json({ error: 'Naver API credentials not configured' });
    return;
  }

  const timestamp = Date.now().toString();
  const hmac = crypto.createHmac('sha256', secretKey);
  hmac.update(timestamp + '.' + accessLicense);
  const signature = hmac.digest('base64');

  const hints = [keyword, keyword + ' 비용', keyword + ' 후기', keyword + ' 잘하는곳', keyword + ' 추천'];
  const hintParam = hints.map(encodeURIComponent).join(',');
  const apiPath = '/keywordstool?hintKeywords=' + hintParam + '&showDetail=1';

  const options = {
    hostname: 'api.searchad.naver.com',
    path: apiPath,
    method: 'GET',
    headers: {
      'Content-Type': 'application/json; charset=UTF-8',
      'X-Timestamp': timestamp,
      'X-API-KEY': accessLicense,
      'X-Customer': customerId,
      'X-Signature': signature
    }
  };

  https.get(options, function(r) {
    var body = '';
    r.on('data', function(chunk) { body += chunk; });
    r.on('end', function() {
      try {
        var data = JSON.parse(body);
        data._debug_status = r.statusCode;
        res.status(r.statusCode).json(data);
      } catch(e) {
        res.status(500).json({ error: 'Parse error', raw: body.slice(0, 500) });
      }
    });
  }).on('error', function(e) {
    res.status(500).json({ error: e.message });
  });
};
