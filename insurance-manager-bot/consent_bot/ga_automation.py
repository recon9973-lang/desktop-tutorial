"""프로젝트 ① — 신한라이프 GA 웹 자동화 (Playwright).

원칙(§4.2, §6.2):
- 로그인·간편비밀번호는 사용자가 직접 수행(봇 제외). 셔플 키패드 자동클릭 금지.
- 로그인 완료 후 사용자가 콘솔에서 Enter → 봇이 이후 단계 자동화.
- 좌표 클릭보다 HTML 셀렉터 우선. UI 변경 감지 시 즉시 사용자 이관.

주의: 아래 SELECTORS는 실제 GA 화면에서 1회 캘리브레이션이 필요하다(placeholder).
      운영 사이트 접근 권한 하에서 개발자도구로 확정한 뒤 채운다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

GA_URL = "https://ga.shinhanlife.co.kr"

# TODO(캘리브레이션): 실제 GA 화면에서 확정. 현재는 구조 예시(placeholder).
SELECTORS = {
    "menu_customer": "text=고객관리",
    "menu_consign_consent": "text=위탁가입설계동의",
    "search_code_input": "input[name='custCode']",
    "search_button": "button:has-text('검색')",
    "new_consent_button": "text=신규가입설계동의",
    "written_consent_option": "text=서면동의",
    "birth_input": "input[name='birthDate']",
    "confirm_button": "button:has-text('확인')",
    "print_button": "button:has-text('인쇄')",
}


@dataclass
class GAContext:
    download_dir: Path
    headless: bool = False   # 사용자가 로그인해야 하므로 기본 headful


class GAConsentAutomation:
    """로그인 이후 동의서 생성·저장 단계를 자동화. 각 단계는 재시도 가능."""

    def __init__(self, ctx: GAContext):
        self.ctx = ctx
        self._pw = None
        self._browser = None
        self.page = None

    # --- 세션 수명주기 ---------------------------------------------------
    def open(self):
        from playwright.sync_api import sync_playwright  # 지연 import
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.ctx.headless)
        context = self._browser.new_context(accept_downloads=True)
        self.page = context.new_page()
        self.page.goto(GA_URL)
        return self.page

    def wait_manual_login(self, prompt_fn=input):
        """사용자가 로그인 + 간편비밀번호까지 직접 완료하도록 대기(휴먼 게이트)."""
        prompt_fn("\n[사용자 작업] GA 로그인 + 간편비밀번호 입력을 완료한 뒤 Enter: ")
        # 로그인 성공 판정: 고객관리 메뉴 노출 여부
        return self._assert_visible("menu_customer", "로그인 확인 실패 — 재로그인 필요")

    # --- 업무 단계(로그인 이후) -----------------------------------------
    def go_customer_management(self):
        self.page.click(SELECTORS["menu_customer"])
        self.page.click(SELECTORS["menu_consign_consent"])
        return self._assert_visible("search_code_input", "고객관리 화면 진입 실패")

    def search_customer(self, code: str) -> int:
        """코드로 검색. 반환: 후보 수(0=없음, 1=단일, 2+=동명이인 → 사용자 확인)."""
        self.page.fill(SELECTORS["search_code_input"], code)
        self.page.click(SELECTORS["search_button"])
        self.page.wait_for_load_state("networkidle")
        rows = self.page.locator("table tbody tr")  # TODO: 실제 결과 테이블 셀렉터
        return rows.count()

    def pick_customer_row(self, index: int):
        """동명이인 시 사용자가 고른 index 행 선택."""
        self.page.locator("table tbody tr").nth(index).click()

    def create_written_consent(self, birthdate_yyyymmdd: str) -> Path:
        """신규가입설계동의(서면동의) 생성 → 생년월일 입력 → 인쇄/저장(PDF 다운로드)."""
        self.page.click(SELECTORS["new_consent_button"])
        self.page.click(SELECTORS["written_consent_option"])
        self.page.fill(SELECTORS["birth_input"], birthdate_yyyymmdd)
        self.page.click(SELECTORS["confirm_button"])
        self.page.click(SELECTORS["confirm_button"])  # 원본 절차상 '확인' 2회
        with self.page.expect_download() as dl_info:
            self.page.click(SELECTORS["print_button"])
        download = dl_info.value
        target = self.ctx.download_dir / "원본_동의서.pdf"
        download.save_as(str(target))
        return target

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    # --- 내부 유틸 -------------------------------------------------------
    def _assert_visible(self, key: str, err: str) -> bool:
        try:
            self.page.wait_for_selector(SELECTORS[key], timeout=15000)
            return True
        except Exception as e:  # UI 변경/세션 만료 → 사용자 이관
            raise RuntimeError(f"{err}: {e}") from e
