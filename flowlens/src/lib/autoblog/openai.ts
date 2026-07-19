// OpenAI Chat Completions 호출 (fetch 기반). venom 엔진 openai-client.js 이식.
// OPENAI_API_KEY 필수. 모델은 OPENAI_TEXT_MODEL(기본 gpt-4o-mini).

type ChatOpts = { model?: string; temperature?: number; max_tokens?: number };
type Usage = { prompt_tokens: number; completion_tokens: number; total_tokens: number };

export async function chatComplete(
  systemPrompt: string,
  userPrompt: string,
  opts: ChatOpts = {}
): Promise<{ text: string; usage: Usage }> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY 환경변수가 없습니다. Vercel(또는 .env.local)에 설정하세요.");

  const model = opts.model || process.env.OPENAI_TEXT_MODEL || "gpt-4o-mini";
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model,
      temperature: opts.temperature ?? 0.7,
      max_tokens: opts.max_tokens ?? 2000,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
    }),
  });

  const json = await res.json();
  if (json.error) throw new Error(json.error.message || "OpenAI API 오류");
  const choice = json.choices?.[0]?.message?.content;
  if (typeof choice !== "string") throw new Error("OpenAI 응답 형식 오류");
  return {
    text: choice.trim(),
    usage: json.usage ?? { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
  };
}
