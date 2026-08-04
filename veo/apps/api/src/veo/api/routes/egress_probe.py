"""임시 점검 창구 — **확인이 끝나면 지운다.**

두 가지를 실제로 봐야 해서 만든다. 둘 다 **해외에서 나가는 요청**으로만 답할 수 있고,
사무실 회선·Vercel(둘 다 한국)로는 답이 안 나온다.

1. 막힌 응답 759바이트에 **무엇이라고 적혀 있는가.** 지금까지 크기와 "제목이 없다" 만
   알았지 내용을 한 번도 못 읽었다.
2. 해외 IP 에서 **User-Agent 를 바꾸면 뚫리는가.** 한국에서는 UA 를 무엇으로 바꿔도
   전부 정상이라 이 질문이 갈리지 않았다. 타사 도구가 같은 사이트를 문제없이 재는
   이유가 UA 때문인지 IP 때문인지가 여기서 갈린다.

**입력을 받지 않는다.** 주소도 UA 도 아래 목록에 박혀 있다 — 임의 주소를 받는 창구는
그대로 SSRF 통로가 되고, 이 파일은 `veo.common.security.fetcher` 의 가드를 우회하는
자리가 아니다.
"""

from __future__ import annotations

from typing import Any, Final

import httpx
from fastapi import APIRouter

router = APIRouter(tags=["임시 점검"])

#: 막는 곳 둘, 안 막는 곳 하나(대조군).
TARGETS: Final = ("https://venomad.com", "https://good-tour.kr", "https://chamsarang1075.com")

#: 신원을 하나씩 바꿔 본다. 우리 것 → 브라우저 → 검색엔진 봇 → 빈 값.
AGENTS: Final = {
    "veo": "VEO-Bot/1.0 (+https://veo.seokorea.org/bot; SEO/GEO diagnostics by VENOM)",
    "chrome": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "googlebot": (
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    ),
    "empty": "",
}


@router.get("/egress-probe", include_in_schema=False)
async def egress_probe() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    async with httpx.AsyncClient(follow_redirects=True, timeout=25.0) as client:
        try:
            who = (await client.get("https://ipinfo.io/json")).json()
        except Exception as error:
            who = {"error": str(error)}

        for url in TARGETS:
            for label, agent in AGENTS.items():
                try:
                    response = await client.get(url, headers={"user-agent": agent})
                    body = response.text
                    rows.append(
                        {
                            "url": url,
                            "agent": label,
                            "status": response.status_code,
                            "final_url": str(response.url),
                            "bytes": len(body),
                            # 막힌 응답이 무엇이라고 말하는지. 이것을 못 읽어서 여기까지 왔다.
                            "head": body[:900],
                        }
                    )
                except Exception as error:
                    rows.append({"url": url, "agent": label, "error": str(error)})

    return {"egress": who, "rows": rows}
