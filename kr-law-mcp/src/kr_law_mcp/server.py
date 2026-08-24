"""FastMCP 서버 정의 + 8개 MCP 도구 등록"""

from fastmcp import FastMCP
from .api_client import LawAPIClient

mcp = FastMCP(
    "kr-law",
    instructions=(
        "국가법령정보센터(law.go.kr) 오픈 API를 활용하여 "
        "한국 법령, 판례, 법령해석례, 행정규칙을 검색하고 조회하는 MCP 서버입니다."
    ),
)

client = LawAPIClient()


# ─────────────────────────────────────────────
# 1. 법령 관련 도구 (3개)
# ─────────────────────────────────────────────

@mcp.tool(
    description=(
        "한국 법령(법률, 대통령령, 총리령, 부령)을 키워드로 검색합니다. "
        "법령명이나 조문 내용에 포함된 키워드를 입력하세요. "
        "검색 키워드는 한 단어씩 사용하세요. 복합 키워드(예: '전자상거래 청약철회')는 0건이 반환될 수 있습니다. "
        "대신 핵심 단어 하나(예: '청약철회')로 검색 후 결과에서 필터링하세요. "
        "판례를 찾으려면 search_precedent를, "
        "법령해석례를 찾으려면 search_interpretation을 사용하세요."
    )
)
async def search_law(query: str, page: int = 1, display: int = 20) -> dict:
    """법령 검색: 키워드로 법령 목록을 반환합니다."""
    # 1페이지 + 짧은 키워드(법령명으로 추정) → 확대 검색 후 정확일치 우선 정렬
    if page == 1 and len(query) <= 5:
        result = await client.search("law", query=query, page=1, display=100)
        items = result.get("items", [])
        exact = [i for i in items if i.get("법령명한글", "") == query]
        starts = [i for i in items if i.get("법령명한글", "").startswith(query) and i not in exact]
        rest = [i for i in items if i not in exact and i not in starts]
        sorted_items = exact + starts + rest
        result["items"] = sorted_items[:display]
        result["totalCnt"] = len(sorted_items)
        return result
    return await client.search("law", query=query, page=page, display=display)


@mcp.tool(
    description=(
        "특정 법령의 전체 조문 또는 특정 조문을 조회합니다. "
        "법령 일련번호(MST)가 필요합니다. "
        "search_law로 먼저 법령을 검색한 후, 결과의 '법령일련번호' 필드 값을 law_id에 넣으세요. "
        "주의: '법령ID' 필드가 아닌 '법령일련번호' 필드를 사용해야 합니다. "
        "article_no를 지정하면 해당 조문만 반환합니다."
    )
)
async def get_law_detail(law_id: str, article_no: str | None = None) -> dict:
    """법령 조문 조회: 특정 법령의 조문 내용을 반환합니다."""
    result = await client.get_detail("law", MST=law_id)

    # article_no가 지정된 경우 해당 조문만 필터링
    if article_no and "조문" in result:
        jo = result.get("조문", {})
        articles = jo.get("조문단위", []) if isinstance(jo, dict) else []
        if not isinstance(articles, list):
            articles = [articles]
        filtered = []
        for art in articles:
            if isinstance(art, dict):
                no = art.get("조문번호", "")
                if str(article_no) == str(no):
                    filtered.append(art)
        if filtered:
            result["조문"] = {"조문단위": filtered}
            result["_filter_note"] = f"조문번호 '{article_no}' 필터 적용됨"

    return result


@mcp.tool(
    description=(
        "특정 법령의 제정·개정 이력과 제개정이유를 조회합니다. "
        "법령 일련번호(MST)가 필요합니다. "
        "search_law로 먼저 법령을 검색한 후, 결과의 '법령일련번호' 필드 값을 law_id에 넣으세요. "
        "주의: '법령ID' 필드가 아닌 '법령일련번호' 필드를 사용해야 합니다."
    )
)
async def get_law_history(law_id: str) -> dict:
    """법령 연혁 조회: 제정·개정 이력을 반환합니다."""
    result = await client.get_detail("law", MST=law_id)

    # 기본정보에서 연혁 관련 필드 추출
    history_fields = {}
    basic = result.get("기본정보", {})
    if isinstance(basic, dict):
        for key in ("법령명_한글", "법령ID", "제개정구분", "공포일자", "시행일자",
                     "소관부처", "공포번호", "법종구분"):
            if key in basic:
                history_fields[key] = basic[key]

    # 연혁, 개정문, 제개정이유는 최상위에 있을 수 있음
    for key in ("연혁", "개정문", "제개정이유"):
        if key in result:
            history_fields[key] = result[key]

    return history_fields if history_fields else result


