import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DataSourceBadge } from './DataSourceBadge';

describe('DataSourceBadge', () => {
  it('renders the Korean origin label and the collected-at timestamp', () => {
    const { container } = render(
      <DataSourceBadge source="NAVER_SEARCH_AD" collectedAt="2026-07-28T01:30:00Z" />,
    );

    expect(screen.getByText('네이버 검색광고 API')).toBeInTheDocument();
    const time = container.querySelector('time');
    expect(time).not.toBeNull();
    expect(time?.getAttribute('datetime')).toBe('2026-07-28T01:30:00Z');
    // Rendered in Asia/Seoul so server and client agree.
    expect(time?.textContent).toContain('2026');
    expect(time?.textContent).toContain('10:30');
  });

  it('labels every supported origin', () => {
    const cases = [
      ['NAVER_SEARCH_AD', '네이버 검색광고 API'],
      ['NAVER_DATALAB', '네이버 데이터랩'],
      ['CALCULATED', 'VEO 계산값'],
      ['VEO_CRAWLER', 'VEO 수집기'],
    ] as const;

    for (const [source, label] of cases) {
      const { unmount } = render(
        <DataSourceBadge source={source} collectedAt="2026-07-28T01:30:00Z" />,
      );
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it('does not claim the value is real time', () => {
    const { container } = render(
      <DataSourceBadge source="VEO_CRAWLER" collectedAt="2026-07-28T01:30:00Z" />,
    );
    expect(container.textContent).not.toContain('실시간');
    expect(container.textContent).toContain('수집 시각');
  });
});
