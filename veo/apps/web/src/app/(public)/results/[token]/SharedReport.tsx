'use client';

/**
 * 공유 링크로 열어 본 진단 결과 — 진단 화면의 Report 를 그대로 다시 그린다.
 *
 * 별도 화면을 만들지 않는 것이 요점이다: 공유받은 사람이 보는 리포트와 진단한
 * 사람이 본 리포트가 한 컴포넌트에서 나오므로, 둘이 다르게 그려질 방법이 없다.
 * 지난 측정과의 비교(previous)만 없다 — 그 기록은 진단한 브라우저의 localStorage
 * 에 있고, 링크를 받은 사람의 것이 아니다.
 */

import { useEffect, useRef, useState } from 'react';

import { Report } from '../../tools/checker/PublicChecker';
import type { ScanResult, ScanVerdict } from '@/lib/scan-api-types';

export function SharedReport({ result }: { readonly result: ScanResult }) {
  const [filter, setFilter] = useState<'ALL' | ScanVerdict>('ALL');
  const reportRef = useRef<HTMLDivElement | null>(null);

  // 인쇄(PDF 저장) 직전에 접힌 항목을 전부 연다 — 진단 화면과 같은 이유.
  useEffect(() => {
    const openAll = () => {
      reportRef.current
        ?.querySelectorAll('details')
        .forEach((element) => element.setAttribute('open', ''));
    };
    window.addEventListener('beforeprint', openAll);
    return () => window.removeEventListener('beforeprint', openAll);
  }, []);

  return (
    <Report
      result={result}
      kind={result.kind}
      filter={filter}
      onFilter={setFilter}
      reportRef={reportRef}
      previous={null}
    />
  );
}
