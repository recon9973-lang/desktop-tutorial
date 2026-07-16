// LLM 문장 다듬기 연결 지점 (2단계).
// MVP는 결정론적 룰 엔진 문장을 그대로 사용한다. ANTHROPIC_API_KEY가 설정되면
// 아래에서 Claude API를 호출해 문장을 더 자연스럽게 다듬도록 확장할 수 있다.
//
// 예시(구현 시):
//   const res = await fetch("https://api.anthropic.com/v1/messages", {
//     method: "POST",
//     headers: { "x-api-key": process.env.ANTHROPIC_API_KEY!, "anthropic-version": "2023-06-01", "content-type": "application/json" },
//     body: JSON.stringify({ model: "claude-haiku-4-5-20251001", max_tokens: 800,
//       messages: [{ role: "user", content: `다음 리포트를 대표에게 보고하듯 자연스러운 한국어로 다듬어줘. 수치는 바꾸지 마:\n\n${text}` }] }),
//   });
//
// 주의: 룰 엔진이 만든 수치·판단은 신뢰 근거이므로 LLM이 수치를 바꾸지 않도록 프롬프트로 고정할 것.

export async function polishKorean(text: string): Promise<string> {
  if (!process.env.ANTHROPIC_API_KEY) return text; // 키 없으면 원문 사용 (MVP 기본)
  return text; // TODO: 위 예시대로 Claude 호출 연결
}
