// 팝업: 설정 저장 후 현재 탭에 오버레이 콘텐츠 스크립트를 주입/토글한다.
const $ = (id) => document.getElementById(id);

// 저장된 설정 불러오기
chrome.storage.local.get(["origin", "siteKey", "token", "gesture", "mode", "period"], (c) => {
  if (c.origin) $("origin").value = c.origin;
  if (c.siteKey) $("siteKey").value = c.siteKey;
  if (c.token) $("token").value = c.token;
  if (c.gesture) $("gesture").value = c.gesture;
  if (c.mode) $("mode").value = c.mode;
  if (c.period) $("period").value = c.period;
});

$("toggle").addEventListener("click", async () => {
  const origin = $("origin").value.trim().replace(/\/$/, "");
  const siteKey = $("siteKey").value.trim();
  const token = $("token").value.trim();
  const gesture = $("gesture").value;
  const mode = $("mode").value;
  const period = $("period").value;
  if (!origin || !siteKey || !token) {
    $("status").textContent = "FlowLens 주소 · 사이트 키 · 오버레이 토큰을 모두 입력하세요.";
    return;
  }
  await chrome.storage.local.set({ origin, siteKey, token, gesture, mode, period });

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;

  $("status").textContent = "불러오는 중…";
  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
    const res = await chrome.tabs.sendMessage(tab.id, { type: "FL_TOGGLE", origin, siteKey, token, gesture, mode, period });
    if (res?.on) $("status").textContent = mode === "scroll" ? "스크롤맵 표시 중" : `히트맵 표시 중 · 클릭 ${res.count ?? 0}개`;
    else $("status").textContent = "표시를 껐습니다.";
  } catch (e) {
    $("status").textContent = "이 페이지에서는 실행할 수 없습니다(브라우저 내부 페이지 등).";
  }
});
