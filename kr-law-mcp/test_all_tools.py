"""kr-law-mcp 전체 도구 통합 테스트 스크립트

실행: python test_all_tools.py
"""

import asyncio
import sys
from kr_law_mcp.api_client import LawAPIClient


async def test_search_law(client: LawAPIClient):
    """1. search_law - 법령 검색"""
    print("\n" + "=" * 60)
    print("[1/8] search_law - '민법' 검색")
    print("=" * 60)
    result = await client.search("law", query="민법", display=5)
    print(f"  총 결과: {result['totalCnt']}건, 페이지: {result['page']}")
    for i, item in enumerate(result["items"][:5], 1):
        name = item.get("법령명한글", "?")
        law_id = item.get("법령일련번호", "?")
        kind = item.get("법령구분명", "")
        print(f"  [{i}] {name} ({kind}, MST: {law_id})")
    return result


async def test_get_law_detail(client: LawAPIClient, law_id: str, law_name: str):
    """2. get_law_detail - 법령 조문 조회"""
    print("\n" + "=" * 60)
    print(f"[2/8] get_law_detail - {law_name} (MST: {law_id})")
    print("=" * 60)
    result = await client.get_detail("law", MST=law_id)

    basic = result.get("기본정보", {})
    if isinstance(basic, dict):
        print(f"  법령명: {basic.get('법령명_한글', '?')}")
        print(f"  법종: {basic.get('법종구분', '?')}")
        print(f"  시행일자: {basic.get('시행일자', '?')}")

    jo = result.get("조문", {})
    articles = jo.get("조문단위", []) if isinstance(jo, dict) else []
    if not isinstance(articles, list):
        articles = [articles]
    # 실제 조문만 카운트 (전문/장제목 제외)
    real_articles = [a for a in articles if isinstance(a, dict) and a.get("조문여부") == "조문"]
    print(f"  조문 수: {len(real_articles)}개")
    for art in real_articles[:3]:
        no = art.get("조문번호", "?")
        title = art.get("조문제목", "")
        content = art.get("조문내용", "")[:80]
        print(f"    제{no}조 ({title}) {content}")
    return result


async def test_get_law_history(client: LawAPIClient, law_id: str, law_name: str):
    """3. get_law_history - 법령 연혁 조회"""
    print("\n" + "=" * 60)
    print(f"[3/8] get_law_history - {law_name} (MST: {law_id})")
    print("=" * 60)
    result = await client.get_detail("law", MST=law_id)

    basic = result.get("기본정보", {})
    if isinstance(basic, dict):
        print(f"  법령명: {basic.get('법령명_한글', '?')}")
        print(f"  제개정구분: {basic.get('제개정구분', '?')}")
        print(f"  공포일자: {basic.get('공포일자', '?')}")
        print(f"  시행일자: {basic.get('시행일자', '?')}")
        print(f"  소관부처: {basic.get('소관부처', '?')}")

    for key in ("개정문", "제개정이유"):
        val = result.get(key, "")
        if val:
            text = str(val)[:150]
            print(f"  {key} (발췌): {text}...")
    return result


async def test_search_precedent(client: LawAPIClient):
    """4. search_precedent - 판례 검색"""
    print("\n" + "=" * 60)
    print("[4/8] search_precedent - '손해배상' 검색")
    print("=" * 60)
    result = await client.search("prec", query="손해배상", display=5)
    print(f"  총 결과: {result['totalCnt']}건")
    for i, item in enumerate(result["items"][:5], 1):
        name = item.get("사건명", "?")
        case_no = item.get("사건번호", "?")
        prec_id = item.get("판례일련번호", "?")
        court = item.get("법원명", "?")
        date = item.get("선고일자", "?")
        print(f"  [{i}] {name} ({case_no}) - {court} {date} (ID: {prec_id})")
    return result


