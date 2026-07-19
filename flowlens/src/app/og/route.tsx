import { ImageResponse } from "next/og";

export const runtime = "edge";
export const contentType = "image/png";

// 브랜드 대표 이미지(1200×630). 블로그 Article 구조화 데이터의 image,
// 그리고 소셜 공유 미리보기(og:image)에 사용. 안정적 URL: /og
// (한글 폰트 임베드가 필요 없도록 텍스트는 라틴/기호 위주로 구성)
export function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          background: "linear-gradient(135deg, #0b1020 0%, #1b1f47 55%, #4f46e5 130%)",
          color: "#ffffff",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: "#6366f1",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 34,
              fontWeight: 800,
            }}
          >
            F
          </div>
          <div style={{ fontSize: 40, fontWeight: 800, letterSpacing: -1 }}>FlowLens</div>
        </div>

        <div style={{ marginTop: 44, display: "flex", flexDirection: "column", fontSize: 68, fontWeight: 800, lineHeight: 1.15, letterSpacing: -2 }}>
          <div style={{ display: "flex" }}>Heatmap analytics</div>
          <div style={{ display: "flex" }}>for higher conversion</div>
        </div>

        <div style={{ marginTop: 30, fontSize: 30, color: "#c7cbf5", fontWeight: 500 }}>
          Privacy-first web behavior analytics · flow.seokorea.org
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
