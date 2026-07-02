// 목표 경로: tests/server/crypto.test.ts
import { describe, it, expect, beforeAll } from "vitest";
import { encryptSecret, decryptSecret, maskSecret } from "@/server/crypto";

beforeAll(() => {
  // 테스트용 32바이트 키(hex 64자)
  process.env.CREDENTIAL_ENC_KEY = "0".repeat(64);
});

describe("crypto (자격증명 암호화)", () => {
  it("암호화→복호화 라운드트립", () => {
    const plain = "myS3cret!한글비번";
    const enc = encryptSecret(plain);
    expect(enc).toBeTruthy();
    expect(enc).not.toContain(plain); // 평문 노출 없음
    expect(decryptSecret(enc)).toBe(plain);
  });

  it("빈값/null은 null 반환", () => {
    expect(encryptSecret("")).toBeNull();
    expect(encryptSecret(null)).toBeNull();
    expect(decryptSecret(null)).toBeNull();
  });

  it("동일 평문도 매번 다른 암호문(IV 랜덤)", () => {
    expect(encryptSecret("same")).not.toBe(encryptSecret("same"));
  });

  it("변조된 암호문은 복호화 실패", () => {
    const enc = encryptSecret("data")!;
    const tampered = enc.slice(0, -2) + (enc.endsWith("A") ? "B" : "A");
    expect(() => decryptSecret(tampered)).toThrow();
  });

  it("마스킹", () => {
    expect(maskSecret("abcd1234")).toBe("ab****34");
    expect(maskSecret("ab")).toBe("**");
  });
});
