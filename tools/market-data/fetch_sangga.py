#!/usr/bin/env python3
"""소상공인시장진흥공단 상가(상권)정보 → 시군구별 업종 점포 수(러너 전용).

왜 쓰나: 심평원은 «병원이 몇 곳인가»를 말해 주지만 «그 동네가 어떤 동네인가»는 말해 주지
않는다. 상가정보는 동네의 업종 구성을 말해 준다 — 학원가인지, 오피스인지, 먹자골목인지.
병원 마케팅에서 타깃이 그 동네에 사는지 판단하는 데 쓴다.

[실측 2026-09-26] 사장님 열쇠에 이 서비스가 이미 붙어 있다
(`B553077/api/open/sdsc2/storeListInDong` 가 200 · resultCode 11 = 필수값 빠짐).

`--mode probe` 로 이 API가 무엇을 받는지 먼저 알아내고, 알아낸 대로 `--mode collect` 한다.
주소·값 이름을 외워 쓰지 않는다 — 답하는 것을 찾는다.
"""
import argparse, csv, json, os, pathlib, sys, time, urllib.parse, urllib.request

BASE = "https://apis.data.go.kr/B553077/api/open/sdsc2"
OUT = pathlib.Path("data/market")
RAW = OUT / "raw"
KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
OPS = ["storeListInArea", "storeListInDong", "storeListInUpjong", "storeListInRadius",
       "storeListInRectangle", "storeZoneInRectangle", "baroApi"]
calls = 0


def get(url: str, timeout: int = 15):
    global calls
    calls += 1
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()[:4000]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:1200]
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode()


def call(op: str, params: dict, timeout: int = 15):
    k = KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")
    url = f"{BASE}/{op}?serviceKey={k}&" + urllib.parse.urlencode(params)
    return get(url, timeout)


