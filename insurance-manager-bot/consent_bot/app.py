"""프로젝트 ① — 가입설계동의 봇 오케스트레이터 (상태머신).

기획안.md §5의 상태머신을 코드로 구현. 각 단계는 사용자 확인 게이트/재시도 지원.
웹 자동화(GA) 단계는 실제 사이트 캘리브레이션이 필요하므로 --skip-ga로 분리 실행 가능
(입력→PDF작성→팩스이미지 구간은 실제 양식으로 완결 동작).

사용 예:
    python -m consent_bot.app --src 양식_원본.pdf --skip-ga \
        --name 홍길동 --phone 01012345678 --agent 이은우 --out ./output
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.parsing import parse_customer_text          # noqa: E402
from common.state import JobStore, dedup_key             # noqa: E402
from common.validation import normalize_phone           # noqa: E402
from consent_bot.fill_pdf import ConsentData, fill_consent_pdf, verify_layout  # noqa: E402
from consent_bot.to_fax_images import output_pdf_name, pdf_to_fax_images       # noqa: E402


def confirm_gate(fields: dict, ask=input) -> bool:
    print("\n=== 추출/입력값 확인 (사용자 확정 게이트) ===")
    for k, v in fields.items():
        print(f"  {k:10s}: {v}")
    return ask("이대로 진행할까요? [y/N]: ").strip().lower() == "y"


def run(args) -> int:
    store = JobStore(args.db)
    src = Path(args.src)

    # INPUT / EXTRACT -----------------------------------------------------
    if args.paste_file:
        parsed = parse_customer_text(Path(args.paste_file).read_text(encoding="utf-8"))
        name = args.name or parsed.name
        phone = args.phone or parsed.phone
        if parsed.warnings:
            print("[주의]", "; ".join(parsed.warnings))
    else:
        name, phone = args.name, args.phone

    if not name or not phone:
        print("오류: 고객명/전화번호가 필요합니다.", file=sys.stderr)
        return 2
    phone = normalize_phone(phone) or phone

    # CONSENT (동의 증빙) -------------------------------------------------
    if not args.consent_ref and not args.assume_consent:
        print("오류: 동의 증빙(--consent-ref)이 없습니다. "
              "동의 확보 후 진행하거나 --assume-consent로 명시 확인하세요.", file=sys.stderr)
        return 3

    # CONFIRM -------------------------------------------------------------
    fields = {"고객명": name, "전화번호": phone, "사용인": args.agent,
              "서명일": (args.date or date.today().isoformat()),
              "동의증빙": args.consent_ref or "(사용자 확인)"}
    if not args.yes and not confirm_gate(fields):
        print("사용자 취소.")
        return 1

    key = dedup_key(name, args.birth or "", date.today())
    if store.already_done(key) and not args.force:
        print("이미 처리된 건입니다(중복 방지). 재생성하려면 --force.", file=sys.stderr)
        return 4

    # GA_* (웹 자동화) ----------------------------------------------------
    if not args.skip_ga:
        from consent_bot.ga_automation import GAConsentAutomation, GAContext
        ctx = GAContext(download_dir=Path(args.out))
        bot = GAConsentAutomation(ctx)
        try:
            bot.open()
            bot.wait_manual_login()          # 휴먼 게이트: 로그인+간편PW
            bot.go_customer_management()
            n = bot.search_customer(args.code or name)
            if n == 0:
                raise RuntimeError("고객 검색 결과 없음")
            if n > 1:
                idx = int(input(f"동명이인 {n}명. 선택할 행 번호(0부터): "))
                bot.pick_customer_row(idx)
            src = bot.create_written_consent((args.birth or "").replace("-", ""))
        finally:
            bot.close()

    # PDF_SAVE 검증 + PDF_FILL -------------------------------------------
    problems = verify_layout(src)
    if problems:
        print("[양식 검증 실패]", *problems, sep="\n  ", file=sys.stderr)
        return 5

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    sign_date = date.fromisoformat(args.date) if args.date else date.today()
    filled = out_dir / output_pdf_name(name, sign_date)
    fill_consent_pdf(src, filled, ConsentData(
        customer_name=name, phone=phone, agent_name=args.agent, sign_date=sign_date,
    ))
    print(f"[완료] 기재 PDF: {filled}")

    # IMG_MAKE ------------------------------------------------------------
    imgs = pdf_to_fax_images(filled, out_dir, name, when=sign_date)
    for p in imgs:
        print(f"[완료] 팩스 전송용 이미지: {p}")

    # DELIVER (카카오톡) — 1차: 폴더 열기 안내 -----------------------------
    print(f"\n[다음 단계] 위 이미지를 프로그램 사용자 카카오톡으로 전달 후 "
          f"팩스({'02-2200-2999'})로 전송하세요.")
    print(f"저장 폴더: {out_dir.resolve()}")

    # DONE ----------------------------------------------------------------
    store.record(
        project="consent", key=key, customer_name=name, input_source=(
            "paste" if args.paste_file else "manual"),
        state="DONE", success=True,
        files=[filled.name] + [p.name for p in imgs],
        consent_ref=args.consent_ref,
    )
    store.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="가입설계동의 봇 (프로젝트 ①)")
    p.add_argument("--src", required=True, help="원본 동의서 PDF(2장). GA에서 저장한 파일")
    p.add_argument("--name"); p.add_argument("--phone"); p.add_argument("--agent", required=True)
    p.add_argument("--birth", help="생년월일 YYYY-MM-DD (GA 입력/중복키용)")
    p.add_argument("--code", help="GA 고객 코드(미지정 시 이름으로 검색)")
    p.add_argument("--date", help="서명일 YYYY-MM-DD (기본: 오늘)")
    p.add_argument("--paste-file", help="카톡/문자 원문 텍스트 파일(파싱)")
    p.add_argument("--consent-ref", help="동의 증빙 파일 경로(audit trail)")
    p.add_argument("--assume-consent", action="store_true", help="동의 확보를 명시 확인(증빙 없이)")
    p.add_argument("--out", default="./output"); p.add_argument("--db", default="manager_bot.sqlite3")
    p.add_argument("--skip-ga", action="store_true", help="GA 웹 자동화 건너뛰고 --src로 바로 작성")
    p.add_argument("--yes", action="store_true", help="확인 게이트 자동 통과(무인 테스트)")
    p.add_argument("--force", action="store_true", help="중복이어도 재생성")
    return p


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
