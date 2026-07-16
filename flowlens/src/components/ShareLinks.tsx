"use client";

import { useEffect, useState } from "react";

type Link = { id: string; token: string; active: boolean; createdAt: string };

export default function ShareLinks({ siteId, links }: { siteId: string; links: Link[] }) {
  const [origin, setOrigin] = useState("");
  useEffect(() => setOrigin(window.location.origin), []);

  return (
    <div className="card card-pad">
      <div className="between" style={{ marginBottom: 12 }}>
        <div>
          <h4>화이트라벨 공유 링크</h4>
          <p className="muted small" style={{ margin: "4px 0 0" }}>계정 없이 열람 가능한 읽기전용 리포트. 대행사 로고가 표시됩니다.</p>
        </div>
        <form action={`/api/sites/${siteId}/share`} method="post">
          <button className="btn primary sm" type="submit">+ 새 링크 생성</button>
        </form>
      </div>
      <div className="stack">
        {links.length === 0 && <div className="muted small">아직 생성된 공유 링크가 없습니다.</div>}
        {links.map((l) => {
          const url = `${origin}/share/${l.token}`;
          return (
            <div key={l.id} className="between" style={{ background: "var(--surface-2)", padding: "10px 12px", borderRadius: 8 }}>
              <a href={`/share/${l.token}`} target="_blank" className="small" style={{ color: "var(--accent)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {url || `/share/${l.token}`}
              </a>
              <div className="row">
                <button className="btn sm" type="button" onClick={() => navigator.clipboard.writeText(url)}>복사</button>
                <a className="btn sm" href={`/share/${l.token}`} target="_blank">열기 ↗</a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
