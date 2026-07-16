import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import { prisma } from "@/lib/db";
import TopBar from "@/components/TopBar";

export const dynamic = "force-dynamic";

const ERRORS: Record<string, string> = {
  invalid: "사이트명과 도메인을 입력해 주세요.",
  domain: "도메인 형식이 올바르지 않습니다. 예: good-tour.kr",
  client: "고객사명을 입력하거나 기존 고객사를 선택해 주세요.",
  limit: "현재 요금제의 사이트 수 한도를 모두 사용했습니다. 요금제를 올리면 더 등록할 수 있습니다.",
};

export default async function NewSitePage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const clients = await prisma.client.findMany({
    where: { agencyId: user.agencyId },
    orderBy: { createdAt: "asc" },
  });

  const error = (await searchParams).error;

  return (
    <>
      <TopBar agencyName={user.agency.name} userName={user.name} />
      <div className="container" style={{ maxWidth: 620 }}>
        <Link href="/dashboard" className="muted small">← 대시보드</Link>
        <h1 style={{ fontSize: 22, margin: "10px 0 4px" }}>사이트 등록</h1>
        <p className="muted small" style={{ marginBottom: 20 }}>
          고객사와 웹사이트를 등록하면 추적 스크립트(설치 코드)가 발급됩니다.
        </p>

        {error && (
          <div className="notice small" style={{ borderColor: "#ef4444", color: "#b91c1c", marginBottom: 16 }}>
            {ERRORS[error] || "입력을 확인해 주세요."}
          </div>
        )}

        <form action="/api/sites" method="post" className="card card-pad stack" style={{ gap: 16 }}>
          {clients.length > 0 && (
            <div>
              <label className="small" style={{ fontWeight: 700 }}>기존 고객사에 추가 (선택)</label>
              <select name="clientId" className="field-inline" style={{ width: "100%", marginTop: 6 }} defaultValue="">
                <option value="">➕ 새 고객사 만들기</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                기존 고객사를 고르면 아래 “새 고객사명”은 무시됩니다.
              </p>
            </div>
          )}

          <div>
            <label className="small" style={{ fontWeight: 700 }}>새 고객사명</label>
            <input name="clientName" placeholder="예: 굿투어" className="field-inline" style={{ width: "100%", marginTop: 6 }} />
          </div>

          <div>
            <label className="small" style={{ fontWeight: 700 }}>업종</label>
            <select name="industry" className="field-inline" style={{ width: "100%", marginTop: 6 }} defaultValue="ETC">
              <option value="ECOMMERCE">이커머스 / 쇼핑몰</option>
              <option value="CLINIC">병원 / 의료</option>
              <option value="EDU">교육</option>
              <option value="B2B">B2B / 기업</option>
              <option value="ETC">기타</option>
            </select>
          </div>

          <hr style={{ border: 0, borderTop: "1px solid var(--line, #e5e7eb)", margin: "2px 0" }} />

          <div>
            <label className="small" style={{ fontWeight: 700 }}>사이트명</label>
            <input name="siteName" placeholder="예: 굿투어 홈페이지" className="field-inline" style={{ width: "100%", marginTop: 6 }} required />
          </div>

          <div>
            <label className="small" style={{ fontWeight: 700 }}>도메인</label>
            <input name="domain" placeholder="예: good-tour.kr" className="field-inline" style={{ width: "100%", marginTop: 6 }} required />
            <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
              http:// 나 www 없이 순수 주소만. 이 도메인에서 들어오는 데이터만 수집됩니다(도용 방지).
            </p>
          </div>

          <div className="row" style={{ gap: 8, marginTop: 4 }}>
            <button type="submit" className="btn primary">사이트 등록하고 설치 코드 받기</button>
            <Link href="/dashboard" className="btn sm">취소</Link>
          </div>
        </form>
      </div>
    </>
  );
}
