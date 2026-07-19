"use client";

import { useEffect, useState } from "react";

type Finding = { level: "ok" | "warn" | "fail"; title: string; detail: string };

export default function InstallClient({ siteKey, siteId }: { siteKey: string; siteId: string }) {
  const [origin, setOrigin] = useState("https://app.flowlens.kr");
  const [copied, setCopied] = useState(false);
  const [status, setStatus] = useState<{ installed: boolean; eventCount?: number } | null>(null);
  const [checking, setChecking] = useState(false);
  const [findings, setFindings] = useState<Finding[] | null>(null);

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

  async function runDiagnose() {
    setChecking(true);
    setFindings(null);
    try {
      const r = await fetch(`/api/sites/${siteId}/install-check`);
      const d = await r.json();
      setFindings(
        Array.isArray(d.findings) && d.findings.length
          ? d.findings
          : [{ level: "warn", title: "점검을 완료하지 못했어요", detail: "잠시 후 다시 시도해 주세요." }]
      );
    } catch {
      setFindings([{ level: "warn", title: "점검을 완료하지 못했어요", detail: "네트워크 상태를 확인하고 다시 시도해 주세요." }]);
    } finally {
      setChecking(false);
    }
  }

  // 설치를 대신 해줄 담당자(개발자·호스팅)에게 보낼 메일 초안.
  const mailHref =
    "mailto:?subject=" +
    encodeURIComponent("[설치 요청] 웹사이트에 분석 코드 한 줄 추가 부탁드립니다") +
    "&body=" +
    encodeURIComponent(
      `안녕하세요,\n\n아래 코드 한 줄을 웹사이트의 모든 페이지 <head> 안에 넣어 주세요. (방문자 행동 분석용, 개인정보 미수집)\n\n${snippet}\n\n워드프레스·카페24·아임웹 등은 '헤더 스크립트' 영역에 붙이시면 됩니다. 넣으신 뒤 저장·게시까지 부탁드립니다.\n\n감사합니다.`
    );

  return (
    <div className="card card-pad">
      <div className="between" style={{ marginBottom: 12 }}>
        <h4>추적 스크립트 설치</h4>
        {status &&
          (status.installed ? (
            <span className="badge high">● 설치 확인됨 · {status.eventCount?.toLocaleString()} 이벤트 수집</span>
          ) : (
            <span className="badge gray">● 아직 이벤트 없음</span>
          ))}
      </div>
      <p className="muted small" style={{ marginTop: 0 }}>
        고객사 웹사이트 <code>&lt;head&gt;</code>에 아래 한 줄을 추가하면 수집이 시작됩니다.
      </p>
      <div className="code">{snippet}</div>
      <div className="row" style={{ marginTop: 12, flexWrap: "wrap" }}>
        <button className="btn primary sm" onClick={copy} type="button">
          {copied ? "복사됨 ✓" : "스크립트 복사"}
        </button>
        <a className="btn sm" href={mailHref}>설치 요청 메일 보내기</a>
        <button className="btn sm" onClick={runDiagnose} type="button" disabled={checking}>
          {checking ? "점검 중…" : "설치가 안 되나요? 원인 점검"}
        </button>
      </div>

      {findings && (
        <div className="stack" style={{ gap: 8, marginTop: 14 }}>
          {findings.map((f, i) => (
            <div
              key={i}
              className="notice small"
              style={{
                background: f.level === "ok" ? "#e7f6ee" : f.level === "fail" ? "#fdf2f2" : "#fbf4e6",
                borderColor: f.level === "ok" ? "#bde5cd" : f.level === "fail" ? "#f5c2c2" : "#f0dcb0",
                color: f.level === "ok" ? "#1a6b3c" : f.level === "fail" ? "#a13b34" : "#8a5a12",
              }}
            >
              <b>
                {f.level === "ok" ? "✓ " : f.level === "fail" ? "✕ " : "! "}
                {f.title}
              </b>
              <br />
              <span>{f.detail}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
