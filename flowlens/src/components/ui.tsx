import type { Confidence } from "@/lib/rules";

// help를 주면 카드에 마우스를 올렸을 때(또는 탭·키보드 포커스 시) 설명이 뜬다.
// CSS만으로 동작하므로 서버 컴포넌트 그대로 쓸 수 있다(자바스크립트 추가 없음).
// 문구는 @/lib/metric-help 에 모아둔다.
export function MetricCard({ label, value, sub, help }: { label: string; value: string | number; sub?: string; help?: string }) {
  return (
    <div className={"card metric" + (help ? " has-help" : "")} tabIndex={help ? 0 : undefined}>
      <div className="label">
        {label}
        {help && (
          <span className="help-dot" aria-hidden="true">
            ?
          </span>
        )}
      </div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
      {help && (
        <span className="help-pop" role="tooltip">
          {help}
        </span>
      )}
    </div>
  );
}

export function ConfidenceBadge({ c }: { c: Confidence }) {
  const map = { HIGH: ["high", "신뢰도 높음"], MEDIUM: ["medium", "신뢰도 보통"], LOW: ["low", "신뢰도 낮음"] } as const;
  const [cls, label] = map[c];
  return <span className={`badge ${cls}`}>{label}</span>;
}

export function Bar({ value, max = 100, color }: { value: number; max?: number; color?: string }) {
  const pct = Math.min(100, max > 0 ? (value / max) * 100 : 0);
  return (
    <div className="bar-track">
      <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

const INDUSTRY_LABEL: Record<string, string> = {
  ECOMMERCE: "쇼핑몰",
  CLINIC: "병원/상담",
  EDU: "교육",
  B2B: "B2B",
  ETC: "기타",
};
export function IndustryBadge({ industry }: { industry: string }) {
  return <span className="badge industry">{INDUSTRY_LABEL[industry] ?? industry}</span>;
}
