import { NextRequest, NextResponse } from "next/server";
import { loadSiteForUser } from "@/lib/site";
import { resolvePublicUrl } from "@/lib/diagnose";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// 설치 자가진단: 등록 도메인 홈페이지를 소유자 요청으로 1회 읽어
// 추적 스크립트 설치 여부·도메인 일치 여부를 확인하고 원인을 알려준다.
type Finding = { level: "ok" | "warn" | "fail"; title: string; detail: string };

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36";

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site } = await loadSiteForUser(id);
  if (!site) return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });

  const regDomain = site.domain.replace(/^https?:\/\//, "").replace(/\/.*$/, "").toLowerCase();

  const url = await resolvePublicUrl(site.domain);
  if (!url) {
    return NextResponse.json({
      ok: true,
      reachable: false,
      findings: [
        {
          level: "fail",
          title: "도메인을 찾을 수 없어요",
          detail: `등록한 주소 '${regDomain}'에 접속되지 않습니다. 사이트 주소가 정확한지, 실제로 열리는지 확인하세요.`,
        },
      ] as Finding[],
    });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  let html = "";
  let finalHost = "";
  let blocked = false;
  try {
    const res = await fetch(url.toString(), {
      signal: controller.signal,
      redirect: "follow",
      headers: { "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8" },
    });
    try {
      finalHost = new URL(res.url).hostname.toLowerCase();
    } catch {
      /* ignore */
    }
    const buf = await res.arrayBuffer();
    html = new TextDecoder("utf-8").decode(buf.slice(0, 500_000));
    if (!res.ok) blocked = true;
  } catch {
    blocked = true;
  } finally {
    clearTimeout(timer);
  }

  // WAF 등으로 자동 점검이 막힌 경우: 실패로 단정하지 않고 실시간 표시로 안내.
  if (blocked || (!/<title/i.test(html) && html.length < 2000)) {
    return NextResponse.json({
      ok: true,
      reachable: false,
      findings: [
        {
          level: "warn",
          title: "자동 점검이 막혔어요",
          detail:
            "사이트 보안 설정(WAF) 때문에 자동 확인이 어렵습니다. 사이트 자체는 정상일 수 있어요. 위의 '설치 확인됨'(실시간 이벤트) 표시로 판단하세요.",
        },
      ] as Finding[],
    });
  }

  const siteKeyFound = html.includes(site.siteKey);
  const tjsFound = /\/t\.js/i.test(html);
  const findings: Finding[] = [];

  if (siteKeyFound) {
    findings.push({
      level: "ok",
      title: "추적 스크립트가 설치돼 있어요",
      detail: "홈페이지에서 이 사이트의 추적 코드를 확인했습니다. 이제 방문이 생기면 데이터가 쌓입니다.",
    });
  } else if (tjsFound) {
    findings.push({
      level: "warn",
      title: "스크립트는 있는데 이 사이트의 키가 안 보여요",
      detail:
        "FlowLens 코드는 있지만 사이트 키가 다릅니다. 설치 코드의 data-site(또는 ?site=) 값이 이 사이트 키와 같은지 확인하세요.",
    });
  } else {
    findings.push({
      level: "fail",
      title: "추적 스크립트를 찾지 못했어요",
      detail:
        "홈페이지 소스에서 코드가 안 보입니다. ① 코드를 넣었는지 ② 저장·게시(Publish)했는지 ③ 맞는 페이지에 넣었는지 확인하세요. 아래 '설치 요청 메일'로 담당자에게 부탁할 수도 있어요.",
    });
  }

  // 도메인 불일치(수집은 등록 도메인과 일치해야 함) — 흔한 '스크립트는 있는데 데이터가 안 쌓임' 원인.
  const hostMismatch =
    finalHost &&
    regDomain &&
    finalHost !== regDomain &&
    !finalHost.endsWith("." + regDomain) &&
    !regDomain.endsWith("." + finalHost);
  if (hostMismatch) {
    findings.push({
      level: "warn",
      title: "실제 주소가 등록 주소와 달라요",
      detail: `등록: ${regDomain} · 실제 접속: ${finalHost}. 방문자가 실제로 여는 주소를 등록 도메인과 맞춰야 수집됩니다(예: www 유무, 도메인 변경).`,
    });
  }

  return NextResponse.json({ ok: true, reachable: true, siteKeyFound, findings });
}
