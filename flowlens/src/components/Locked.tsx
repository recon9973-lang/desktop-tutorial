import Link from "next/link";
import { PLANS, type Feature } from "@/lib/plans";

// 현재 요금제에 없는 기능일 때 보여주는 안내 (차단 대신 업그레이드 유도).
export default function Locked({ feature, title, desc }: { feature: Feature; title: string; desc: string }) {
  // 이 기능을 포함한 가장 저렴한 요금제 찾기
  const need = PLANS.filter((p) => p.features.includes(feature)).sort((a, b) => a.price - b.price)[0];

  return (
    <div className="card card-pad" style={{ textAlign: "center", padding: "48px 24px" }}>
      <div style={{ fontSize: 32, marginBottom: 10 }}>🔒</div>
      <h3 style={{ fontSize: 17, marginBottom: 6 }}>{title}</h3>
      <p className="muted small" style={{ marginBottom: 6 }}>{desc}</p>
      {need && (
        <p className="small" style={{ marginBottom: 18 }}>
          <b>{need.name}</b> 요금제({need.priceLabel}/월)부터 사용할 수 있습니다.
        </p>
      )}
      <Link href="/billing" className="btn primary">요금제 보기</Link>
    </div>
  );
}
