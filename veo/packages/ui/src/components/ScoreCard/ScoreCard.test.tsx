import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ScoreCard } from './ScoreCard';

describe('ScoreCard', () => {
  it('renders 측정 불가 instead of 0 when the score is null', () => {
    render(
      <ScoreCard
        title="SEO 기술 준비도"
        score={null}
        specVersion="veo.seo.readiness 1.0.0"
        coverage={0.42}
        confidence={0.61}
      />,
    );

    expect(screen.getByText('측정 불가')).toBeInTheDocument();
    expect(screen.queryByText('0')).toBeNull();
    expect(screen.queryByText('0.0')).toBeNull();
  });

  it('always renders spec version, coverage and confidence next to a numeric score', () => {
    render(
      <ScoreCard
        title="GEO 준비도"
        score={96.875}
        specVersion="veo.geo.readiness 1.0.0"
        coverage={1}
        confidence={0.9}
      />,
    );

    // 96.875 를 **자른** 값이다. 반올림했다면 96.88 이 나온다 — 재지 않은 값이다.
    expect(screen.getByText('96.87')).toBeInTheDocument();
    expect(screen.getByText('veo.geo.readiness 1.0.0')).toBeInTheDocument();
    expect(screen.getByText('100.00%')).toBeInTheDocument();
    expect(screen.getByText('90.00%')).toBeInTheDocument();
    expect(screen.getByText('기준 버전')).toBeInTheDocument();
    expect(screen.getByText('측정 범위')).toBeInTheDocument();
    expect(screen.getByText('신뢰도')).toBeInTheDocument();
  });

  it('still renders spec version, coverage and confidence when the score is null', () => {
    render(
      <ScoreCard
        title="SEO 기술 준비도"
        score={null}
        specVersion="veo.seo.readiness 1.0.0"
        coverage={0}
        confidence={0}
      />,
    );

    expect(screen.getByText('veo.seo.readiness 1.0.0')).toBeInTheDocument();
    expect(screen.getByText('기준 버전')).toBeInTheDocument();
    expect(screen.getByText('측정 범위')).toBeInTheDocument();
    expect(screen.getByText('신뢰도')).toBeInTheDocument();
    expect(screen.getAllByText('0.00%')).toHaveLength(2);
  });

  it('states that the score is not a ranking guarantee', () => {
    render(
      <ScoreCard
        title="SEO 기술 준비도"
        score={81.25}
        specVersion="veo.seo.readiness 1.0.0"
        coverage={0.9}
        confidence={0.8}
      />,
    );
    expect(
      screen.getByText(/검색 순위를 예측하거나 보장하지 않습니다/),
    ).toBeInTheDocument();
  });
});
