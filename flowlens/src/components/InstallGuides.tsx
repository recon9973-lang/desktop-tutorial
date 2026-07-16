"use client";

import { useEffect, useState } from "react";

// 플랫폼별 설치 가이드 + 복사 스니펫 + 워드프레스 플러그인 다운로드.
export default function InstallGuides({ siteKey, siteId, defaultKey = "wordpress" }: { siteKey: string; siteId: string; defaultKey?: string }) {
  const [origin, setOrigin] = useState("https://app.flowlens.kr");
  const [open, setOpen] = useState<string>(defaultKey);
  const [copied, setCopied] = useState<string>("");

  useEffect(() => setOrigin(window.location.origin), []);
  const snippet = `<script async src="${origin}/t.js" data-site="${siteKey}"></script>`;
  // GTM은 맞춤HTML 주입 시 data-* 속성을 제거하므로, siteKey를 URL 쿼리로 전달한다.
  const gtmSnippet = `<script async src="${origin}/t.js?site=${siteKey}"></script>`;

  function copy(key: string, text: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(""), 1500);
    });
  }

  const platforms = [
    { key: "wordpress", label: "워드프레스 (원클릭)", badge: "자동 설치" },
    { key: "cafe24", label: "Cafe24 / 아임웹", badge: "간편" },
    { key: "gtm", label: "Google Tag Manager", badge: "간편" },
    { key: "general", label: "일반 사이트 (HTML)", badge: "" },
  ];

  return (
    <div className="card card-pad">
      <h4 style={{ marginBottom: 4 }}>플랫폼별 설치</h4>
      <p className="muted small" style={{ marginTop: 0, marginBottom: 14 }}>고객사 플랫폼에 맞는 방법을 선택하세요.</p>

      <div className="row" style={{ flexWrap: "wrap", marginBottom: 16 }}>
        {platforms.map((p) => (
          <button key={p.key} type="button" className={`btn sm ${open === p.key ? "primary" : ""}`} onClick={() => setOpen(p.key)}>
            {p.label}{p.badge && <span className="pill" style={{ marginLeft: 4 }}>{p.badge}</span>}
          </button>
        ))}
      </div>

      {open === "wordpress" && (
        <div className="stack" style={{ gap: 12 }}>
          <div className="notice small">
            <b>가장 쉬운 방법.</b> siteKey가 이미 들어있는 전용 플러그인을 내려받아 설치만 하면 됩니다. 코드 편집이 필요 없습니다.
          </div>
          <a className="btn primary" href={`/api/sites/${siteId}/wp-plugin`} download style={{ width: "fit-content" }}>
            ⬇ 워드프레스 플러그인 다운로드 (flowlens-tracker.php)
          </a>
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 2 }}>
            <li>내려받은 <code>flowlens-tracker.php</code>를 압축(zip)합니다.</li>
            <li>워드프레스 관리자 &gt; 플러그인 &gt; 새로 추가 &gt; 플러그인 업로드 &gt; zip 선택</li>
            <li>설치 후 <b>활성화</b>를 누르면 모든 페이지에 추적이 시작됩니다.</li>
          </ol>
        </div>
      )}

      {open === "cafe24" && (
        <div className="stack" style={{ gap: 12 }}>
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 2 }}>
            <li>Cafe24 관리자 &gt; <b>디자인 &gt; 디자인(스마트)디자인 편집</b></li>
            <li>공통 레이아웃 <code>&lt;/head&gt;</code> 바로 위에 아래 스크립트를 붙여넣기</li>
            <li>아임웹: <b>관리자 &gt; 사이트 관리 &gt; 고급 &gt; head 태그 삽입</b> 영역에 붙여넣기</li>
          </ol>
          <SnippetBox snippet={snippet} copied={copied === "cafe24"} onCopy={() => copy("cafe24", snippet)} />
        </div>
      )}

      {open === "gtm" && (
        <div className="stack" style={{ gap: 12 }}>
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 2 }}>
            <li>GTM &gt; <b>태그 &gt; 새로 만들기 &gt; 맞춤 HTML</b></li>
            <li>아래 <b>GTM 전용 코드</b>를 붙여넣고, 트리거는 <b>All Pages</b>로 설정</li>
            <li>저장 후 <b>제출/게시</b> (게시해야 반영됩니다)</li>
          </ol>
          <div className="notice small" style={{ background: "#fef9e7", borderColor: "#f0d98a", color: "#8a6d00" }}>
            GTM은 <code>data-site</code> 같은 속성을 자동 제거하므로, GTM에서는 반드시 아래처럼 <b>주소 뒤 <code>?site=</code></b>가 붙은 코드를 쓰세요. (일반 <code>&lt;head&gt;</code> 직접 삽입은 위/아래 <code>data-site</code> 버전을 써도 됩니다.)
          </div>
          <SnippetBox snippet={gtmSnippet} copied={copied === "gtm"} onCopy={() => copy("gtm", gtmSnippet)} />
        </div>
      )}

      {open === "general" && (
        <div className="stack" style={{ gap: 12 }}>
          <p className="muted small" style={{ margin: 0 }}>HTML을 직접 편집할 수 있는 사이트(React/Next/Vue 포함)는 <code>&lt;head&gt;</code>에 아래 한 줄을 추가하세요.</p>
          <SnippetBox snippet={snippet} copied={copied === "general"} onCopy={() => copy("general", snippet)} />
        </div>
      )}

      <div className="notice small" style={{ marginTop: 16, background: "#fdf2f2", borderColor: "#f5c2c2", color: "#a13b34" }}>
        네이버 블로그·카페, 쿠팡·11번가 등 외부 스크립트 삽입이 불가한 플랫폼은 지원되지 않습니다.
      </div>
    </div>
  );
}

function SnippetBox({ snippet, copied, onCopy }: { snippet: string; copied: boolean; onCopy: () => void }) {
  return (
    <div>
      <div className="code">{snippet}</div>
      <button className="btn primary sm" type="button" onClick={onCopy} style={{ marginTop: 10 }}>
        {copied ? "복사됨 ✓" : "스크립트 복사"}
      </button>
    </div>
  );
}
