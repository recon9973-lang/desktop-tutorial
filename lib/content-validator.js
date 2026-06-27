'use strict';

// 자동 생성 블로그 본문의 "콘텐츠 오류"를 검수·정리하는 모듈.
// 의료광고법(medical-ad-validator)과 별개로, 인코딩 깨짐·잘림·구분자 잔존·
// 빈 태그·깨진 HTML 구조 등 "발행하면 안 되는 오류"를 잡아낸다.

const REPLACEMENT_CHAR = '�'; // � (멀티바이트 깨짐 시 나타나는 문자)
const DELIMITER_RE = /<{2,3}\s*(TITLE|SEO|META|KEYWORDS|HTML|END)\s*>{2,3}/gi;

/**
 * 본문을 발행 가능한 형태로 "정리"한다(수정 가능한 오류 자동 보정).
 * - 깨짐 문자(�) 및 그 주변 잔여물 제거
 * - 남아있는 출력 구분자(<<<HTML>>> 등) 제거
 * - JSON-LD가 아닌 script 태그 제거
 * - 빈 태그(<p></p>, <h2> </h2>) 제거
 * - 과도한 연속 공백/빈 줄 정리
 * @param {string} html
 * @returns {string}
 */
function cleanContent(html) {
  if (!html || typeof html !== 'string') return '';
  let out = html;

  // 1) 출력 구분자 잔존 제거
  out = out.replace(DELIMITER_RE, '');

  // 2) JSON-LD(application/ld+json) 이외의 script 제거
  out = out.replace(/<script\b(?![^>]*application\/ld\+json)[^>]*>[\s\S]*?<\/script>/gi, '');

  // 3) 깨짐 문자 제거 — 연속된 �는 한 번에 제거하고, 한글 사이에 낀 경우 공백 흔적도 정리
  out = out.replace(new RegExp(REPLACEMENT_CHAR + '+', 'g'), '');

  // 4) 빈 블록 태그 제거 (여러 번 반복해 중첩 빈태그도 정리)
  for (let i = 0; i < 3; i++) {
    out = out.replace(/<(p|h1|h2|h3|h4|li|strong|em|span)>\s*<\/\1>/gi, '');
  }

  // 5) 과도한 공백/빈 줄 정리
  out = out.replace(/[ \t]{2,}/g, ' ').replace(/\n{3,}/g, '\n\n');

  return out.trim();
}

/**
 * 정리 후에도 남아있는 "발행 차단/주의" 오류를 검출.
 * severity: 'block' = 발행 금지(검수 대기), 'warn' = 경고(발행은 가능)
 * @param {string} html
 * @returns {Array<{type:string, severity:'block'|'warn', msg:string}>}
 */
function detectContentErrors(html) {
  const errors = [];
  const text = String(html || '');
  const plain = text.replace(/<[^>]+>/g, '').trim();

  // 인코딩 깨짐 (복구 불가 → 발행 차단)
  if (text.includes(REPLACEMENT_CHAR)) {
    errors.push({ type: 'encoding', severity: 'block', msg: '깨진 문자(�)가 포함되어 있습니다.' });
  }
  // 구분자 잔존
  if (DELIMITER_RE.test(text)) {
    errors.push({ type: 'delimiter', severity: 'block', msg: '출력 구분자(<<<...>>>)가 본문에 남아있습니다.' });
    DELIMITER_RE.lastIndex = 0;
  }
  // 본문 길이 부족
  if (plain.length < 800) {
    errors.push({ type: 'too-short', severity: 'block', msg: `본문이 너무 짧습니다(${plain.length}자).` });
  }
  // 잘림(truncation) — 마지막이 닫는 태그로 끝나지 않으면 중간에 끊겼을 가능성
  if (text && !/(<\/[a-z0-9]+>|\/>)\s*$/i.test(text)) {
    errors.push({ type: 'truncated', severity: 'block', msg: '본문이 닫는 태그로 끝나지 않습니다(생성 중 잘림 의심).' });
  }
  // 핵심 태그 짝 안 맞음(깨진 HTML 구조)
  for (const tag of ['h2', 'h3', 'table', 'ul', 'ol', 'figure']) {
    const open = (text.match(new RegExp('<' + tag + '\\b', 'gi')) || []).length;
    const close = (text.match(new RegExp('</' + tag + '>', 'gi')) || []).length;
    if (open !== close) {
      errors.push({ type: 'broken-html', severity: 'warn', msg: `<${tag}> 태그 짝이 맞지 않습니다(${open}/${close}).` });
    }
  }
  return errors;
}

/**
 * 한 번에 정리 + 검수.
 * @param {string} html
 * @returns {{ cleaned:string, errors:Array, hasBlockingErrors:boolean }}
 */
function reviewContent(html) {
  // 깨짐 문자는 cleanContent가 제거하지만, 제거해도 글자가 소실된 것이므로
  // "원본에 깨짐이 있었는지"를 먼저 기록해 발행 차단(검수 대기) 사유로 남긴다.
  const hadReplacement = String(html || '').includes(REPLACEMENT_CHAR);
  const cleaned = cleanContent(html);
  const errors = detectContentErrors(cleaned);
  if (hadReplacement) {
    errors.unshift({
      type: 'encoding',
      severity: 'block',
      msg: '깨진 문자(�)로 일부 내용이 소실되었습니다. 자동 발행하지 않고 재생성/검수가 필요합니다.',
    });
  }
  return {
    cleaned,
    errors,
    hasBlockingErrors: errors.some(e => e.severity === 'block'),
  };
}

module.exports = { cleanContent, detectContentErrors, reviewContent, REPLACEMENT_CHAR };
