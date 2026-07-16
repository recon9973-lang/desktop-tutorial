"use client";

import { useRef, useState } from "react";

// 로고 파일을 선택하면 캔버스로 축소(최대 240px)해 data URL로 변환, 미리보기 + 저장.
export default function LogoUploader({ currentUrl, logoText }: { currentUrl: string; logoText: string }) {
  const [preview, setPreview] = useState(currentUrl);
  const dataRef = useRef<HTMLInputElement>(null);

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const max = 240;
        const scale = Math.min(1, max / Math.max(img.width, img.height));
        const w = Math.round(img.width * scale);
        const h = Math.round(img.height * scale);
        const c = document.createElement("canvas");
        c.width = w;
        c.height = h;
        c.getContext("2d")!.drawImage(img, 0, 0, w, h);
        const dataUrl = c.toDataURL(file.type === "image/png" ? "image/png" : "image/jpeg", 0.9);
        setPreview(dataUrl);
        if (dataRef.current) dataRef.current.value = dataUrl;
      };
      img.src = reader.result as string;
    };
    reader.readAsDataURL(file);
  }

  return (
    <form action="/api/settings/logo" method="post">
      <div className="row" style={{ gap: 16, marginBottom: 14, alignItems: "flex-end" }}>
        <div>
          <div className="muted small" style={{ marginBottom: 6 }}>미리보기</div>
          <div style={{ height: 44, minWidth: 120, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-2)", display: "flex", alignItems: "center", padding: "0 12px" }}>
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="로고" style={{ maxHeight: 28, maxWidth: 180 }} />
            ) : (
              <b>{logoText}</b>
            )}
          </div>
        </div>
        <div>
          <label className="btn sm" style={{ cursor: "pointer" }}>
            이미지 선택
            <input type="file" accept="image/*" onChange={onFile} style={{ display: "none" }} />
          </label>
        </div>
      </div>

      <div className="field" style={{ maxWidth: 320 }}>
        <label>로고 텍스트 (이미지가 없을 때 표시)</label>
        <input name="logoText" defaultValue={logoText} placeholder="예: GrowthLab" />
      </div>

      <input ref={dataRef} type="hidden" name="logoUrl" />
      <div className="row" style={{ marginTop: 8 }}>
        <button className="btn primary sm" type="submit">저장</button>
        <button className="btn sm" type="submit" name="remove" value="1">로고 이미지 제거</button>
      </div>
      <p className="muted small" style={{ marginTop: 8 }}>로고는 고객에게 보내는 화이트라벨 리포트 상단에 표시됩니다. (최대 240px로 자동 축소)</p>
    </form>
  );
}
