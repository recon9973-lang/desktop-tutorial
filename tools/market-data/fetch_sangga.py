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
import argparse, csv, json, os, pathlib, re, sys, time, urllib.parse, urllib.request

BASE = "https://apis.data.go.kr/B553077/api/open/sdsc2"
OUT = pathlib.Path("data/market")
RAW = OUT / "raw"
KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
OPS = ["storeListInArea", "storeListInDong", "storeListInUpjong", "storeListInRadius",
       "storeListInRectangle", "storeZoneInRectangle", "baroApi"]
calls = 0


def get(url: str, timeout: int = 15, cap: int | None = 4000):
    """cap 은 «맛보기만 볼 때» 쓴다. 코드표·수집은 통째로 읽어야 한다 —
    [실측] 4,000바이트에서 자르는 바람에 업종 대분류가 6개만 잡히고 중분류는 0개였다."""
    global calls
    calls += 1
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
            return r.status, (body[:cap] if cap else body)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:1200]
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode()


def call(op: str, params: dict, timeout: int = 15, cap: int | None = 4000):
    k = KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")
    url = f"{BASE}/{op}?serviceKey={k}&" + urllib.parse.urlencode(params)
    return get(url, timeout, cap)


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
                             "pageNo": str(page), "type": "json"}, timeout=90, cap=None)
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


# ── 업종 중분류 가운데 «병원 상권에 쓸모 있는 것»만 고른다 ─────────────────────
# 74가지를 다 세면 252×74=18,648 번이라 한 판에 안 끝난다. 환자 수요를 대신
# 말해 주는 것만 고른다(왜 골랐는지 옆에 적는다 — 다음 사람이 지우거나 더할 수 있게).
MCLS_PICK = [
    ("S207", "이용·미용"),        # 미용 수요 — 피부과·성형외과 상권의 핵
    ("S208", "욕탕·신체관리"),    # 에스테틱·마사지 — 비수술 미용과 겹친다
    ("G215", "의약·화장품 소매"),  # 약국·화장품 — 처방·미용 동선
    ("P105", "일반 교육"),        # 학원가 — 아이 있는 집이 사는 동네
    ("P106", "기타 교육"),        # 같은 뜻으로 함께 본다
    ("Q101", "병원"),             # 상가로 등록된 병원
    ("Q102", "의원"),             # 상가로 등록된 의원
    ("Q104", "기타 보건"),        # 한의원·치과 등이 섞여 들어온다
    ("R103", "스포츠 서비스"),    # 헬스·필라테스 — 다이어트·비만 수요
    ("I211", "주점"),             # 유흥 상권 — 밤에 사람이 도는 곳
    ("I212", "비알코올"),         # 카페 — 낮 유동인구
    ("L102", "부동산 서비스"),     # 임대가 도는 곳 = 상권이 바뀌는 곳
    ("M107", "본사·경영 컨설팅"),  # 오피스 상권 — 직장인 낮 인구
    ("G209", "섬유·의복·신발 소매"),  # 패션 상권 — 젊은 여성 동선
]

# 2026년에 생긴 구는 202606 상가자료가 아직 모를 수 있다. 구 코드가 모두 0으로
# 오면 시 코드로 한 번 더 물어본다(화성시는 2026년에 4개 구가 생겼다).
PARENT_CODE = {("경기", "화성시"): ["41590"]}


def regions() -> list[dict]:
    """252곳(표와 같은 자리) × 그 자리를 가리키는 시군구 코드들.

    행정동 표준코드 앞 다섯 자리 = 시군구 코드. ANSEO 행안부 자료에서 가져온다.
    이름은 표(`market_sggu.csv`)와 **같은 꼴**로 돌린다 — 「고양시덕양구」→「고양덕양구」,
    화성 4개 구는 표에 한 줄(「화성시」)이므로 한 자리로 묶는다.
    세종은 행안부 동별 자료에 없어 코드를 못 만든다 — 상가자료에서 찾아낸 코드를 쓴다.
    """
    import gzip
    pop = pathlib.Path("/home/user/veo-platform/apps/api/data/population/"
                       "mois_dong_population.json.gz")
    if not pop.exists():
        return []
    d = json.load(gzip.open(pop, "rt", encoding="utf-8"))
    short = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
             "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
             "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
             "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
             "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
             "경상남도": "경남", "제주특별자치도": "제주"}
    # 표의 자리 이름을 기준으로 삼는다 — 새 이름을 만들지 않는다.
    table = []
    tp = OUT / "market_sggu.csv"
    if tp.exists():
        with tp.open(encoding="utf-8-sig") as f:
            table = [(r["시도"], r["시군구"]) for r in csv.DictReader(f)]
    tset = set(table)

    def fit(sido: str, sggu: str) -> tuple[str, str]:
        g = sggu.replace(" ", "")
        m = re.match(r"^(.+?)시(.+구)$", g)     # 고양시덕양구 → 고양덕양구
        if m:
            g = m.group(1) + m.group(2)
        if (sido, g) in tset or not tset:
            return (sido, g)
        # 표에 구가 없고 시 한 줄만 있으면 시로 묶는다(화성 4개 구 → 화성시)
        for s2, g2 in tset:
            if s2 == sido and g2.endswith("시") and g.startswith(g2[:-1]):
                return (s2, g2)
        return (sido, g)

    bykey: dict[tuple[str, str], list[str]] = {}
    seen: set[str] = set()
    for code, sido, sggu in zip(d["dong_code"], d["sido_name"], d["sigungu_name"]):
        c = code[:5]
        if c in seen:
            continue
        seen.add(c)
        bykey.setdefault(fit(short.get(sido, sido), sggu), []).append(c)

    sj = RAW / "sangga_codes.json"          # 세종 — 상가자료에서 찾아낸 코드
    if sj.exists():
        for c in (json.loads(sj.read_text(encoding="utf-8"))
                  .get("세종_시군구코드") or {}):
            bykey.setdefault(("세종", "세종시"), []).append(c)

    return [{"시도": k[0], "시군구": k[1], "코드": sorted(v),
             "대체코드": PARENT_CODE.get(k, [])}
            for k, v in sorted(bykey.items())]


