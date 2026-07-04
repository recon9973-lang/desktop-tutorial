"""프로젝트 ② — 고객정보 자동입력 봇 오케스트레이터.

흐름(기획안_2 §4): 입력 → 온디바이스 파싱 → 검증(주민번호 체크섬 등)
→ 사용자 확인(마스킹) → 반자동 로그인 → 필드 자동입력 → ★제출 전 사람 확인 → 기록.

민감정보 취급: 주민번호는 메모리에서만 다루고 즉시 폐기. 로그·DB에 원문 저장 금지.
웹 자동화 단계는 실제 GA 화면 캘리브레이션 필요 → --dry-run으로 파싱·검증까지 실행 가능.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.parsing import parse_customer_text            # noqa: E402
from common.secure import mask_name, mask_phone           # noqa: E402
from common.state import JobStore, dedup_key              # noqa: E402
from common.validation import mask_rrn, rrn_birthdate, validate_rrn  # noqa: E402


def run(args) -> int:
    text = Path(args.paste_file).read_text(encoding="utf-8") if args.paste_file else (args.text or "")
    parsed = parse_customer_text(text)

    name = args.name or parsed.name
    phone = args.phone or parsed.phone
    address = args.address or parsed.address
    rrn = args.rrn or parsed.rrn

    # 검증 --------------------------------------------------------------
    errors = []
    if not name:
        errors.append("이름 없음")
    if not phone:
        errors.append("전화번호 없음/형식 오류")
    if not rrn or not validate_rrn(rrn):
        errors.append("주민번호 없음 또는 체크섬 실패(오인식 가능)")
    for w in parsed.warnings:
        print("[주의]", w)
    if errors:
        print("[검증 실패]", *errors, sep="\n  ", file=sys.stderr)
        if not args.allow_invalid:
            return 2

    # 사용자 확인(마스킹 표시) ------------------------------------------
    birth = rrn_birthdate(rrn) if rrn else None
    print("\n=== 입력값 확인 (주민번호 마스킹) ===")
    print(f"  이름     : {name}")
    print(f"  전화     : {phone}")
    print(f"  주소     : {address or '(없음)'}")
    print(f"  주민번호 : {mask_rrn(rrn) if rrn else '(없음)'}  (생년월일 {birth})")
    if not args.yes and input("이대로 GA에 입력할까요? [y/N]: ").strip().lower() != "y":
        print("사용자 취소.")
        return 1

    if args.dry_run:
        print("\n[dry-run] 파싱·검증까지 완료. 웹 입력은 실행하지 않음.")
        # 로그: 주민번호 원문 저장 안 함(마스킹 식별자만)
        store = JobStore(args.db)
        store.record(project="entry", key=dedup_key(name, birth or "", date.today()),
                     customer_name=name, input_source="paste" if args.paste_file else "manual",
                     state="CONFIRM", success=False, fail_step="dry-run")
        store.close()
        return 0

    # 반자동 로그인 + 필드 입력 -----------------------------------------
    from entry_bot.ga_login import GALogin
    from entry_bot.ga_form_fill import EntryData, GAEntryForm

    login = GALogin(user_key=args.user_key)
    try:
        login.open()
        if not login.autofill_id_pw():
            print("자격증명 미등록 — common.secure.save_credentials로 먼저 등록하세요.", file=sys.stderr)
            return 3
        if not login.wait_manual_simple_password():
            print("로그인 확인 실패(간편PW/세션).", file=sys.stderr)
            return 4

        form = GAEntryForm(login.page)
        form.fill(EntryData(name=name, phone=phone, zipcode=args.zipcode,
                            address=address, address_detail=args.address_detail, rrn=rrn))
        problems = form.verify_written(EntryData(name, phone, None, address, None, rrn))
        if problems:
            print("[입력 검증]", *problems, sep="\n  ", file=sys.stderr)

        # ★ 제출 전 사람 최종 확인
        ok = args.yes or input("\n★ 화면 최종 확인 후 제출할까요? [y/N]: ").strip().lower() == "y"
        submitted = form.submit_after_human_confirm(ok)
        print("제출 완료." if submitted else "제출 보류(사용자 미확인).")
    finally:
        login.close()
        rrn = None  # 민감정보 폐기

    store = JobStore(args.db)
    store.record(project="entry", key=dedup_key(name, birth or "", date.today()),
                 customer_name=name, input_source="paste" if args.paste_file else "manual",
                 state="DONE", success=True)
    store.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="고객정보 자동입력 봇 (프로젝트 ②)")
    p.add_argument("--text", help="카톡/문자 원문(따옴표로 감싸 전달)")
    p.add_argument("--paste-file", help="카톡/문자 원문 텍스트 파일")
    p.add_argument("--name"); p.add_argument("--phone"); p.add_argument("--address")
    p.add_argument("--address-detail"); p.add_argument("--zipcode")
    p.add_argument("--rrn", help="주민번호(민감) — 즉시 폐기됨. 지정 없으면 원문에서 파싱")
    p.add_argument("--user-key", default="default", help="keyring 자격증명 키")
    p.add_argument("--db", default="manager_bot.sqlite3")
    p.add_argument("--dry-run", action="store_true", help="파싱·검증만(웹 입력 안 함)")
    p.add_argument("--allow-invalid", action="store_true", help="검증 실패해도 진행")
    p.add_argument("--yes", action="store_true", help="확인 게이트 자동 통과(테스트)")
    return p


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
