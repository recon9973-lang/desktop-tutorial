// 목표 경로: src/server/crypto.ts
//
// 거래처 채널계정 자격증명(아이디/비밀번호) 대칭 암호화.
// AES-256-GCM. 키는 환경변수 CREDENTIAL_ENC_KEY (32바이트 = base64 44자 또는 hex 64자).
// 저장형식: v1:<iv_b64>:<authTag_b64>:<cipher_b64>  (버전 프리픽스로 향후 키 로테이션 대비)
//
// ⚠️ 평문을 로그/응답/에러메시지에 절대 남기지 말 것. 열람은 반드시 감사기록(recordAudit).
import { createCipheriv, createDecipheriv, randomBytes } from "crypto";

const VERSION = "v1";
const ALGO = "aes-256-gcm";
const IV_BYTES = 12; // GCM 권장 IV 길이

function getKey(): Buffer {
  const raw = process.env.CREDENTIAL_ENC_KEY;
  if (!raw) {
    throw new Error("CREDENTIAL_ENC_KEY_MISSING");
  }
  // hex(64) 또는 base64(=32바이트) 허용
  const key = /^[0-9a-fA-F]{64}$/.test(raw)
    ? Buffer.from(raw, "hex")
    : Buffer.from(raw, "base64");
  if (key.length !== 32) {
    throw new Error("CREDENTIAL_ENC_KEY_INVALID_LENGTH"); // 32바이트 필요
  }
  return key;
}

/** 평문 → 저장용 암호문 문자열. 빈값/undefined는 그대로 null 반환. */
export function encryptSecret(plain: string | null | undefined): string | null {
  if (plain == null || plain === "") return null;
  const key = getKey();
  const iv = randomBytes(IV_BYTES);
  const cipher = createCipheriv(ALGO, key, iv);
  const enc = Buffer.concat([cipher.update(plain, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return `${VERSION}:${iv.toString("base64")}:${tag.toString("base64")}:${enc.toString("base64")}`;
}

/** 저장용 암호문 → 평문. 위·변조 시 throw. */
export function decryptSecret(stored: string | null | undefined): string | null {
  if (stored == null || stored === "") return null;
  const parts = stored.split(":");
  if (parts.length !== 4 || parts[0] !== VERSION) {
    throw new Error("CREDENTIAL_FORMAT_INVALID");
  }
  const [, ivB64, tagB64, dataB64] = parts;
  const key = getKey();
  const decipher = createDecipheriv(ALGO, key, Buffer.from(ivB64, "base64"));
  decipher.setAuthTag(Buffer.from(tagB64, "base64"));
  const dec = Buffer.concat([
    decipher.update(Buffer.from(dataB64, "base64")),
    decipher.final()
  ]);
  return dec.toString("utf8");
}

/** UI 표시용 마스킹 (열람 전 기본 표시). 예: "abcd1234" → "ab****34" */
export function maskSecret(plain: string | null | undefined): string {
  if (!plain) return "";
  if (plain.length <= 4) return "*".repeat(plain.length);
  return `${plain.slice(0, 2)}${"*".repeat(Math.max(2, plain.length - 4))}${plain.slice(-2)}`;
}
