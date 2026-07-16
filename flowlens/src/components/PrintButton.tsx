"use client";

// 리포트를 PDF로 저장/인쇄. 브라우저 인쇄 대화상자에서 "PDF로 저장" 선택.
export default function PrintButton() {
  return (
    <button className="btn sm no-print" type="button" onClick={() => window.print()}>
      🖨 PDF로 저장 · 인쇄
    </button>
  );
}
