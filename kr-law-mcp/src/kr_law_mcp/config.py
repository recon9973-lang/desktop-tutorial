"""설정 로드 (.env 파일에서 API 키 등 관리)"""

import os
from dotenv import load_dotenv

load_dotenv()

LAW_API_OC = os.getenv("LAW_API_OC", "")
LAW_API_BASE_SEARCH = "https://www.law.go.kr/DRF/lawSearch.do"
LAW_API_BASE_SERVICE = "https://www.law.go.kr/DRF/lawService.do"

# HTTP 클라이언트 설정
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
