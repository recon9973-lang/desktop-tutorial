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

// 입찰가 추정: 평균 노출 위치별 입찰가(average-position-bid)
//   POST /estimate/average-position-bid/keyword
//   body { device:'PC'|'MOBILE', items:[{ key:'<키워드>', position:<1~15> }] }
//   반환: { status, configured, error|null, bids: { '<키워드>': <원> } | null, device, position }
// 실측 불가 환경 대비: 응답 스키마가 예상과 다르면 bids=null로 안전 degrade(허위수치 금지).
function fetchBidEstimate(keywords, opts) {
  const timeout = (opts && opts.timeout) || 8000;
  const device = (opts && opts.device) === 'PC' ? 'PC' : 'MOBILE';
  const position = (opts && opts.position) || 2;
  return new Promise((resolve) => {
    const c = adCreds();
    if (!isConfigured(c)) return resolve({ status: 501, configured: false, error: '네이버 검색광고 API 미설정', bids: null, device, position });
    const list = (Array.isArray(keywords) ? keywords : [keywords])
      .map((k) => String(k).replace(/\s+/g, '')).filter(Boolean).slice(0, 5);
    if (!list.length) return resolve({ status: 400, configured: true, error: '키워드 없음', bids: null, device, position });

    const apiPath = '/estimate/average-position-bid/keyword';
    const body = JSON.stringify({ device, items: list.map((k) => ({ key: k, position })) });
    const headers = Object.assign(signHeaders('POST', apiPath, c), { 'Content-Length': Buffer.byteLength(body) });
    const req = https.request(
      { hostname: 'api.searchad.naver.com', path: apiPath, method: 'POST', headers },
      (res) => {
        const chunks = [];
        res.on('data', (d) => chunks.push(d));
        res.on('end', () => {
          const raw = Buffer.concat(chunks).toString('utf8');
          let json = null; try { json = JSON.parse(raw); } catch (e) { /* null */ }
          if (res.statusCode !== 200 || !json) {
            return resolve({ status: res.statusCode, configured: true, error: (json && (json.title || json.message)) || ('HTTP ' + res.statusCode), bids: null, device, position });
          }
          // 예상 스키마: { estimate:[{ key, position, bid }] }. 다른 형태면 안전 degrade.
          const arr = Array.isArray(json.estimate) ? json.estimate : (Array.isArray(json) ? json : null);
          if (!arr) return resolve({ status: 200, configured: true, error: '입찰가 응답 형식 예상과 다름', bids: null, device, position });
          const bids = {};
          arr.forEach((e) => { if (e && e.key != null && typeof e.bid === 'number') bids[e.key] = e.bid; });
          resolve({ status: 200, configured: true, error: null, bids: Object.keys(bids).length ? bids : null, device, position });
        });
      }
    );
    req.on('error', (e) => resolve({ status: 500, configured: true, error: e.message, bids: null, device, position }));
    req.setTimeout(timeout, () => { req.destroy(); resolve({ status: 504, configured: true, error: 'timeout', bids: null, device, position }); });
    req.write(body); req.end();
  });
}

module.exports = { adCreds, isConfigured, signHeaders, toNum, fetchKeywordTool, fetchBidEstimate };
