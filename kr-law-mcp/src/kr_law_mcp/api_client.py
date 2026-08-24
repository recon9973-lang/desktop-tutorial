"""국가법령정보 API 호출 클래스"""

import httpx
from typing import Any

from .config import (
    LAW_API_OC,
    LAW_API_BASE_SEARCH,
    LAW_API_BASE_SERVICE,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
)
from .xml_parser import parse_search_results, parse_service_response


class LawAPIClient:
    """국가법령정보센터 오픈 API 비동기 클라이언트"""

    def __init__(self, oc: str | None = None):
        self.oc = oc or LAW_API_OC
        if not self.oc:
            raise ValueError(
                "API 키(OC)가 설정되지 않았습니다. "
                ".env 파일에 LAW_API_OC를 설정하세요."
            )

    async def _request(self, url: str, params: dict) -> str:
        """HTTP GET 요청을 보내고 응답 텍스트를 반환한다. 최대 MAX_RETRIES회 재시도."""
        params["OC"] = self.oc
        params["type"] = "XML"

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    return resp.text
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    continue
        raise ConnectionError(
            f"API 호출 실패 ({MAX_RETRIES}회 재시도 후): {last_error}"
        )

    async def search(self, target: str, **kwargs) -> dict[str, Any]:
        """목록 검색 API (lawSearch.do)를 호출한다.

        Args:
            target: 검색 대상 (law, prec, expc, admrul)
            **kwargs: query, page, display, sort, search 등
        """
        params = {"target": target}
        for k, v in kwargs.items():
            if v is not None:
                params[k] = v

        xml_text = await self._request(LAW_API_BASE_SEARCH, params)
        return parse_search_results(xml_text)

    async def get_detail(self, target: str, **kwargs) -> dict[str, Any]:
        """단건 조회 API (lawService.do)를 호출한다.

        Args:
            target: 조회 대상 (law, prec, expc, admrul)
            **kwargs: ID, MST 등
        """
        params = {"target": target}
        for k, v in kwargs.items():
            if v is not None:
                params[k] = v

        xml_text = await self._request(LAW_API_BASE_SERVICE, params)
        return parse_service_response(xml_text)
