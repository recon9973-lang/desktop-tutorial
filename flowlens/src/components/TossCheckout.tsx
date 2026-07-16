"use client";

import { useEffect, useRef, useState } from "react";

// 토스페이먼츠 결제위젯(v2)을 로드해 결제 수단 선택 + 결제 요청을 처리한다.
declare global {
  interface Window {
    TossPayments?: (clientKey: string) => {
      widgets: (opts: { customerKey: string }) => {
        setAmount: (a: { currency: string; value: number }) => Promise<void>;
        renderPaymentMethods: (o: { selector: string; variantKey?: string }) => Promise<void>;
        renderAgreement: (o: { selector: string }) => Promise<void>;
        requestPayment: (o: { orderId: string; orderName: string; successUrl: string; failUrl: string }) => Promise<void>;
      };
    };
  }
}

export default function TossCheckout({
  clientKey,
  customerKey,
  amount,
  orderId,
  orderName,
  planKey,
}: {
  clientKey: string;
  customerKey: string;
  amount: number;
  orderId: string;
  orderName: string;
  planKey: string;
}) {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const widgetsRef = useRef<ReturnType<NonNullable<Window["TossPayments"]>>["widgets"] extends never ? unknown : any>(null);

  useEffect(() => {
    if (!clientKey) {
      setError("결제 키가 설정되지 않았습니다.");
      return;
    }
    let cancelled = false;

    function init() {
      if (cancelled || !window.TossPayments) return;
      try {
        const toss = window.TossPayments(clientKey);
        const widgets = toss.widgets({ customerKey });
        widgetsRef.current = widgets;
        widgets.setAmount({ currency: "KRW", value: amount }).then(async () => {
          await widgets.renderPaymentMethods({ selector: "#payment-method" });
          await widgets.renderAgreement({ selector: "#agreement" });
          if (!cancelled) setReady(true);
        });
      } catch (e) {
        setError("결제 위젯 초기화 실패");
      }
    }

    if (window.TossPayments) {
      init();
    } else {
      const s = document.createElement("script");
      s.src = "https://js.tosspayments.com/v2/standard";
      s.onload = init;
      s.onerror = () => setError("토스페이먼츠 SDK 로드 실패 (네트워크 확인)");
      document.head.appendChild(s);
    }
    return () => {
      cancelled = true;
    };
  }, [clientKey, customerKey, amount]);

  async function pay() {
    const widgets = widgetsRef.current;
    if (!widgets) return;
    const origin = window.location.origin;
    try {
      await widgets.requestPayment({
        orderId,
        orderName,
        successUrl: `${origin}/billing/success?plan=${planKey}`,
        failUrl: `${origin}/billing/fail`,
      });
    } catch (e) {
      setError("결제 요청 중 오류가 발생했습니다.");
    }
  }

  if (error) {
    return <div className="notice" style={{ background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c" }}>{error}</div>;
  }

  return (
    <div>
      <div id="payment-method" />
      <div id="agreement" />
      <button className="btn primary" onClick={pay} disabled={!ready} style={{ width: "100%", justifyContent: "center", marginTop: 16 }}>
        {ready ? `${amount.toLocaleString()}원 결제하기` : "결제 수단 불러오는 중…"}
      </button>
    </div>
  );
}
