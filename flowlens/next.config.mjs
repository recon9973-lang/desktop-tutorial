/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker 배포용 독립 실행 번들 생성 (개발에는 영향 없음)
  output: "standalone",
  // 스크린샷 캡처용 헤드리스 크롬은 번들링하지 말고 런타임에 그대로 로드 (Vercel 서버리스)
  serverExternalPackages: ["@sparticuz/chromium", "puppeteer-core"],
  // Next 파일추적이 데이터파일(.br 압축 크롬)을 빼먹으므로, 스크린샷 라우트에 강제 포함
  outputFileTracingIncludes: {
    "/api/sites/[id]/screenshot": ["./node_modules/@sparticuz/chromium/bin/**"],
  },
  // 추적 스크립트(t.js)는 외부 고객 사이트에서 로드되므로 캐시/CORS 여유를 둔다.
  async headers() {
    return [
      {
        source: "/t.js",
        headers: [
          { key: "Access-Control-Allow-Origin", value: "*" },
          { key: "Cache-Control", value: "public, max-age=300" },
        ],
      },
    ];
  },
};

export default nextConfig;
