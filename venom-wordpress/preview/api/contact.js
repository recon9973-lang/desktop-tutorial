module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: 'Method not allowed' }); return; }

  var APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbzZYLKxO6hMOvy0UBQf-rj1mBukpY3d0BETght9KdXn1cbpCvxNAO39_4mBwaQ4wIEzgA/exec';

  try {
    // Vercel auto-parses JSON body; fallback to raw read
    var body = req.body;
    if (!body || typeof body !== 'object' || Array.isArray(body)) {
      var _chunks = [];
      await new Promise(function(resolve, reject) {
        req.on('data', function(c) { _chunks.push(c); });
        req.on('end', resolve);
        req.on('error', reject);
      });
      try { body = JSON.parse(Buffer.concat(_chunks).toString('utf8')); } catch(e) { body = {}; }
    }

    // 무료 AI 노출 진단 신청 → Airtable 접수 베이스 (기존 상담신청과 분기)
    if (body && body.formType === 'diagnose') {
      return await submitDiagnosis(body, req, res);
    }

    if (!body || !body.hospital) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Build GET query string
    var qs = Object.keys(body)
      .map(function(k) { return encodeURIComponent(k) + '=' + encodeURIComponent(body[k] || ''); })
      .join('&');
    var url = APPS_SCRIPT_URL + '?' + qs;

    // fetch() is available in Node 18+ (Vercel runtime)
    // follow redirects automatically (default)
    var response = await fetch(url, {
      method: 'GET',
      headers: { 'User-Agent': 'Mozilla/5.0' },
      redirect: 'follow',
      signal: AbortSignal.timeout(30000)
    });

    var text = await response.text();
    var data;
    try { data = JSON.parse(text); } catch(e) { data = { result: 'ok' }; }

    // 상담신청 1건을 KV 카운터에 집계(대시보드 실데이터) — 응답 지연 없이 fire-and-forget
    try {
      var _host = (req.headers && req.headers.host) || 'venom-new-site.vercel.app';
      fetch('https://' + _host + '/api/analytics', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lead: 1 }),
      }).catch(function(){});
    } catch (e) {}

    return res.status(200).json({ result: 'ok', raw: data });
  } catch (e) {
    console.error('contact handler error:', e.message);
    return res.status(500).json({ error: e.message });
  }
};

// ── 무료 AI 노출 진단 신청 → Airtable "신청접수" 테이블 기록 ──
// 베이스/테이블: 베놈 무료진단 접수(appR2NeAuARbojdPs · 신청접수). env로 재정의 가능.
// 개인정보보호법 대응: 필수동의 검증 + 동의증적(버전·일시·IP) 저장.
async function submitDiagnosis(body, req, res) {
  var name = (body.name || '').trim();
  var phone = (body.phone || '').trim();
  if (!name || !phone) return res.status(400).json({ error: '성명과 휴대전화는 필수입니다.' });
  if (!body.agreeRequired) return res.status(400).json({ error: '개인정보 수집·이용 필수 동의가 필요합니다.' });

  var token = (process.env.AIRTABLE_TOKEN || process.env.AIRTABLE_API_KEY || '').trim();
  var base = (process.env.AIRTABLE_LEAD_BASE || 'appR2NeAuARbojdPs').trim();
  var table = (process.env.AIRTABLE_LEAD_TABLE || 'tblSE4a5JrqggAiVR').trim();
  if (!token) return res.status(501).json({ error: '접수 저장소(AIRTABLE_TOKEN) 미설정' });

  var ip = ((req.headers && req.headers['x-forwarded-for']) || '').split(',')[0].trim()
    || (req.socket && req.socket.remoteAddress) || '';

  var fields = {
    '병원명': body.hospital || '',
    '병원주소': body.address || '',
    '진료과목': body.dept || '',
    '신청자성명': name,
    '직책': body.title || '',
    '휴대전화': phone,
    '이메일': body.email || '',
    '희망키워드': body.keywords || '',
    '문의사항': body.message || '',
    '동의_필수(수집이용+제공조건)': !!body.agreeRequired,
    '동의_상담안내(선택)': !!body.agreeConsult,
    '동의_광고_문자': !!body.agreeSmsAd,
    '동의_광고_이메일': !!body.agreeEmailAd,
    '동의_광고_전화': !!body.agreeCallAd,
    '동의문구버전': body.consentVersion || '',
    '동의일시': new Date().toISOString(),
    'IP': ip,
  };
  // singleSelect(수령방식·상담희망)은 값이 있을 때만 — 폼 옵션명은 베이스 옵션과 일치시켜 운영
  if (body.delivery) fields['수령방식'] = body.delivery;
  if (body.wantConsult) fields['상담희망'] = body.wantConsult;

  try {
    var r = await fetch('https://api.airtable.com/v0/' + base + '/' + encodeURIComponent(table), {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ records: [{ fields: fields }], typecast: true }),
      signal: AbortSignal.timeout(15000),
    });
    var data = await r.json().catch(function () { return {}; });
    if (!r.ok) {
      console.error('airtable lead error:', r.status, JSON.stringify(data).slice(0, 300));
      return res.status(502).json({ error: '접수 저장 실패', status: r.status });
    }
    // 리드 1건 집계 (대시보드 실데이터) — fire-and-forget
    try {
      var _host = (req.headers && req.headers.host) || 'venom-new-site.vercel.app';
      fetch('https://' + _host + '/api/analytics', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lead: 1 }),
      }).catch(function () {});
    } catch (e) {}
    var id = (data.records && data.records[0] && data.records[0].id) || null;
    return res.status(200).json({ result: 'ok', id: id });
  } catch (e) {
    console.error('submitDiagnosis error:', e.message);
    return res.status(500).json({ error: e.message });
  }
}