async def test_get_precedent_detail(client: LawAPIClient, prec_id: str, case_name: str):
    """5. get_precedent_detail - 판례 본문 조회"""
    print("\n" + "=" * 60)
    print(f"[5/8] get_precedent_detail - {case_name} (ID: {prec_id})")
    print("=" * 60)
    result = await client.get_detail("prec", ID=prec_id)
    for key in ("사건번호", "사건명", "선고일자", "법원명", "판결유형"):
        val = result.get(key, "")
        if val:
            print(f"  {key}: {val}")

    for key in ("판시사항", "판결요지"):
        val = result.get(key, "")
        if val:
            # HTML 태그 제거
            text = str(val).replace("<br/>", "\n").replace("<br>", "\n")[:200]
            print(f"  {key} (발췌): {text}...")

    refs = result.get("참조조문", "")
    if refs:
        print(f"  참조조문: {str(refs)[:150]}...")
    return result


async def test_search_interpretation(client: LawAPIClient):
    """6. search_interpretation - 법령해석례 검색"""
    print("\n" + "=" * 60)
    print("[6/8] search_interpretation - '개인정보' 검색")
    print("=" * 60)
    result = await client.search("expc", query="개인정보", display=3)
    print(f"  총 결과: {result['totalCnt']}건")
    for i, item in enumerate(result["items"][:3], 1):
        title = item.get("안건명", "?")
        expc_id = item.get("법령해석례일련번호", "?")
        date = item.get("회신일자", "?")
        print(f"  [{i}] {title[:60]}... (ID: {expc_id}, {date})")
    return result


async def test_get_interpretation_detail(client: LawAPIClient, expc_id: str):
    """7. get_interpretation_detail - 법령해석례 본문 조회"""
    print("\n" + "=" * 60)
    print(f"[7/8] get_interpretation_detail - ID: {expc_id}")
    print("=" * 60)
    result = await client.get_detail("expc", ID=expc_id)
    for key in ("안건번호", "안건명", "해석일자", "해석기관명", "질의기관명"):
        val = result.get(key, "")
        if val:
            print(f"  {key}: {val}")

    for key in ("질의요지", "회답", "이유"):
        val = result.get(key, "")
        if val:
            text = str(val).strip()[:200]
            print(f"  {key} (발췌): {text}...")
    return result


async def test_search_admin_rule(client: LawAPIClient):
    """8. search_admin_rule - 행정규칙 검색"""
    print("\n" + "=" * 60)
    print("[8/9] search_admin_rule - '개인정보' 검색")
    print("=" * 60)
    result = await client.search("admrul", query="개인정보", display=3)
    print(f"  총 결과: {result['totalCnt']}건")
    for i, item in enumerate(result["items"][:3], 1):
        name = item.get("행정규칙명", "?")
        kind = item.get("행정규칙종류", "")
        rule_id = item.get("행정규칙일련번호", "?")
        dept = item.get("소관부처명", "?")
        print(f"  [{i}] {name} ({kind}) - {dept} (ID: {rule_id})")
    return result


async def test_get_admin_rule_detail(client: LawAPIClient, rule_id: str, rule_name: str):
    """9. get_admin_rule_detail - 행정규칙 본문 조회"""
    print("\n" + "=" * 60)
    print(f"[9/9] get_admin_rule_detail - {rule_name} (ID: {rule_id})")
    print("=" * 60)
    result = await client.get_detail("admrul", ID=rule_id)
    for key in ("행정규칙명", "발령일자", "소관부처명", "행정규칙종류"):
        val = result.get(key, "")
        if val:
            print(f"  {key}: {val}")
    # 본문 내용 일부 출력
    for key in ("본문", "내용", "규칙내용"):
        val = result.get(key, "")
        if val:
            text = str(val).strip()[:200]
            print(f"  {key} (발췌): {text}...")
            break
    keys = list(result.keys())
    print(f"  반환 필드: {keys[:10]}")
    return result


