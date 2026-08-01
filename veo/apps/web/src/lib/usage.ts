import 'server-only';

import { callConsoleApi, type ConsoleOutcome } from '@/lib/console-api';

/**
 * 외부 API 한도 — 넘기 **전에** 보이는 숫자.
 *
 * PageSpeed 는 하루 25,000회까지 무료라 청구서는 오지 않는다. 위험은 돈이 아니라
 * 하루다: 넘기면 그날의 모든 고객 진단에서 성능이 측정 불가가 되고, 화면에는
 * **사이트의 문제처럼 보이는 형태**로 나타난다.
 */

export interface PageSpeedQuota {
  readonly provider: string;
  /** 오늘(UTC) **전체에서** 나간 호출 수. 실패한 호출도 한도를 썼으므로 들어 있다. */
  readonly calls_today: number;
  /**
   * 이 조직이 쓴 몫.
   *
   * **남은 양이 아니다.** 한도는 API 키 하나에 걸리고 키는 하나라, 다른 조직이 태운
   * 것도 같은 한도를 쓴다. 이 값을 `remaining` 과 같은 크기로 그리면 화면이 "우리는
   * 200회밖에 안 썼는데요" 라고 말하는 동안 키는 이미 막혀 있다.
   */
  readonly calls_by_this_organization: number;
  readonly daily_quota: number;
  readonly remaining: number;
  readonly used_ratio: number;
  /** 한도를 넘기 **전에** 참이 된다. */
  readonly is_warning: boolean;
  readonly is_exhausted: boolean;
  /** 남은 호출로 더 돌릴 수 있는 진단 횟수(상한 기준). */
  readonly scans_remaining: number;
  readonly calls_per_scan: number;
  readonly window_start: string;
  readonly window_end: string;
  /** 화면에 **그대로** 쓴다. 숫자로 문장을 다시 지으면 설명이 두 벌이 된다. */
  readonly summary_ko: string;
  readonly caveat_ko: string;
  /** 할 일이 없으면 비어 있다. 여유 있을 때까지 띄우면 급할 때 아무도 안 읽는다. */
  readonly remedies_ko: readonly string[];
}

export async function readPageSpeedQuota(): Promise<ConsoleOutcome<PageSpeedQuota>> {
  return callConsoleApi('/api/usage/pagespeed-quota');
}
