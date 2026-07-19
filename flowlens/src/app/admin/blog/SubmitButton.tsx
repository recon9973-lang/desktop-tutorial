"use client";

import { useFormStatus } from "react-dom";

// 폼 제출 중(서버 액션 실행 중)에는 버튼을 "처리 중…"으로 바꾸고 비활성화한다.
// AI 초안 생성처럼 30초~1분 걸리는 동작에 "지금 작동 중"임을 명확히 보여준다.
export function SubmitButton({
  children,
  pending: pendingLabel,
  note,
  className = "btn primary",
}: {
  children: React.ReactNode;
  pending?: string;
  note?: string;
  className?: string;
}) {
  const { pending } = useFormStatus();
  return (
    <>
      <button
        className={className}
        type="submit"
        disabled={pending}
        style={{ opacity: pending ? 0.65 : 1, cursor: pending ? "wait" : "pointer" }}
      >
        {pending ? (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <span className="spin" style={{ width: 14, height: 14, border: "2px solid currentColor", borderTopColor: "transparent", borderRadius: "50%", display: "inline-block" }} />
            {pendingLabel || "처리 중…"}
          </span>
        ) : (
          children
        )}
      </button>
      {pending && note && (
        <p className="small" style={{ marginTop: 10, color: "var(--accent)", fontWeight: 600 }}>⏳ {note}</p>
      )}
      <style>{`@keyframes fl-spin{to{transform:rotate(360deg)}} .spin{animation:fl-spin .7s linear infinite}`}</style>
    </>
  );
}