def count(op: str, div: str, code: str, field: str = "", val: str = "") -> tuple:
    """그 자리·그 업종의 «전체 건수»만 센다(numOfRows=1 로 totalCount 만 본다)."""
    p = {"divId": div, "key": code, "numOfRows": "1", "pageNo": "1", "type": "json"}
    if field:
        p[field] = val
    st, body = call(op, p, timeout=25, cap=None)
    try:
        j = json.loads(body.decode("utf-8", "replace"))
        b = j.get("body") or {}
        return st, b.get("totalCount"), (j.get("header") or {}).get("resultCode")
    except Exception:  # noqa: BLE001
        return st, None, None


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


def collect(op: str, div: str, limit: int, do_mcls: bool) -> int:
    """252곳 × (전체 · 업종 대분류 10 · 골라 둔 중분류)의 점포 수를 센다.

    한 판이 끊겨도 이어받는다 — 이미 센 (코드, 갈래, 업종) 은 건너뛴다.
    **대분류를 먼저 다 센 뒤** 중분류로 넘어간다(중간에 끊기면 굵은 것부터 남게).
    """
    path = RAW / "sangga_counts.jsonl"
    RAW.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                d = json.loads(line)
                done.add((d["코드"], d["갈래"], d["업종코드"]))
            except Exception:  # noqa: BLE001
                pass
    regs = regions()
    if not regs:
        print("시군구 코드를 못 만들었다 — ANSEO 자료가 없다"); return 2

    codes = json.loads((RAW / "sangga_codes.json").read_text(encoding="utf-8"))
    lcls = sorted(codes["대분류"].items())
    print(f"자리 {len(regs)}곳 · 업종 대분류 {len(lcls)}가지 · "
          f"중분류 {len(MCLS_PICK) if do_mcls else 0}가지 (이미 센 것 {len(done):,})")

    # ── 중분류로 걸러지는지 먼저 확인한다 — 두드려 보지 않은 값을 쓰지 않는다 ──
    mcls_ok = False
    if do_mcls:
        # 한 번 안 되면 세 번까지 다시 묻는다 — 한 번 삐끗해서 중분류를 통째로
        # 건너뛰면 다음 판을 또 돌려야 한다.
        for t in range(3):
            _, whole, _ = count(op, div, "11680")
            _, big, _ = count(op, div, "11680", "indsLclsCd", "S2")
            _, mid, _ = count(op, div, "11680", "indsMclsCd", "S207")
            print(f"  [확인 {t+1}] 강남구 전체 {whole} · 대분류 S2 {big} · 중분류 S207 {mid}")
            try:
                mcls_ok = (0 < int(mid) <= int(big) < int(whole))
            except Exception:  # noqa: BLE001
                mcls_ok = False
            if mcls_ok or whole is not None:
                break
            time.sleep(2 ** t)
        print(f"  [확인] 중분류로 걸러진다: {'그렇다' if mcls_ok else '아니다 — 건너뛴다'}")

    jobs = [("전체", "", "", "", "")]
    jobs += [("대", c, n, "indsLclsCd", c) for c, n in lcls]
    if mcls_ok:
        jobs += [("중", c, n, "indsMclsCd", c) for c, n in MCLS_PICK]

    n = 0
    with path.open("a", encoding="utf-8") as f:
        for reg in regs:
            for code in reg["코드"] + reg["대체코드"]:
                for kind, ic, inm, field, val in jobs:
                    if (code, kind, ic) in done:
                        continue
                    if n >= limit:
                        print("한도 도달 — 다음 판에서 이어받는다"); return 0
                    st, total, rc = count(op, div, code, field, val)
                    n += 1
                    f.write(json.dumps({"시도": reg["시도"], "시군구": reg["시군구"],
                                        "코드": code, "갈래": kind, "업종코드": ic,
                                        "업종": inm, "점포수": total, "http": st,
                                        "resultCode": rc}, ensure_ascii=False) + "\n")
                    time.sleep(0.03)
                f.flush()
            print(f"  {reg['시도']} {reg['시군구']} 완료 (누적 {n})")
    print(f"호출 {calls}회 → {path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="probe", choices=["probe", "codes", "collect"])
    ap.add_argument("--op", default="storeListInDong")
    ap.add_argument("--div", default="signguCd")
    ap.add_argument("--no-mcls", action="store_true", help="업종 중분류는 건너뛴다")
    ap.add_argument("--limit", type=int, default=8000)
    a = ap.parse_args()
    if not KEY:
        print("DATA_GO_KR_SERVICE_KEY 없음 — 중단"); return 2
    if a.mode == "probe":
        return probe()
    if a.mode == "codes":
        return codes_mode()
    return collect(a.op, a.div, a.limit, not a.no_mcls)


if __name__ == "__main__":
    sys.exit(main())
