"""프로젝트 ② — 신한라이프 GA 반자동 로그인 (Playwright).

원칙(기획안_2 §3):
- ID/PW는 OS 보안저장소(keyring)에서 불러와 자동 입력.
- 간편비밀번호는 셔플 키패드 → 자동 클릭 금지, 사용자 직접 입력.
- 무인 실행 금지: 반드시 사용자 세션 하에서.
- 캡차/추가 인증 발생 시 사용자 이관.
"""
from __future__ import annotations

from pathlib import Path

GA_URL = "https://ga.shinhanlife.co.kr"

# TODO(캘리브레이션): 실제 로그인 폼 셀렉터 확정.
SELECTORS = {
    "id_input": "input[name='userId']",
    "pw_input": "input[name='userPw']",
    "login_button": "button:has-text('로그인')",
    "logged_in_marker": "text=고객관리",
}


class GALogin:
    def __init__(self, user_key: str, headless: bool = False):
        self.user_key = user_key
        self.headless = headless
        self._pw = None
        self._browser = None
        self.page = None

    def open(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self.page = self._browser.new_context(accept_downloads=True).new_page()
        self.page.goto(GA_URL)
        return self.page

    def autofill_id_pw(self) -> bool:
        """keyring에서 ID/PW 불러와 자동 입력. 성공 시 True."""
        from common.secure import load_credentials
        login_id, pw = load_credentials(self.user_key)
        if not login_id or not pw:
            return False
        self.page.fill(SELECTORS["id_input"], login_id)
        self.page.fill(SELECTORS["pw_input"], pw)
        return True

    def wait_manual_simple_password(self, prompt_fn=input) -> bool:
        """간편비밀번호는 사용자가 직접 입력(셔플 키패드). 완료 후 Enter."""
        prompt_fn("\n[사용자 작업] 간편비밀번호(보안 키패드)를 직접 입력하고 로그인 완료 후 Enter: ")
        try:
            self.page.wait_for_selector(SELECTORS["logged_in_marker"], timeout=15000)
            return True
        except Exception:
            return False

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
