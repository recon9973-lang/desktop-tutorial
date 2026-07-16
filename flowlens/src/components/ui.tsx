import type { Confidence } from "@/lib/rules";

export function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="card metric">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
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
