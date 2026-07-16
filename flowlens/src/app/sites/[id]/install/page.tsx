import crypto from "crypto";
import { redirect } from "next/navigation";
import { prisma } from "@/lib/db";
import { loadSiteForUser } from "@/lib/site";
import { detectPlatform, type PlatformKey } from "@/lib/diagnose";
import InstallClient from "@/components/InstallClient";
import InstallGuides from "@/components/InstallGuides";
import ShareLinks from "@/components/ShareLinks";

export const dynamic = "force-dynamic";

// 감지된 플랫폼 → 설치 가이드 탭 매핑
function guideTab(key: PlatformKey | undefined): string {
  if (key === "wordpress") return "wordpress";
  if (key === "cafe24" || key === "imweb" || key === "sixshop") return "cafe24";
  if (key === "gtm") return "gtm";
  return "general";
}

export default async function InstallPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site } = await loadSiteForUser(id);
  if (!site) redirect("/dashboard");

  // 크롬 확장용 비밀 토큰. 기존 사이트는 없을 수 있어 최초 조회 시 발급한다.
  let overlayToken = site.overlayToken;
  if (!overlayToken) {
    overlayToken = crypto.randomBytes(24).toString("base64url");
    await prisma.site.update({ where: { id: site.id }, data: { overlayToken } });
  }

  // 사이트를 한 번 읽어 제작 플랫폼을 추정 → 그 플랫폼 안내를 자동으로 펼쳐준다.
  let platform: { key: PlatformKey; name: string; how: string } | null = null;
  try {
    const res = await fetch(`https://${site.domain}/`, {
      signal: AbortSignal.timeout(5000),
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36" },
    });
    if (res.ok) platform = detectPlatform((await res.text()).slice(0, 300000));
  } catch {
    /* 감지 실패 시 일반 안내 */
  }

  const links = site.shareLinks.map((l) => ({
    id: l.id,
    token: l.token,
    active: l.active,
    createdAt: l.createdAt.toISOString(),
  }));

  return (
    <div className="stack" style={{ gap: 18 }}>
      <InstallClient siteKey={site.siteKey} />

      {platform && (
        <div className="notice" style={{ background: "#eef5ff", borderColor: "#c9dcff" }}>
          <b>이 사이트는 &ldquo;{platform.name}&rdquo;로 만들어졌습니다.</b> — {platform.how}
          <br />
          <span className="muted small">아래에서 해당 방법이 자동으로 열려 있습니다.</span>
        </div>
      )}

      <InstallGuides siteKey={site.siteKey} siteId={site.id} defaultKey={guideTab(platform?.key)} />

      <ShareLinks siteId={site.id} links={links} />

      {/* 크롬 확장(실제 사이트 위 히트맵 오버레이) 설정값 */}
      <div className="card card-pad">
        <h4 style={{ marginBottom: 4 }}>크롬 확장으로 보기 (선택)</h4>
        <p className="muted small" style={{ marginTop: 0, marginBottom: 12 }}>
          실제 사이트를 돌아다니면서 그 위에 히트맵을 겹쳐 보고 싶을 때 사용합니다. 확장 팝업에 아래 값을 넣으세요.
        </p>
        <div className="stack" style={{ gap: 8 }}>
          <div>
            <span className="muted small">사이트 키</span>
            <div className="code">{site.siteKey}</div>
          </div>
          <div>
            <span className="muted small">오버레이 토큰</span>
            <div className="code">{overlayToken}</div>
          </div>
        </div>
        <div className="notice small" style={{ marginTop: 12, background: "#fdf2f2", borderColor: "#f5c2c2", color: "#a13b34" }}>
          <b>토큰은 비밀입니다.</b> 이 토큰이 있으면 이 사이트의 히트맵을 조회할 수 있으니 외부에 공유하지 마세요.
          (추적 스크립트에 들어가는 <b>사이트 키와 달리</b> 절대 공개되지 않습니다)
        </div>
      </div>

      <div className="notice small">
        <b>개인정보 보호 기본값</b> — 폼 입력값·비밀번호는 수집하지 않으며, 클릭 라벨의 이메일/전화/카드/주민번호 패턴은 전송 전 자동 마스킹됩니다. 좌표는 상대값만 저장하고 IP는 저장하지 않습니다.
      </div>
    </div>
  );
}
