/**
 * 서버가 "언제 다시 오라" 고 한 값. 한 곳에서 읽는다.
 *
 * 공개 키워드 조회와 진단 호출이 이 함수를 한 벌씩 갖고 있었다(2026-08-09 실측).
 *
 * **못 읽으면 `null` 이지 `0` 이 아니다.** `0` 은 "지금 바로 다시 걸어라" 라는 뜻이라,
 * 헤더를 못 읽은 것을 `0` 으로 접으면 한도에 걸린 클라이언트가 곧바로 다시 두드린다.
 */
export function retryAfterFrom(response: Response): number | null {
  const header = response.headers.get('retry-after');
  if (header === null) {
    return null;
  }
  const seconds = Number.parseInt(header, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}
