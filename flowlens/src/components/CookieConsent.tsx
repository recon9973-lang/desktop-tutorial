"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

// 쿠키/행태정보 동의 배너(CMP). 선택을 localStorage에 저장하고, 저장 전까지만 노출.
// 개인정보 보호가 브랜드 핵심이므로 기본은 '거부(필수만)'가 쉬운 선택이 되도록 구성.
export default function CookieConsent() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem("fl_consent")) setShow(true);
    } catch {
      /* 무시 */
    }
  }, []);

  function decide(value: "all" | "essential") {
    try {
      localStorage.setItem("fl_consent", value);
    } catch {}
    setShow(false);
  }

  if (!show) return null;

  return (
    <div className="cmp" role="dialog" aria-label="쿠키 동의">
      <div className="cmp-inner">
        <p>
          FlowLens는 서비스 제공과 사용성 개선을 위해 최소한의 쿠키/행태정보를 사용합니다. 자세한 내용은{" "}
          <Link href="/privacy" style={{ color: "var(--accent)", fontWeight: 600 }}>개인정보처리방침</Link>을 확인하세요.
        </p>
        <div className="row">
          <button className="btn sm" type="button" onClick={() => decide("essential")}>필수만 허용</button>
          <button className="btn primary sm" type="button" onClick={() => decide("all")}>모두 동의</button>
        </div>
      </div>
    </div>
  );
}
