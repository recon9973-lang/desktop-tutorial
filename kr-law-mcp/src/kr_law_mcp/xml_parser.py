"""XML 응답을 Python dict로 변환하는 유틸리티"""

import xml.etree.ElementTree as ET
from typing import Any


def xml_to_dict(element: ET.Element) -> dict[str, Any]:
    """XML Element를 재귀적으로 dict로 변환한다."""
    result: dict[str, Any] = {}
    for child in element:
        tag = child.tag
        if len(child) > 0:
            value = xml_to_dict(child)
        else:
            value = (child.text or "").strip()
        # 같은 태그가 여러 개면 리스트로
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(value)
        else:
            result[tag] = value
    return result


def parse_xml_response(xml_text: str) -> dict[str, Any]:
    """XML 문자열을 파싱하여 dict로 반환한다."""
    root = ET.fromstring(xml_text)
    return xml_to_dict(root), root.tag


def parse_search_results(xml_text: str) -> dict[str, Any]:
    """검색 API 응답(목록)을 파싱한다.

    Returns:
        {"totalCnt": int, "page": int, "items": [dict, ...]}
    """
    root = ET.fromstring(xml_text)
    total_cnt = 0
    page = 1
    items = []

    # 최상위에서 totalCnt, page 추출
    total_el = root.find("totalCnt")
    if total_el is not None and total_el.text:
        total_cnt = int(total_el.text)
    page_el = root.find("page")
    if page_el is not None and page_el.text:
        page = int(page_el.text)

    # 메타 태그 목록 (검색 결과 항목이 아닌 것들)
    meta_tags = {
        "totalCnt", "page", "target", "키워드", "section",
        "numOfRows", "resultCode", "resultMsg",
    }

    # 각 하위 요소를 item으로 수집 (메타 태그 제외)
    for child in root:
        if child.tag in meta_tags:
            continue
        item = xml_to_dict(child)
        if item:  # 빈 dict 제외
            items.append(item)

    # 각 item에서 target별 ID 필드를 통일된 'id' 키로 추가
    _id_field_map = {
        "법령일련번호": "id",
        "판례일련번호": "id",
        "법령해석례일련번호": "id",
        "행정규칙일련번호": "id",
    }
    for item in items:
        for src_key in _id_field_map:
            if src_key in item:
                item["id"] = item[src_key]
                break

    return {"totalCnt": total_cnt, "page": page, "items": items}


def parse_service_response(xml_text: str) -> dict[str, Any]:
    """단건 조회 API 응답을 파싱한다."""
    root = ET.fromstring(xml_text)
    return xml_to_dict(root)
