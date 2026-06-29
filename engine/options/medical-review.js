'use strict';
const path = require('path');
const { validateMedicalAd, autoFix } = require(path.join(__dirname, '../../../lib/medical-ad-validator'));

/**
 * 생성된 HTML에 의료광고법 검수를 적용하고 위반어를 자동 수정한다.
 * @param {string} html  렌더링된 사이트 HTML
 * @returns {{ html: string, fixed: boolean, report: object }}
 */
function runMedicalReview(html) {
  const before = validateMedicalAd(html);
  if (before.pass) {
    return { html, fixed: false, report: { before, after: before } };
  }
  const fixedHtml = autoFix(html);
  const after = validateMedicalAd(fixedHtml);
  return {
    html: fixedHtml,
    fixed: true,
    report: { before, after },
  };
}

module.exports = { runMedicalReview };
