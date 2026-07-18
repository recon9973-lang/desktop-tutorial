"use client";

// 운영 도구의 파괴적 동작(요금제 변경 등) 오클릭 방지용 확인창.
// 서버 액션 폼 안의 제출 버튼을 감싸, 확인을 거부하면 제출을 막는다.
export default function ConfirmButton({
  children,
  message,
  className,
}: {
  children: React.ReactNode;
  message: string;
  className?: string;
}) {
  return (
    <button
      type="submit"
      className={className}
      onClick={(e) => {
        if (!window.confirm(message)) e.preventDefault();
      }}
    >
      {children}
    </button>
  );
}
