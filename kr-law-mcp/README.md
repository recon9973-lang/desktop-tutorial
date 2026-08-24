# kr-law-mcp

국가법령정보센터(law.go.kr) 오픈 API를 활용한 MCP 서버입니다.
Claude에서 한국 법령, 판례, 법령해석례, 행정규칙을 자연어로 검색하고 본문을 조회할 수 있습니다.

> **기존 130개 도구 MCP 서버 대비 장점**: 한국 법령 조회에 특화된 9개 도구만 포함하여 Claude가 올바른 도구를 선택하기 쉽고, 각 도구의 description에 사용 맥락과 주의사항이 상세히 기술되어 있습니다.

---

## 도구 목록

| 도구명 | 설명 |
|--------|------|
| `search_law` | 법령(법률·대통령령·총리령·부령) 키워드 검색 |
| `get_law_detail` | 특정 법령의 전체 조문 또는 특정 조문 조회 |
| `get_law_history` | 특정 법령의 제정·개정 이력 및 제개정이유 조회 |
| `search_precedent` | 판례(대법원·하급심) 키워드 검색 |
| `get_precedent_detail` | 특정 판례의 전문(판시사항·판결요지·판례내용) 조회 |
| `search_interpretation` | 법제처 법령해석례 키워드 검색 |
| `get_interpretation_detail` | 특정 법령해석례의 전문(질의요지·회답·이유) 조회 |
| `search_admin_rule` | 행정규칙(훈령·예규·고시) 키워드 검색 |
| `get_admin_rule_detail` | 특정 행정규칙의 본문 조회 |

---

## 설치 방법

### Step 1: 국가법령정보 오픈 API 신청

[국가법령정보센터 오픈 API](https://www.law.go.kr/LSW/openApiInfo.do) 페이지에서 이메일 ID로 API를 신청합니다.
신청 후 발급받은 이메일 ID(OC)를 `LAW_API_OC` 환경변수로 사용합니다.

### Step 2: 저장소 설치

```bash
git clone https://github.com/dikehomme/kr-law-mcp.git
cd kr-law-mcp
pip install -e .
```

또는 [uv](https://github.com/astral-sh/uv) 사용:

```bash
git clone https://github.com/dikehomme/kr-law-mcp.git
cd kr-law-mcp
uv sync
```

### Step 3: 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키를 입력합니다:

```
LAW_API_OC=your_email_id
```

### Step 4: Claude Desktop 등록

`claude_desktop_config.json`에 아래 내용을 추가합니다:

```json
{
  "mcpServers": {
    "kr-law": {
      "command": "uv",
      "args": ["--directory", "/path/to/kr-law-mcp", "run", "python", "-m", "kr_law_mcp.server"],
      "env": {
        "LAW_API_OC": "your_email_id"
      }
    }
  }
}
```

`/path/to/kr-law-mcp`를 실제 설치 경로로 변경하세요.

---

## 사용 예시

아래는 Claude에서 직접 사용할 수 있는 프롬프트 예시입니다.

**법령 검색 및 조문 조회**
```
개인정보보호법 제15조(개인정보의 수집·이용)를 보여줘.
```

**판례 검색**
```
손해배상 관련 최근 대법원 판례를 5건 찾아줘.
```

**법령해석례 조회**
```
법령해석례에서 '청약철회' 관련 사례를 찾아 요약해줘.
```

**행정규칙 본문 조회**
```
개인정보 관련 행정안전부 훈령을 검색하고 본문을 보여줘.
```

**법령 개정 이력 확인**
```
민법의 최근 개정 이력과 개정 이유를 알려줘.
```

---

## 주의사항

1. **단일 키워드 사용**: 검색 도구는 한 단어씩 검색하세요.
   복합 키워드(예: `전자상거래 청약철회`)는 0건이 반환될 수 있습니다.
   핵심 단어 하나(예: `청약철회`)로 검색 후 결과에서 필터링하세요.

2. **법령일련번호 vs 법령ID**: `get_law_detail` · `get_law_history`에는
   `법령ID` 필드가 아닌 **`법령일련번호`** 필드 값을 사용해야 합니다.

3. **API 키 설정**: `.env` 파일에 `LAW_API_OC`를 반드시 설정해야 합니다.
   키가 없으면 서버가 시작되지 않습니다.

4. **API 호출 제한**: 국가법령정보센터 오픈 API의 호출 정책을 준수하세요.

---

## 프로젝트 구조

```
kr-law-mcp/
├── src/
│   └── kr_law_mcp/
│       ├── __init__.py
│       ├── __main__.py       # python -m kr_law_mcp 진입점
│       ├── server.py         # FastMCP 서버 + 9개 도구 등록
│       ├── api_client.py     # 국가법령정보 API 비동기 클라이언트
│       ├── xml_parser.py     # XML 응답 파싱 유틸리티
│       └── config.py         # 환경변수 및 상수 설정
├── tests/                    # 단위 테스트 디렉토리
├── test_all_tools.py         # 9개 도구 통합 테스트 스크립트
├── .env.example              # 환경변수 템플릿
├── pyproject.toml
└── README.md
```

---

## 라이선스

MIT License
