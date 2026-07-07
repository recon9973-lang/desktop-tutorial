// ============================================================
// naver-searchad — 네이버 검색광고 키워드도구(/keywordstool) 단일 소스
// ============================================================
// 동일한 HMAC 서명 + /keywordstool 호출이 api/insights.js·api/seo-proxy.js·
// lib/keyword-research.js 3벌로 중복돼 있던 것을 이 모듈로 통합한다.
// 이 모듈은 "인증 + 원시 호출"만 담당하고, 각 호출부는 자기 응답 형태로 가공한다.
// (비파괴: 공개 엔드포인트 응답 형태는 그대로 유지)
//
// 필요 env(신·구 변수명 모두 허용):
//   NAVER_AD_API_KEY | NAVER_ACCESS_LICENSE
//   NAVER_AD_SECRET  | NAVER_SECRET_KEY
//   NAVER_AD_CUSTOMER_ID | NAVER_CUSTOMER_ID
// ============================================================
const https = require('https');
const crypto = require('crypto');

// 검색광고 자격증명 — 저장소 통합 전 등록분 호환을 위해 신·구 변수명 모두 허용
function adCreds() {
  return {
    key: (process.env.NAVER_AD_API_KEY || process.env.NAVER_ACCESS_LICENSE || '').trim(),
    secret: (process.env.NAVER_AD_SECRET || process.env.NAVER_SECRET_KEY || '').trim(),
    customer: (process.env.NAVER_AD_CUSTOMER_ID || process.env.NAVER_CUSTOMER_ID || '').trim(),
  };
}

function isConfigured(c) {
  c = c || adCreds();
  return !!(c.key && c.secret && c.customer);
}

// 네이버 검색광고 공식 서명 규격: HMAC-SHA256("{timestamp}.{method}.{apiPath}", 비밀키)
function signHeaders(method, apiPath, c) {
  c = c || adCreds();
  const ts = String(Date.now());
  const sign = crypto.createHmac('sha256', c.secret).update(`${ts}.${method}.${apiPath}`).digest('base64');
  return {
    'Content-Type': 'application/json; charset=UTF-8',
    'X-Timestamp': ts,
    'X-API-KEY': c.key,
    'X-Customer': c.customer,
    'X-Signature': sign,
  };
}

// 네이버는 검색량이 적으면 "< 10" 문자열로 준다 → 5로 근사
function toNum(v) {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    if (/<\s*10/.test(v)) return 5;
    const n = parseInt(v.replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : n;
  }
  return 0;
}

// 원시 호출: hints(문자열 또는 배열, 공백 제거·최대 5개) → 표준 결과
// 반환: { status, configured, keywordList|null, json|null, raw, error|null }
function fetchKeywordTool(hints, opts) {
  const timeout = (opts && opts.timeout) || 8000;
  return new Promise((resolve) => {
    const c = adCreds();
    if (!isConfigured(c)) {
      return resolve({ status: 501, configured: false, keywordList: null, json: null, raw: '', error: '네이버 검색광고 API 미설정' });
    }
    // hintKeywords는 공백 불허(네이버 11001 오류) → 공백 제거, 최대 5개
    const clean = (Array.isArray(hints) ? hints : [hints])
      .map((k) => String(k).replace(/\s+/g, '')).filter(Boolean).slice(0, 5);
    const apiPath = '/keywordstool';
    const path = `${apiPath}?hintKeywords=${clean.map(encodeURIComponent).join(',')}&showDetail=1`;
    const req = https.get(
      { hostname: 'api.searchad.naver.com', path, method: 'GET', headers: signHeaders('GET', apiPath, c) },
      (res) => {
        const chunks = [];
        res.on('data', (d) => chunks.push(d));
        res.on('end', () => {
          const raw = Buffer.concat(chunks).toString('utf8');
          let json = null;
          try { json = JSON.parse(raw); } catch (e) { /* keep null */ }
          const keywordList = json && Array.isArray(json.keywordList) ? json.keywordList : null;
          const error = res.statusCode !== 200
            ? ((json && (json.title || json.message)) || ('네이버 검색광고 응답 오류 HTTP ' + res.statusCode))
            : (keywordList ? null : '응답 형식 오류');
          resolve({ status: res.statusCode, configured: true, keywordList, json, raw, error });
        });
      }
    );
    req.on('error', (e) => resolve({ status: 500, configured: true, keywordList: null, json: null, raw: '', error: e.message }));
    req.setTimeout(timeout, () => { req.destroy(); resolve({ status: 504, configured: true, keywordList: null, json: null, raw: '', error: 'timeout' }); });
  });
}

module.exports = { adCreds, isConfigured, signHeaders, toNum, fetchKeywordTool };