# ─────────────────────────────────────────────
# 2. 판례 관련 도구 (2개)
# ─────────────────────────────────────────────

@mcp.tool(
    description=(
        "한국 판례(대법원, 하급심)를 키워드로 검색합니다. "
        "사건명, 판시사항, 판결요지 등에 포함된 키워드를 입력하세요. "
        "검색 키워드는 한 단어씩 사용하세요. 복합 키워드(예: '전자상거래 청약철회')는 0건이 반환될 수 있습니다. "
        "대신 핵심 단어 하나(예: '청약철회')로 검색 후 결과에서 필터링하세요. "
        "법령을 찾으려면 search_law를, "
        "법령해석례를 찾으려면 search_interpretation을 사용하세요."
    )
)
async def search_precedent(query: str, page: int = 1, display: int = 20) -> dict:
    """판례 검색: 키워드로 판례 목록을 반환합니다."""
    return await client.search("prec", query=query, page=page, display=display)


@mcp.tool(
    description=(
        "특정 판례의 전문(판시사항, 판결요지, 참조조문, 참조판례, 판례내용)을 조회합니다. "
        "판례 일련번호(ID)가 필요합니다. "
        "search_precedent로 먼저 판례를 검색한 후, 결과의 '판례일련번호' 필드 값을 precedent_id에 넣으세요."
    )
)
async def get_precedent_detail(precedent_id: str) -> dict:
    """판례 본문 조회: 특정 판례의 전문을 반환합니다."""
    return await client.get_detail("prec", ID=precedent_id)


# ─────────────────────────────────────────────
# 3. 법령해석례 관련 도구 (2개)
# ─────────────────────────────────────────────

@mcp.tool(
    description=(
        "법제처 법령해석례를 키워드로 검색합니다. "
        "법령 해석에 관한 질의·회답 사례를 찾을 때 사용하세요. "
        "검색 키워드는 한 단어씩 사용하세요. 복합 키워드(예: '전자상거래 청약철회')는 0건이 반환될 수 있습니다. "
        "대신 핵심 단어 하나(예: '청약철회')로 검색 후 결과에서 필터링하세요. "
        "법령 자체를 찾으려면 search_law를, "
        "판례를 찾으려면 search_precedent를 사용하세요."
    )
)
async def search_interpretation(query: str, page: int = 1, display: int = 20) -> dict:
    """법령해석례 검색: 키워드로 해석례 목록을 반환합니다."""
    return await client.search("expc", query=query, page=page, display=display)


@mcp.tool(
    description=(
        "특정 법령해석례의 전문(질의요지, 회답, 이유)을 조회합니다. "
        "해석례 일련번호(ID)가 필요합니다. "
        "search_interpretation으로 먼저 검색한 후, 결과의 '법령해석례일련번호' 필드 값을 interpretation_id에 넣으세요."
    )
)
async def get_interpretation_detail(interpretation_id: str) -> dict:
    """법령해석례 본문 조회: 특정 해석례의 전문을 반환합니다."""
    return await client.get_detail("expc", ID=interpretation_id)


# ─────────────────────────────────────────────
# 4. 행정규칙 관련 도구 (2개)
# ─────────────────────────────────────────────

@mcp.tool(
    description=(
        "행정규칙(훈령, 예규, 고시 등)을 키워드로 검색합니다. "
        "행정규칙명이나 내용에 포함된 키워드를 입력하세요. "
        "검색 키워드는 한 단어씩 사용하세요. 복합 키워드(예: '전자상거래 청약철회')는 0건이 반환될 수 있습니다. "
        "대신 핵심 단어 하나(예: '청약철회')로 검색 후 결과에서 필터링하세요."
    )
)
async def search_admin_rule(query: str, page: int = 1, display: int = 20) -> dict:
    """행정규칙 검색: 키워드로 행정규칙 목록을 반환합니다."""
    return await client.search("admrul", query=query, page=page, display=display)


@mcp.tool(
    description=(
        "특정 행정규칙(훈령, 예규, 고시 등)의 본문을 조회합니다. "
        "행정규칙 일련번호(ID)가 필요합니다. "
        "search_admin_rule로 먼저 검색한 후, 결과의 '행정규칙일련번호' 필드 값을 admin_rule_id에 넣으세요."
    )
)
async def get_admin_rule_detail(admin_rule_id: str) -> dict:
    """행정규칙 본문 조회: 특정 행정규칙의 본문을 반환합니다."""
    return await client.get_detail("admrul", ID=admin_rule_id)


# ─────────────────────────────────────────────
# 서버 실행 진입점
# ─────────────────────────────────────────────

def main():
    mcp.run()


if __name__ == "__main__":
    main()
