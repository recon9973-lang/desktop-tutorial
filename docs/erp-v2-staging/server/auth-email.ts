// 목표: src/server/auth.ts 를 이메일 인증 방식으로 조정 (참고 구현).
// 기존 Kakao provider 대체 → 이메일 매직링크(인증메일) 가입/로그인.
// next-auth v5(beta) + @auth/prisma-adapter 기준.
//
// 필요 env: AUTH_SECRET, DATABASE_URL, EMAIL_SERVER(SMTP), EMAIL_FROM
// 예) EMAIL_SERVER="smtp://user:pass@smtp.example.com:587"  EMAIL_FROM="no-reply@venom.co.kr"
//
// ⚠️ 직원 전용: 사전 등록/초대된 이메일만 로그인 허용(signIn 콜백에서 화이트리스트 검사).
import NextAuth from "next-auth";
import Email from "next-auth/providers/nodemailer";
import { PrismaAdapter } from "@auth/prisma-adapter";

import { db } from "@/server/db";
import { UserStatus } from "@/domain/types";
import { recordLogin } from "@/server/tracking";

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(db),
  session: { strategy: "database" },
  providers: [
    Email({
      server: process.env.EMAIL_SERVER,
      from: process.env.EMAIL_FROM
      // maxAge: 기본 24h 매직링크 유효
    })
  ],
  pages: { signIn: "/login" },
  callbacks: {
    /**
     * 직원만 로그인 허용: 사전 등록된 ACTIVE/INVITED 사용자만 통과.
     * (초대는 관리자가 User를 INVITED로 생성 → 첫 로그인 시 ACTIVE 전환)
     */
    async signIn({ user }) {
      const email = user?.email?.trim().toLowerCase();
      if (!email) return false;
      const staff = await db.user.findFirst({
        where: { email, status: { in: [UserStatus.ACTIVE, UserStatus.INVITED] } },
        select: { id: true, status: true }
      });
      if (!staff) return false; // 미등록 이메일 차단
      if (staff.status === UserStatus.INVITED) {
        await db.user.update({ where: { id: staff.id }, data: { status: UserStatus.ACTIVE } });
      }
      return true;
    }
  },
  events: {
    async signIn({ user }) {
      if (user?.id) {
        try {
          await recordLogin({ userId: user.id, success: true });
        } catch {
          /* 로그인 이력 실패는 로그인 자체를 막지 않음 */
        }
      }
    }
  }
});
