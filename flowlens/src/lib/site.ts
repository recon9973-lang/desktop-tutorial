import { prisma } from "./db";
import { getCurrentUser } from "./session";

// 사이트를 로그인 유저의 대행사 범위로만 조회 (멀티테넌시 격리).
// user가 없거나 다른 대행사 사이트면 null.
export async function loadSiteForUser(siteId: string) {
  const user = await getCurrentUser();
  if (!user) return { user: null, site: null };
  const site = await prisma.site.findFirst({
    where: { id: siteId, client: { agencyId: user.agencyId } },
    include: { client: true, shareLinks: { orderBy: { createdAt: "desc" } } },
  });
  return { user, site };
}
