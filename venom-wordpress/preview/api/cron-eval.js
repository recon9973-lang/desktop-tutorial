'use strict';

/**
 * 주간 품질 채점 크론 엔드포인트 (Vercel Cron 전용).
 * eval-judge 핸들러를 n=24·save=1 고정으로 호출한다. 크론 path에 쿼리스트링을
 * 넣으면 배포 검증이 깨질 수 있어, 파라미터를 코드에서 주입하는 전용 경로로 분리.
 *
 * 인증: Vercel Cron은 CRON_SECRET을 Bearer로 전달 → eval-judge의 save 인증 통과.
 */

const evalJudge = require('./eval-judge');

module.exports = function handler(req, res) {
  req.method = 'GET';
  req.query = Object.assign({ n: '24', save: '1' }, req.query || {});
  return evalJudge(req, res);
};
