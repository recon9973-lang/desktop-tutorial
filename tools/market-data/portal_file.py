#!/usr/bin/env python3
"""공공데이터포털 «파일데이터» 를 키 없이 받아 본다(러너 전용).

오픈API 는 활용신청 키가 있어야 하지만, 파일데이터(csv/xlsx/zip)는 로그인 없이
내려받아지는 경우가 있다. 되는지 여부를 실제로 두드려 확인한다 — 안 되면 안 된다고
남기고 끝낸다(추정으로 채우지 않는다).

대상(기본):
  15051059  건강보험심사평가원_전국 병의원 및 약국 현황
  15051057  건강보험심사평가원_요양기관 개설 현황
  15127855  보건복지부_병원 및 의원 수(의료기관 종류별·시도별)
  15055562  심평원_의원급 표시과목별 시도별 진료비 통계
"""
import argparse, pathlib, re, sys, urllib.parse, urllib.request

OUT = pathlib.Path("data/market/raw/portal")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
DEFAULT_PKS = ["15051059", "15051057", "15127855", "15055562"]


def http(url: str, data: bytes | None = None, referer: str = "") -> tuple[int, bytes, dict]:
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ko,en;q=0.8"}
    if referer:
        h["Referer"] = referer
    if data is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:2000], dict(e.headers or {})
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode(), {}


def looks_like_file(body: bytes, headers: dict) -> bool:
    cd = (headers.get("Content-Disposition") or "").lower()
    ct = (headers.get("Content-Type") or "").lower()
    if "attachment" in cd:
        return True
    if body[:2] == b"PK" or body[:4] == b"%PDF":
        return True
    return "html" not in ct and len(body) > 50_000


def try_pk(pk: str) -> bool:
    page_url = f"https://www.data.go.kr/data/{pk}/fileData.do"
    st, body, _ = http(page_url)
    html = body.decode("utf-8", "replace")
    print(f"[{pk}] 소개 페이지 {st} · {len(body):,}바이트")
    if st != 200:
        return False
    ids = sorted(set(re.findall(r"(?:atchFileId|publicDataDetailPk)['\"]?\s*[:=,]\s*['\"]?"
                                r"(FILE_[0-9A-Za-z]+)", html)))
    sns = sorted(set(re.findall(r"fileDetailSn['\"]?\s*[:=,]\s*['\"]?(\d{1,3})", html)))
    print(f"[{pk}] 찾은 파일키 {ids or '없음'} · 일련번호 {sns or '없음'}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{pk}_page.html").write_bytes(body)
    got = False
    for fid in ids or [""]:
        for sn in sns or ["1"]:
            for url in [
                f"https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={fid}&fileDetailSn={sn}",
                ("https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?"
                 f"publicDataPk={pk}&publicDataDetailPk={fid}&fileDetailSn={sn}"),
            ]:
                st, body, hd = http(url, referer=page_url)
                ok = st == 200 and looks_like_file(body, hd)
                print(f"    {st} {len(body):>10,}바이트 {'←받음' if ok else ''} {url[:96]}")
                if ok:
                    name = (hd.get("Content-Disposition") or "")
                    m = re.search(r'filename="?([^\";]+)', name)
                    fn = urllib.parse.unquote(m.group(1)) if m else f"{pk}_{sn}.bin"
                    (OUT / fn.replace("/", "_")).write_bytes(body)
                    print(f"    → {fn}")
                    got = True
    return got


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pk", default=",".join(DEFAULT_PKS))
    a = ap.parse_args()
    ok = [pk for pk in a.pk.split(",") if pk.strip() and try_pk(pk.strip())]
    print(f"\n받아진 데이터셋 {len(ok)}개: {ok or '없음'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
