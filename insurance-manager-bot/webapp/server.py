"""원스톱 웹 앱 — 보험 매니저 봇 (FastAPI, 로컬 실행).

한 화면에서 고객정보를 한 번 입력(OCR/붙여넣기/직접)하면:
  ① 동의서 자동 작성(양식 PDF 위에 체크·서명·전화 기재 → PDF/팩스이미지)
  ② 신한 웹 폼 자동 입력(반자동 로그인)
두 가지를 모두 사용할 수 있다.

실행:  python -m webapp.server   (기본 http://127.0.0.1:8000)

민감정보 원칙: 주민번호 원문은 서버 메모리(세션)에서만 보관하고 브라우저에는
마스킹 값만 내려보낸다. 로그·디스크에 원문을 남기지 않는다.
"""
from __future__ import annotations

import io
import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

import fitz
from common.ocr import image_to_text, ocr_available
from common.parsing import parse_customer_text
from common.secure import mask_phone
from common.state import JobStore, dedup_key
from common.validation import (mask_rrn, normalize_phone, rrn_birthdate,
                               validate_rrn)
from consent_bot.fill_pdf import ConsentData, fill_consent_pdf, verify_layout
from consent_bot.to_fax_images import output_pdf_name, pdf_to_fax_images

_HERE = Path(__file__).resolve().parent
_STATIC = _HERE / "static"
_RUN_DIR = _HERE.parent / "webapp_output"
_RUN_DIR.mkdir(exist_ok=True)

app = FastAPI(title="보험 매니저 봇 · 원스톱")

# 서버 메모리 세션(단일 사용자 로컬 앱). 주민번호 원문은 여기에만.
SESSIONS: dict[str, dict] = {}
DOWNLOADS: dict[str, Path] = {}


