"""양식 좌표 캘리브레이션 도구 (프로젝트 ①).

양식이 개정되어 좌표가 어긋날 때, 원본 PDF에서 '동의함' 앵커와 서명 블록
앵커 좌표를 다시 추출해 template.json 갱신을 돕는다.

사용:
    python tools/calibrate_template.py 양식_원본.pdf
    python tools/calibrate_template.py 양식_원본.pdf --render   # 페이지 PNG도 출력
"""
import argparse
import sys

import fitz


ANCHORS = ["동의함", "서명일", "성명", "서명", "전화번호", "생년월일", "FC인사명", "(서명"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    print(f"pages={doc.page_count} size={doc[0].rect}")
    for pi, page in enumerate(doc):
        print(f"\n=== PAGE {pi} ===")
        for w in page.get_text("words"):
            if any(a in w[4] for a in ANCHORS):
                print(f"  p{pi} ({w[0]:6.1f},{w[1]:6.1f})-({w[2]:6.1f},{w[3]:6.1f})  {w[4]!r}")
        if args.render:
            out = f"calib_p{pi + 1}.png"
            page.get_pixmap(dpi=150).save(out)
            print(f"  rendered -> {out}")


if __name__ == "__main__":
    sys.exit(main())
