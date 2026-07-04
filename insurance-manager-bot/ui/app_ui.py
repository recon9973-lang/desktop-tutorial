"""보험 매니저 봇 — 데스크톱 UI (PySide6).

두 봇을 탭으로 감싼 업무 패널.
  탭 ① 가입설계동의 봇: 입력/파싱 → 작성 & 미리보기 → 팩스 이미지 생성 → 폴더 열기
  탭 ② 고객정보 자동입력: 카톡 파싱 → 주민번호 체크섬 검증(마스킹) → GA 입력(반자동)

실행: python -m ui.app_ui
헤드리스 검증: QT_QPA_PLATFORM=offscreen (스크린샷 grab 지원)
"""
from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt                                              # noqa: E402
from PySide6.QtGui import QImage, QPixmap                                  # noqa: E402
from PySide6.QtWidgets import (                                           # noqa: E402
    QApplication, QCheckBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

import fitz                                                                # noqa: E402
from common.ocr import OCRUnavailable, image_to_text, ocr_available       # noqa: E402
from common.parsing import ParsedCustomer, parse_customer_text            # noqa: E402
from common.validation import (mask_rrn, normalize_phone, rrn_birthdate,  # noqa: E402
                               validate_rrn)
from consent_bot.fill_pdf import ConsentData, fill_consent_pdf, verify_layout  # noqa: E402
from consent_bot.to_fax_images import output_pdf_name, pdf_to_fax_images  # noqa: E402

_DEFAULT_FORM = Path(__file__).resolve().parent.parent / "양식_원본.pdf"
_IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def _first_dropped_image(event) -> str | None:
    for url in event.mimeData().urls():
        p = url.toLocalFile()
        if Path(p).suffix.lower() in _IMG_EXT:
            return p
    return None


class ImageDropMixin:
    """이미지 파일 드래그드롭 → 온디바이스 OCR → 항목 채우기.

    서브클래스는 on_ocr_parsed(ParsedCustomer, raw_text) 를 구현한다.
    """

    def enable_image_drop(self):
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if _first_dropped_image(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = _first_dropped_image(event)
        if path:
            self.run_ocr(path)

    def run_ocr(self, path: str):
        if not ocr_available():
            QMessageBox.warning(
                self, "OCR 불가",
                "온디바이스 Tesseract가 없습니다. tesseract-ocr(+kor)를 설치하세요.\n"
                "개인정보 보호를 위해 클라우드 OCR로 대체하지 않습니다.")
            return
        try:
            text = image_to_text(path)
        except OCRUnavailable as e:
            QMessageBox.warning(self, "OCR 불가", str(e))
            return
        self.on_ocr_parsed(parse_customer_text(text), text)

    def on_ocr_parsed(self, parsed: ParsedCustomer, raw_text: str):  # override
        raise NotImplementedError


def _render_pdf_page(pdf: Path, page_index: int, width: int = 460) -> QPixmap:
    doc = fitz.open(pdf)
    page = doc[page_index]
    zoom = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
    qpix = QPixmap.fromImage(img.copy())
    doc.close()
    return qpix


class ConsentTab(ImageDropMixin, QWidget):
    """탭 ① 가입설계동의 봇."""

    def __init__(self):
        super().__init__()
        self.enable_image_drop()
        self._filled_pdf: Path | None = None
        self._out_dir = Path("./output")

        root = QHBoxLayout(self)
        left = QVBoxLayout()

        # 입력 폼
        form_box = QGroupBox("고객/사용인 정보")
        form = QFormLayout(form_box)
        self.src = QLineEdit(str(_DEFAULT_FORM) if _DEFAULT_FORM.exists() else "")
        src_btn = QPushButton("원본 동의서 PDF 선택…")
        src_btn.clicked.connect(self._pick_src)
        self.name = QLineEdit(); self.phone = QLineEdit()
        self.agent = QLineEdit(); self.birth = QLineEdit()
        self.sign_date = QLineEdit(date.today().isoformat())
        form.addRow(src_btn, self.src)
        form.addRow("고객명", self.name)
        form.addRow("전화번호", self.phone)
        form.addRow("사용인명(FC)", self.agent)
        form.addRow("생년월일(YYYY-MM-DD)", self.birth)
        form.addRow("서명일", self.sign_date)
        self.consent_chk = QCheckBox("고객 동의를 확보했습니다(증빙 보관)")
        form.addRow("동의 확인", self.consent_chk)
        left.addWidget(form_box)

        # 카톡 파싱 / 이미지 OCR
        paste_box = QGroupBox("카톡/문자 원문 붙여넣기 · 이미지 드래그드롭(OCR)")
        pv = QVBoxLayout(paste_box)
        self.paste = QPlainTextEdit()
        self.paste.setPlaceholderText("이름/전화가 포함된 원문… 또는 사진을 이 창에 끌어다 놓기")
        btn_row = QHBoxLayout()
        parse_btn = QPushButton("파싱하여 채우기")
        parse_btn.clicked.connect(self._parse)
        ocr_btn = QPushButton("이미지 불러오기(OCR)")
        ocr_btn.clicked.connect(self._pick_image)
        btn_row.addWidget(parse_btn); btn_row.addWidget(ocr_btn)
        pv.addWidget(self.paste); pv.addLayout(btn_row)
        left.addWidget(paste_box)

        # 액션 버튼
        actions = QHBoxLayout()
        self.make_btn = QPushButton("작성 & 미리보기")
        self.fax_btn = QPushButton("팩스 이미지 생성")
        self.open_btn = QPushButton("폴더 열기")
        self.make_btn.clicked.connect(self._make)
        self.fax_btn.clicked.connect(self._make_fax)
        self.open_btn.clicked.connect(self._open_folder)
        self.fax_btn.setEnabled(False)
        for b in (self.make_btn, self.fax_btn, self.open_btn):
            actions.addWidget(b)
        left.addLayout(actions)

        self.status = QLabel("대기 중")
        self.status.setWordWrap(True)
        left.addWidget(self.status)
        left.addStretch(1)
        root.addLayout(left, 3)

        # 미리보기
        prev_box = QGroupBox("작성 미리보기 (2페이지)")
        pl = QVBoxLayout(prev_box)
        self.preview = QLabel("작성 후 미리보기가 표시됩니다.")
        self.preview.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.preview.setMinimumWidth(480)
        pl.addWidget(self.preview)
        root.addWidget(prev_box, 2)

    # --- handlers -------------------------------------------------------
    def _pick_src(self):
        f, _ = QFileDialog.getOpenFileName(self, "원본 동의서 PDF", "", "PDF (*.pdf)")
        if f:
            self.src.setText(f)

    def _parse(self):
        self._apply_parsed(parse_customer_text(self.paste.toPlainText()), "파싱 완료")

    def _pick_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "고객정보 이미지", "",
                                           "이미지 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)")
        if f:
            self.run_ocr(f)

    def on_ocr_parsed(self, parsed: ParsedCustomer, raw_text: str):
        self.paste.setPlainText(raw_text)
        self._apply_parsed(parsed, "이미지 OCR 완료 — 값 확인 필요")

    def _apply_parsed(self, p: ParsedCustomer, base_msg: str):
        if p.name:
            self.name.setText(p.name)
        if p.phone:
            self.phone.setText(p.phone)
        msg = base_msg
        if p.warnings:
            msg += " — [주의] " + "; ".join(p.warnings)
        self.status.setText(msg)

    def _collect(self) -> ConsentData | None:
        if not self.name.text() or not self.phone.text() or not self.agent.text():
            QMessageBox.warning(self, "입력 필요", "고객명·전화번호·사용인명은 필수입니다.")
            return None
        if not self.consent_chk.isChecked():
            QMessageBox.warning(self, "동의 확인", "고객 동의 확보를 확인해야 작성할 수 있습니다.")
            return None
        try:
            sd = date.fromisoformat(self.sign_date.text().strip())
        except ValueError:
            QMessageBox.warning(self, "날짜 오류", "서명일 형식은 YYYY-MM-DD 입니다.")
            return None
        phone = normalize_phone(self.phone.text()) or self.phone.text()
        return ConsentData(customer_name=self.name.text().strip(), phone=phone,
                           agent_name=self.agent.text().strip(), sign_date=sd)

    def _make(self):
        src = Path(self.src.text().strip())
        if not src.exists():
            QMessageBox.warning(self, "양식 없음", "원본 동의서 PDF를 선택하세요.")
            return
        problems = verify_layout(src)
        if problems:
            QMessageBox.critical(self, "양식 검증 실패", "\n".join(problems))
            return
        data = self._collect()
        if not data:
            return
        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._filled_pdf = self._out_dir / output_pdf_name(data.customer_name, data.sign_date)
        fill_consent_pdf(src, self._filled_pdf, data)
        self.preview.setPixmap(_render_pdf_page(self._filled_pdf, 1))
        self.fax_btn.setEnabled(True)
        self.status.setText(f"작성 완료: {self._filled_pdf}")

    def _make_fax(self):
        if not self._filled_pdf:
            return
        imgs = pdf_to_fax_images(self._filled_pdf, self._out_dir, self.name.text().strip())
        self.status.setText("팩스 이미지 생성: " + ", ".join(p.name for p in imgs)
                            + "  → 카카오톡 전달 후 팩스(02-2200-2999)")

    def _open_folder(self):
        import subprocess
        self._out_dir.mkdir(parents=True, exist_ok=True)
        opener = {"win32": ["explorer"], "darwin": ["open"]}.get(sys.platform, ["xdg-open"])
        try:
            subprocess.Popen(opener + [str(self._out_dir.resolve())])
        except Exception:
            self.status.setText(f"폴더: {self._out_dir.resolve()}")


class EntryTab(ImageDropMixin, QWidget):
    """탭 ② 고객정보 자동입력 봇."""

    def __init__(self):
        super().__init__()
        self.enable_image_drop()
        self._rrn: str | None = None
        root = QVBoxLayout(self)

        paste_box = QGroupBox("카톡/문자 원문 붙여넣기 · 이미지 드래그드롭(OCR)")
        pv = QVBoxLayout(paste_box)
        self.paste = QPlainTextEdit()
        self.paste.setPlaceholderText("이름/전화/주소/주민번호 원문… 또는 사진을 이 창에 끌어다 놓기")
        btn_row = QHBoxLayout()
        parse_btn = QPushButton("파싱 & 검증")
        parse_btn.clicked.connect(self._parse)
        ocr_btn = QPushButton("이미지 불러오기(OCR)")
        ocr_btn.clicked.connect(self._pick_image)
        btn_row.addWidget(parse_btn); btn_row.addWidget(ocr_btn)
        pv.addWidget(self.paste); pv.addLayout(btn_row)
        root.addWidget(paste_box)

        form_box = QGroupBox("확인 (주민번호는 마스킹 표시)")
        form = QFormLayout(form_box)
        self.name = QLineEdit(); self.phone = QLineEdit(); self.address = QLineEdit()
        self.rrn_masked = QLineEdit(); self.rrn_masked.setReadOnly(True)
        self.birth = QLineEdit(); self.birth.setReadOnly(True)
        for lbl, w in [("이름", self.name), ("전화", self.phone), ("주소", self.address),
                       ("주민번호(마스킹)", self.rrn_masked), ("생년월일", self.birth)]:
            form.addRow(lbl, w)
        root.addWidget(form_box)

        self.ga_btn = QPushButton("GA 반자동 입력 시작 (로그인·간편PW 직접)")
        self.ga_btn.clicked.connect(self._ga_notice)
        root.addWidget(self.ga_btn)
        self.status = QLabel("대기 중"); self.status.setWordWrap(True)
        root.addWidget(self.status); root.addStretch(1)

    def _pick_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "고객정보 이미지", "",
                                           "이미지 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)")
        if f:
            self.run_ocr(f)

    def on_ocr_parsed(self, parsed: ParsedCustomer, raw_text: str):
        self.paste.setPlainText(raw_text)
        self._apply(parsed)

    def _parse(self):
        self._apply(parse_customer_text(self.paste.toPlainText()))

    def _apply(self, p: ParsedCustomer):
        self.name.setText(p.name or ""); self.phone.setText(p.phone or "")
        self.address.setText(p.address or "")
        self._rrn = p.rrn
        if p.rrn:
            self.rrn_masked.setText(mask_rrn(p.rrn))
            b = rrn_birthdate(p.rrn)
            self.birth.setText(b.isoformat() if b else "")
            ok = validate_rrn(p.rrn)
            self.status.setText("주민번호 체크섬 " + ("정상" if ok else "실패 — 오인식 가능(재확인)"))
        else:
            self.status.setText("주민번호를 찾지 못했습니다.")
        if p.warnings:
            self.status.setText(self.status.text() + " | [주의] " + "; ".join(p.warnings))

    def _ga_notice(self):
        QMessageBox.information(
            self, "GA 반자동 입력",
            "실제 GA 입력은 로그인(ID/PW 자동)+간편비밀번호(직접) 후 진행됩니다.\n"
            "셀렉터 캘리브레이션이 완료된 환경에서 entry_bot.app로 실행하세요.\n"
            "주민번호는 메모리에서만 처리되며 저장되지 않습니다.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("보험 매니저 봇")
        self.resize(1000, 680)
        tabs = QTabWidget()
        tabs.addTab(ConsentTab(), "① 가입설계동의")
        tabs.addTab(EntryTab(), "② 고객정보 자동입력")
        self.setCentralWidget(tabs)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
