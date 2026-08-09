/**
 * 시각 한 줄 — **서울 기준으로, 한 곳에서.**
 *
 * 리포트 목록과 리포트 상세가 이 함수를 한 벌씩 갖고 있었다(2026-08-09 실측). 같은
 * 발행본이 두 화면에서 다른 시각으로 보이면 안 되는데, 두 벌이면 언젠가 한쪽만
 * 고쳐진다(0-D).
 *
 * `timeZone` 을 못박는 것이 핵심이다. 안 박으면 **보는 사람의 시간대**로 그려지고,
 * 그러면 같은 발행본이 서버 로그와 다른 시각을 말한다.
 */
export function formatWhen(value: string | null): string {
  if (value === null) return '시각 기록 없음';
  const at = new Date(value);
  // 못 읽은 값은 지어내지 않고 받은 그대로 낸다. "1970-01-01" 보다 원문이 낫다.
  if (Number.isNaN(at.getTime())) return value;
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Seoul',
  }).format(at);
}
