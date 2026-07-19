// 자동 생성 본문의 "콘텐츠 오류"(깨짐·잘림·구분자 잔존·빈 태그·가짜 전화번호)를 정리·검수.
// venom content-validator.js 이식.

const REPLACEMENT_CHAR = "�"; // � (멀티바이트 깨짐)
const DELIMITER_RE = /<{2,3}\s*(TITLE|SEO|META|KEYWORDS|HTML|END)\s*>{2,3}/gi;

export type ContentError = { type: string; severity: "block" | "warn"; msg: string };

export function cleanContent(html: string): string {
  if (!html || typeof html !== "string") return "";
  let out = html;
  out = out.replace(DELIMITER_RE, "");
  out = out.replace(/<script\b(?![^>]*application\/ld\+json)[^>]*>[\s\S]*?<\/script>/gi, "");
  out = out.replace(new RegExp(REPLACEMENT_CHAR + "+", "g"), "");
  for (let i = 0; i < 3; i++) {
    out = out.replace(/<(p|h1|h2|h3|h4|li|strong|em|span)>\s*<\/\1>/gi, "");
  }
  // 가짜 전화번호 제거 (GPT 환각 방지)
  out = out.replace(
    /(전화|연락처|문의(?:전화)?|상담전화|대표번호|고객센터|Tel\.?|TEL\.?|tel\.?)\s*[:：]?\s*(?:\+?82[-\s]?)?(?:0\d{1,2}|01\d)[-\s.]?\d{3,4}[-\s.]?\d{4}/g,
    ""
  );
  out = out.replace(/(?:\+?82[-\s]?)?0\d{1,2}[-\s.]\d{3,4}[-\s.]\d{4}/g, "");
  out = out.replace(/\b1[5-9]\d{2}[-\s.]?\d{4}\b/g, "");
  out = out.replace(/(전화|연락처|Tel\.?|TEL)\s*[:：]\s*(?=[<\s])/g, "");
  out = out.replace(/[ \t]{2,}/g, " ").replace(/\n{3,}/g, "\n\n");
  return out.trim();
}

export function detectContentErrors(html: string): ContentError[] {
  const errors: ContentError[] = [];
  const text = String(html || "");
  const plain = text.replace(/<[^>]+>/g, "").trim();

  if (text.includes(REPLACEMENT_CHAR)) {
    errors.push({ type: "encoding", severity: "block", msg: "깨진 문자(�)가 포함되어 있습니다." });
  }
  if (DELIMITER_RE.test(text)) {
    errors.push({ type: "delimiter", severity: "block", msg: "출력 구분자(<<<...>>>)가 본문에 남아있습니다." });
    DELIMITER_RE.lastIndex = 0;
  }
  if (plain.length < 800) {
    errors.push({ type: "too-short", severity: "block", msg: `본문이 너무 짧습니다(${plain.length}자).` });
  }
  if (text && !/(<\/[a-z0-9]+>|\/>)\s*$/i.test(text)) {
    errors.push({ type: "truncated", severity: "block", msg: "본문이 닫는 태그로 끝나지 않습니다(생성 중 잘림 의심)." });
  }
  for (const tag of ["h2", "h3", "table", "ul", "ol", "figure"]) {
    const open = (text.match(new RegExp("<" + tag + "\\b", "gi")) || []).length;
    const close = (text.match(new RegExp("</" + tag + ">", "gi")) || []).length;
    if (open !== close) {
      errors.push({ type: "broken-html", severity: "warn", msg: `<${tag}> 태그 짝이 맞지 않습니다(${open}/${close}).` });
    }
  }
  return errors;
}

export function reviewContent(html: string): { cleaned: string; errors: ContentError[]; hasBlockingErrors: boolean } {
  const hadReplacement = String(html || "").includes(REPLACEMENT_CHAR);
  const cleaned = cleanContent(html);
  const errors = detectContentErrors(cleaned);
  if (hadReplacement) {
    errors.unshift({
      type: "encoding",
      severity: "block",
      msg: "깨진 문자(�)로 일부 내용이 소실되었습니다. 자동 발행하지 않고 재생성/검수가 필요합니다.",
    });
  }
  return { cleaned, errors, hasBlockingErrors: errors.some((e) => e.severity === "block") };
}
