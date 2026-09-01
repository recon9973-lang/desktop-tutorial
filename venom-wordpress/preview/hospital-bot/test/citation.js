'use strict';

// AEO 인용(cited) 판정 검증 — 네트워크·키 불필요
//   node hospital-bot/test/citation.js

const path = require('path');
const C = require(path.join(__dirname, '..', '..', 'lib', 'geo-citation'));

let fail = 0;
function assert(cond, msg) { if (!cond) { console.error('  ✗ FAIL:', msg); fail = 1; } else { console.log('  ✓', msg); } }

console.log('== 유닛: urlKey (호스트+경로 정규화) ==');
assert(C.urlKey('https://www.Example.co.kr/') === 'example.co.kr', 'www·대문자·끝슬래시 제거');
assert(C.urlKey('blog.naver.com/siwonpain') === 'blog.naver.com/siwonpain', '스킴 없는 입력도 처리');
assert(C.urlKey('없는주소::') === '', '파싱 실패는 빈 문자열');

console.log('== 유닛: siteDomains ==');
const doms = C.siteDomains({ websiteUrl: 'https://siwon-clinic.co.kr', citationDomains: ['blog.naver.com/siwonpain', 'https://siwon-clinic.co.kr/'] });
assert(doms.length === 2, `중복 제거 후 ${doms.length}건`);
assert(doms.indexOf('siwon-clinic.co.kr') >= 0 && doms.indexOf('blog.naver.com/siwonpain') >= 0, '홈페이지·블로그 경로 모두 등록');

console.log('== 유닛: domainMatch (공용 호스트 오탐 방지) ==');
assert(C.domainMatch('https://blog.naver.com/siwonpain/223456789', doms), '자사 네이버 블로그 글 → 인용');
assert(!C.domainMatch('https://blog.naver.com/othercli/111', doms), '남의 네이버 블로그 → 인용 아님');
assert(!C.domainMatch('https://blog.naver.com/siwonpain2/222', doms), '경계 검사: /siwonpain2 는 별개 계정');
assert(C.domainMatch('https://siwon-clinic.co.kr/notice/12', doms), '자사 홈페이지 하위 경로 → 인용');
assert(!C.domainMatch('https://map.kakao.com/', doms), '미등록 출처 → 인용 아님');

console.log('== 유닛: coreInUrl (퍼센트 인코딩 한글 URL) ==');
const cores = ['시원마취통증의학과', '시원마취통증'];
const encoded = 'https://search.naver.com/search.naver?query=' + encodeURIComponent('시원마취통증의학과 포항');
assert(C.coreInUrl(encoded, cores), '인코딩된 한글 URL 디코드 후 core 일치');
assert(!C.coreInUrl('https://blog.naver.com/xxx/223456789', cores), '한글 없는 URL은 core 불일치');

console.log('== 통합: isCited / citedBy ==');
const citations = ['https://map.kakao.com/', 'https://blog.naver.com/siwonpain/223456789'];
assert(C.citedBy(citations, doms, cores) === 'https://blog.naver.com/siwonpain/223456789', '첫 매칭 출처 URL 반환');
assert(C.citedBy(['https://map.kakao.com/'], doms, cores) === null, '매칭 없으면 null');
assert(C.citedBy(citations, [], cores) === null, '출처 미등록이면 도메인 판정 불가(허위 인용 없음)');

console.log(fail ? '\n❌ 일부 실패' : '\n✅ 전체 통과');
process.exit(fail);
