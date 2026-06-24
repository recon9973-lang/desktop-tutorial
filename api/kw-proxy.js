import crypto from 'crypto';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const { keyword } = req.query;
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
  hmac.update(`${timestamp}.${accessLicense}`);
  const signature = hmac.digest('base64');

  // 연관 키워드 5개 생성
  const hints = [keyword, `${keyword} 비용`, `${keyword} 후기`, `${keyword} 잘하는곳`, `${keyword} 추천`];
  const apiUrl = `https://api.searchad.naver.com/keywordstool?hintKeywords=${hints.map(encodeURIComponent).join(',')}&showDetail=1`;

  try {
    const r = await fetch(apiUrl, {
      headers: {
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Timestamp': timestamp,
        'X-API-KEY': accessLicense,
        'X-Customer': customerId,
        'X-Signature': signature,
      }
    });
    const data = await r.json();
    res.status(r.status).json(data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
