"use client";

import { useEffect, useState } from "react";

export default function InstallClient({ siteKey }: { siteKey: string }) {
  const [origin, setOrigin] = useState("https://app.flowlens.kr");
  const [copied, setCopied] = useState(false);
  const [status, setStatus] = useState<{ installed: boolean; eventCount?: number } | null>(null);

  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  const snippet = `<script async src="${origin}/t.js" data-site="${siteKey}"></script>`;

  async function checkStatus() {
    try {
      const r = await fetch(`/api/health/${siteKey}`);
      const d = await r.json();
      setStatus(d);
    } catch {
      setStatus(null);
    }
  }

  useEffect(() => {
    checkStatus();
    const t = setInterval(checkStatus, 5000);
    return () => clearInterval(t);
  }, []); // eslint-disable-line

  function copy() {
    navigator.clipboard.writeText(snippet).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className="card card-pad">
      <div className="between" style={{ marginBottom: 12 }}>
        <h4>추적 스크립트 설치</h4>
        {status && (
          status.installed ? (
            <span className="badge high">● 설치 확인됨 · {status.eventCount?.toLocaleString()} 이벤트 수집</span>
          ) : (
            <span className="badge gray">● 아직 이벤트 없음</span>
          )
        )}
      </div>
      <p className="muted small" style={{ marginTop: 0 }}>
        고객사 웹사이트 <code>&lt;head&gt;</code>에 아래 한 줄을 추가하면 수집이 시작됩니다.
      </p>
      <div className="code">{snippet}</div>
      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn primary sm" onClick={copy} type="button">{copied ? "복사됨 ✓" : "스크립트 복사"}</button>
        <button className="btn sm" onClick={checkStatus} type="button">설치 상태 새로고침</button>
      </div>
    </div>
  );
}