def codes_mode() -> int:
    """업종 코드표를 **자료에서** 찾아낸다 — 외워 쓰지 않는다.

    [실측 2026-09-26] 통하는 조합: storeListInDong + divId(signguCd/ctprvnCd/adongCd) + key.
    큰 시군구 몇 곳의 첫 장을 크게 받아 나오는 대·중분류를 모은다.
    세종 시군구코드도 여기서 알아낸다(행안부 동별 자료에 세종이 없어 코드를 못 만든다).
    """
    lcls, mcls, sejong = {}, {}, {}
    for key, div in (("11680", "signguCd"), ("41135", "signguCd"),
                     ("48170", "signguCd"), ("36", "ctprvnCd")):
        for page in (1, 2):
            st, body = call("storeListInDong",
                            {"divId": div, "key": key, "numOfRows": "1000",
                             "pageNo": str(page), "type": "json"}, timeout=60)
            if st != 200:
                print(f"  {div}={key} 쪽 {page} → http {st}"); break
            try:
                j = json.loads(body.decode("utf-8", "replace"))
            except Exception:      # 잘린 응답이면 낱말로 긁는다
                txt = body.decode("utf-8", "replace")
                import re as _re
                for a, b in _re.findall(r'"indsLclsCd" : "([^"]+)"[^}]*?"indsLclsNm" : "([^"]+)"', txt):
                    lcls[a] = b
                continue
            for it in (j.get("body") or {}).get("items") or []:
                if it.get("indsLclsCd"):
                    lcls[it["indsLclsCd"]] = it.get("indsLclsNm", "")
                if it.get("indsMclsCd"):
                    mcls[it["indsMclsCd"]] = it.get("indsMclsNm", "")
                if it.get("ctprvnCd") == "36" and it.get("signguCd"):
                    sejong[it["signguCd"]] = it.get("signguNm", "")
        print(f"  {div}={key} 까지 — 대분류 {len(lcls)} · 중분류 {len(mcls)}")
    RAW.mkdir(parents=True, exist_ok=True)
    out = {"대분류": lcls, "중분류": mcls, "세종_시군구코드": sejong,
           "찾은 날": "2026-09-26", "출처": "소상공인시장진흥공단 상가(상권)정보 · 기준월 202606"}
    (RAW / "sangga_codes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    print(f"\n대분류 {len(lcls)}개: " + ", ".join(f"{k} {v}" for k, v in sorted(lcls.items())))
    print(f"보건의료 중분류: " + ", ".join(f"{k} {v}" for k, v in sorted(mcls.items())
                                         if k.startswith("Q")))
    print(f"세종 시군구코드: {sejong}")
    print(f"호출 {calls}회 → {RAW/'sangga_codes.json'}")
    return 0


def sggu_codes() -> list[tuple[str, str, str]]:
    """행정동 표준코드 앞 다섯 자리 = 시군구 코드. ANSEO 경계 자료에서 가져온다."""
    import gzip
    p = pathlib.Path("/home/user/veo-platform/apps/api/data/population/mois_dong_population.json.gz")
    if not p.exists():
        return []
    d = json.load(gzip.open(p, "rt", encoding="utf-8"))
    seen = {}
    for code, sido, sggu in zip(d["dong_code"], d["sido_name"], d["sigungu_name"]):
        seen.setdefault(code[:5], (sido, sggu))
    return [(c, v[0], v[1]) for c, v in sorted(seen.items())]


def probe() -> int:
    """무엇을 받는지 알아낸다. **시도한 것 전부**를 한 파일에 적어 둔다 —
    앞 판에서는 마지막 성공만 덮어써져 «어느 값이 통했는지»를 알 수 없었다."""
    print(f"열쇠 {'있음' if KEY else '없음'}")
    if not KEY:
        return 2
    shapes = [
        ("시군구", {"divId": "signguCd", "key": "11680"}),
        ("시도", {"divId": "ctprvnCd", "key": "11"}),
        ("행정동", {"divId": "adongCd", "key": "11680640"}),
        ("시군구+업종", {"divId": "signguCd", "key": "11680", "indsLclsCd": "Q1"}),
        ("값없음", {}),
    ]
    tried = []
    for op in OPS:
        for name, sh in shapes:
            p = dict(sh, numOfRows="1", pageNo="1", type="json")
            st, body = call(op, p)
            txt = body.decode("utf-8", "replace")
            rc = tot = None
            for kk, tgt in (("resultCode", "rc"), ("totalCount", "tot")):
                i = txt.find(f'"{kk}"')
                if i >= 0:
                    seg = txt[i:i + 60].split(":", 1)[-1].strip().strip(',').strip()
                    v = seg.split(",")[0].strip().strip('"').strip()
                    if tgt == "rc":
                        rc = v
                    else:
                        tot = v
            row = {"op": op, "값": name, "http": st, "resultCode": rc, "totalCount": tot,
                   "맛보기": " ".join(txt.split())[:160]}
            tried.append(row)
            print(f"[{st:>3}] {op:<22} {name:<12} rc={str(rc):<6} total={str(tot):<10} "
                  f"{row['맛보기'][:90]}")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "sangga_probe.json").write_text(
        json.dumps({"시도한 것": tried}, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [t for t in tried if t["resultCode"] == "00"]
    print(f"\n통한 조합 {len(ok)}개:")
    for t in ok:
        print(f"  {t['op']} · {t['값']} · 전체 {t['totalCount']}")
    print(f"호출 {calls}회 → {RAW/'sangga_probe.json'}")
    return 0


def collect(op: str, div: str, lcls: list[str], limit: int) -> int:
    """시군구 × 업종 대분류의 «전체 건수»만 센다(numOfRows=1 로 totalCount 만 본다)."""
    path = RAW / "sangga_counts.jsonl"
    RAW.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                d = json.loads(line); done.add((d["시군구코드"], d["업종대분류"]))
            except Exception:  # noqa: BLE001
                pass
    regions = sggu_codes()
    if not regions:
        print("시군구 코드를 못 만들었다 — ANSEO 자료가 없다"); return 2
    print(f"시군구 {len(regions)} × 업종 {len(lcls)} = {len(regions)*len(lcls):,}쌍 (이미 {len(done):,})")
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for code, sido, sggu in regions:
            for lc in lcls:
                if (code, lc) in done:
                    continue
                if n >= limit:
                    print("한도 도달 — 다음 실행에서 이어받는다"); return 0
                p = {"divId": div, "key": code, "numOfRows": "1", "pageNo": "1", "type": "json"}
                if lc:
                    p["indsLclsCd"] = lc
                st, body = call(op, p, timeout=20)
                n += 1
                total = None
                try:
                    j = json.loads(body.decode("utf-8", "replace"))
                    total = (j.get("body") or {}).get("totalCount")
                except Exception:  # noqa: BLE001
                    pass
                f.write(json.dumps({"시군구코드": code, "시도": sido, "시군구": sggu,
                                    "업종대분류": lc, "점포수": total, "http": st},
                                   ensure_ascii=False) + "\n")
                time.sleep(0.05)
            f.flush()
            print(f"  {sido} {sggu} 완료 (누적 {n})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="probe", choices=["probe", "codes", "collect"])
    ap.add_argument("--op", default="storeListInArea")
    ap.add_argument("--div", default="signguCd")
    ap.add_argument("--lcls", default="", help="업종 대분류 코드 쉼표. 비우면 전체 한 번")
    ap.add_argument("--limit", type=int, default=6000)
    a = ap.parse_args()
    if not KEY:
        print("DATA_GO_KR_SERVICE_KEY 없음 — 중단"); return 2
    if a.mode == "probe":
        return probe()
    if a.mode == "codes":
        return codes_mode()
    lcls = [x.strip() for x in a.lcls.split(",") if x.strip()] or [""]
    return collect(a.op, a.div, lcls, a.limit)


if __name__ == "__main__":
    sys.exit(main())