def _session_public(sid: str) -> dict:
    """브라우저로 내려보낼 안전 필드(주민번호는 마스킹만)."""
    s = SESSIONS[sid]
    rrn = s.get("rrn")
    birth = rrn_birthdate(rrn) if rrn else None
    return {
        "session_id": sid,
        "name": s.get("name") or "",
        "phone": s.get("phone") or "",
        "address": s.get("address") or "",
        "birthdate": birth.isoformat() if birth else "",
        "rrn_masked": mask_rrn(rrn) if rrn else "",
        "rrn_valid": bool(rrn and validate_rrn(rrn)),
        "has_rrn": bool(rrn),
        "warnings": s.get("warnings") or [],
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return (_STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    return {"ok": True, "ocr": ocr_available()}


@app.post("/api/recognize")
async def recognize(text: str = Form(None), image: UploadFile = File(None)):
    """이미지 OCR 또는 텍스트에서 고객정보 추출 → 세션 생성."""
    raw = text or ""
    if image is not None:
        if not ocr_available():
            raise HTTPException(400, "온디바이스 OCR(Tesseract)이 설치되지 않았습니다.")
        data = await image.read()
        tmp = _RUN_DIR / f"_ocr_{uuid.uuid4().hex}.img"
        tmp.write_bytes(data)
        try:
            raw = image_to_text(str(tmp))
        finally:
            tmp.unlink(missing_ok=True)
    parsed = parse_customer_text(raw)
    sid = uuid.uuid4().hex
    SESSIONS[sid] = {
        "name": parsed.name, "phone": parsed.phone, "address": parsed.address,
        "rrn": parsed.rrn, "warnings": parsed.warnings,
    }
    result = _session_public(sid)
    result["raw_text"] = raw
    return result


@app.post("/api/update")
async def update(session_id: str = Form(...), name: str = Form(None),
                 phone: str = Form(None), address: str = Form(None)):
    """사용자가 확인 화면에서 수정한 값 반영(주민번호는 여기서 안 다룸)."""
    if session_id not in SESSIONS:
        raise HTTPException(404, "세션 없음")
    s = SESSIONS[session_id]
    if name is not None:
        s["name"] = name
    if phone is not None:
        s["phone"] = normalize_phone(phone) or phone
    if address is not None:
        s["address"] = address
    return _session_public(session_id)


@app.post("/api/consent/fill")
async def consent_fill(
    session_id: str = Form(...),
    agent_name: str = Form(...),
    consent_confirmed: bool = Form(False),
    sign_date: str = Form(None),
    pdf: UploadFile = File(...),
):
    """① 동의서 작성: 업로드한 원본 양식 위에 기재 → PDF + 팩스이미지."""
    if session_id not in SESSIONS:
        raise HTTPException(404, "세션 없음")
    if not consent_confirmed:
        raise HTTPException(400, "고객 동의 확보 확인이 필요합니다.")
    s = SESSIONS[session_id]
    if not s.get("name") or not s.get("phone"):
        raise HTTPException(400, "고객명/전화번호가 필요합니다.")

    src = _RUN_DIR / f"src_{uuid.uuid4().hex}.pdf"
    src.write_bytes(await pdf.read())
    problems = verify_layout(src)
    if problems:
        src.unlink(missing_ok=True)
        raise HTTPException(400, "양식 검증 실패: " + "; ".join(problems))

    sd = date.fromisoformat(sign_date) if sign_date else date.today()
    out_pdf = _RUN_DIR / output_pdf_name(s["name"], sd)
    fill_consent_pdf(src, out_pdf, ConsentData(
        customer_name=s["name"], phone=s["phone"], agent_name=agent_name, sign_date=sd))
    imgs = pdf_to_fax_images(out_pdf, _RUN_DIR, s["name"], when=sd)
    src.unlink(missing_ok=True)

    # 미리보기(2페이지) PNG를 base64로
    doc = fitz.open(out_pdf)
    zoom = 520 / doc[1].rect.width
    preview = doc[1].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    import base64
    preview_b64 = base64.b64encode(preview.tobytes("png")).decode()
    doc.close()

    # 다운로드 토큰
    def tok(p: Path) -> str:
        t = uuid.uuid4().hex
        DOWNLOADS[t] = p
        return t

    # 처리 기록(주민번호 미저장)
    store = JobStore(_RUN_DIR / "manager_bot.sqlite3")
    store.record(project="consent", key=dedup_key(s["name"], s.get("birth") or "", sd),
                 customer_name=s["name"], input_source="webapp", state="DONE",
                 success=True, files=[out_pdf.name] + [p.name for p in imgs])
    store.close()

    return {
        "preview_png": preview_b64,
        "pdf": {"name": out_pdf.name, "token": tok(out_pdf)},
        "fax": [{"name": p.name, "token": tok(p)} for p in imgs],
    }


@app.get("/api/download/{token}")
def download(token: str):
    p = DOWNLOADS.get(token)
    if not p or not p.exists():
        raise HTTPException(404, "파일 없음")
    return FileResponse(str(p), filename=p.name)


@app.post("/api/entry/prepare")
async def entry_prepare(session_id: str = Form(...)):
    """② 신한 웹 폼 입력 준비: 검증 상태 확인(주민번호 마스킹)."""
    if session_id not in SESSIONS:
        raise HTTPException(404, "세션 없음")
    pub = _session_public(session_id)
    ready = bool(pub["name"] and pub["phone"] and pub["has_rrn"] and pub["rrn_valid"])
    pub["ready_to_submit"] = ready
    pub["note"] = ("실제 GA 입력은 신한 화면 셀렉터 캘리브레이션 후 동작합니다. "
                   "로그인·간편비밀번호는 사용자가 직접 수행합니다.")
    return pub


@app.post("/api/entry/submit")
async def entry_submit(session_id: str = Form(...), user_key: str = Form("default")):
    """② GA 반자동 입력 트리거(스캐폴드). 실제 사이트 캘리브레이션 필요."""
    if session_id not in SESSIONS:
        raise HTTPException(404, "세션 없음")
    # 실제 구현은 entry_bot.ga_login + ga_form_fill 사용(셀렉터 확정 후 활성화)
    return JSONResponse({
        "status": "scaffold",
        "message": ("웹 폼 자동입력은 실제 GA 화면 셀렉터 확정 후 활성화됩니다. "
                    "현재는 흐름·검증까지 준비 완료 상태입니다."),
    })


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