async def main():
    print("=" * 60)
    print("  kr-law-mcp 통합 테스트")
    print("  국가법령정보센터 오픈 API 9개 도구 검증")
    print("=" * 60)

    client = LawAPIClient()
    print(f"  API 키(OC): {client.oc}")

    passed = 0
    failed = 0
    errors = []

    # 1. 법령 검색
    try:
        law_result = await test_search_law(client)
        passed += 1
        law_id = None
        law_name = ""
        if law_result["items"]:
            item = law_result["items"][0]
            law_id = item.get("법령일련번호")
            law_name = item.get("법령명한글", "")
    except Exception as e:
        failed += 1
        errors.append(f"search_law: {e}")
        law_id = None
        law_name = ""
        print(f"  ERROR: {e}")

    # 2. 법령 조문 조회
    if law_id:
        try:
            await test_get_law_detail(client, law_id, law_name)
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"get_law_detail: {e}")
            print(f"  ERROR: {e}")

        # 3. 법령 연혁 조회
        try:
            await test_get_law_history(client, law_id, law_name)
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"get_law_history: {e}")
            print(f"  ERROR: {e}")
    else:
        print("\n  [SKIP] 법령 조문/연혁 조회 - 법령 ID 없음")
        failed += 2

    # 4. 판례 검색
    try:
        prec_result = await test_search_precedent(client)
        passed += 1
        prec_id = None
        case_name = ""
        if prec_result["items"]:
            item = prec_result["items"][0]
            prec_id = item.get("판례일련번호")
            case_name = item.get("사건명", "")
    except Exception as e:
        failed += 1
        errors.append(f"search_precedent: {e}")
        prec_id = None
        case_name = ""
        print(f"  ERROR: {e}")

    # 5. 판례 본문 조회
    if prec_id:
        try:
            await test_get_precedent_detail(client, prec_id, case_name)
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"get_precedent_detail: {e}")
            print(f"  ERROR: {e}")
    else:
        print("\n  [SKIP] 판례 본문 조회 - 판례 ID 없음")
        failed += 1

    # 6. 법령해석례 검색
    try:
        expc_result = await test_search_interpretation(client)
        passed += 1
        expc_id = None
        if expc_result["items"]:
            item = expc_result["items"][0]
            expc_id = item.get("법령해석례일련번호")
    except Exception as e:
        failed += 1
        errors.append(f"search_interpretation: {e}")
        expc_id = None
        print(f"  ERROR: {e}")

    # 7. 법령해석례 본문 조회
    if expc_id:
        try:
            await test_get_interpretation_detail(client, expc_id)
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"get_interpretation_detail: {e}")
            print(f"  ERROR: {e}")
    else:
        print("\n  [SKIP] 해석례 본문 조회 - 해석례 ID 없음")
        failed += 1

    # 8. 행정규칙 검색
    try:
        admin_rule_result = await test_search_admin_rule(client)
        passed += 1
        rule_id = None
        rule_name = ""
        if admin_rule_result["items"]:
            item = admin_rule_result["items"][0]
            rule_id = item.get("행정규칙일련번호")
            rule_name = item.get("행정규칙명", "")
    except Exception as e:
        failed += 1
        errors.append(f"search_admin_rule: {e}")
        rule_id = None
        rule_name = ""
        print(f"  ERROR: {e}")

    # 9. 행정규칙 본문 조회
    if rule_id:
        try:
            await test_get_admin_rule_detail(client, rule_id, rule_name)
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"get_admin_rule_detail: {e}")
            print(f"  ERROR: {e}")
    else:
        print("\n  [SKIP] 행정규칙 본문 조회 - 행정규칙 ID 없음")
        failed += 1

    # 결과 요약
    print("\n" + "=" * 60)
    print(f"  테스트 결과: {passed}/9 성공, {failed}/9 실패")
    print("=" * 60)
    if errors:
        print("  실패 목록:")
        for err in errors:
            print(f"    - {err}")
    else:
        print("  모든 도구가 정상 작동합니다!")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
