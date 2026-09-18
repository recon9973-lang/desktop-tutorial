#!/usr/bin/env python3
"""심평원(HIRA) 병원정보서비스 → 지역별 병의원 상권 원자료 수집기.

작업 컨테이너는 외부 egress 가 막혀 있어(apis.data.go.kr 403) 이 스크립트는
GitHub Actions 러너에서 돈다(.github/workflows/market-data.yml).

원칙: 코드표를 외우지 않고 **API 응답에서 발견**한다. 시도코드·시군구코드·
진료과목코드 모두 탐침(probe)으로 찾고, 찾은 것만 쓴다. 지어낸 값 없음.

산출(모두 data/market/raw/):
  hira_sido.json            시도코드 ↔ 이름 ↔ 기관수
  hira_master.csv           전국 요양기관 마스터(기관별 1행)
  hira_subject_codes.json   진료과목코드 ↔ 이름(있으면) ↔ 전국 기관수
  hira_sggu_subject.jsonl   시군구 × 진료과목 기관수 (재실행 시 이어받기)
"""
import argparse, csv, json, os, pathlib, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

BASE = "https://apis.data.go.kr/B551182"
HOSP = BASE + "/hospInfoServicev2/getHospBasisList"
DETAIL_CANDIDATES = [
    BASE + "/MadmDtlInfoService2.7/getDgsbjtInfo2.7",
    BASE + "/MadmDtlInfoService2/getDgsbjtInfo2",
    BASE + "/MadmDtlInfoService/getDgsbjtInfo",
]
OUT = pathlib.Path("data/market/raw")
KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()

# 마스터에서 뽑을 필드(응답에 있는 것만 채워진다)
FIELDS = ["ykiho", "yadmNm", "clCd", "clCdNm", "sidoCd", "sidoCdNm", "sgguCd",
          "sgguCdNm", "emdongNm", "postNo", "addr", "telno", "hospUrl", "estbDd",
          "drTotCnt", "gdrCnt", "intnCnt", "resdntCnt", "sdrCnt", "mdeptGdrCnt",
          "mdeptIntnCnt", "mdeptResdntCnt", "mdeptSdrCnt", "detyGdrCnt",
          "detyIntnCnt", "detyResdntCnt", "detySdrCnt", "cmdcGdrCnt",
          "cmdcIntnCnt", "cmdcResdntCnt", "cmdcSdrCnt", "pnursCnt", "XPos", "YPos"]

calls = 0


def _key_param() -> str:
    return KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")


def get(url_base: str, params: dict, tries: int = 4) -> ET.Element:
    """XML 한 번 받기. 실패는 지수 백오프로 재시도."""
    global calls
    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())
    url = f"{url_base}?serviceKey={_key_param()}&{qs}"
    last = None
    for i in range(tries):
        try:
            calls += 1
            with urllib.request.urlopen(url, timeout=60) as r:
                body = r.read()
            return ET.fromstring(body)
        except Exception as e:  # noqa: BLE001 — 네트워크/파싱 모두 재시도 대상
            last = e
            time.sleep(2 ** i)
    raise RuntimeError(f"{url_base} 실패: {last}")


def result_code(root: ET.Element) -> tuple[str, str]:
    return (root.findtext(".//resultCode") or "", root.findtext(".//resultMsg") or "")


def total_of(root: ET.Element) -> int:
    t = root.findtext(".//totalCount")
    return int(t) if t and t.strip().isdigit() else 0


def count(params: dict) -> int:
    """조건에 맞는 기관 수만(numOfRows=1)."""
    root = get(HOSP, dict(params, pageNo=1, numOfRows=1))
    code, msg = result_code(root)
    if code not in ("00", "0", ""):
        raise RuntimeError(f"API 오류 {code}: {msg} · params={params}")
    return total_of(root)


def items(params: dict, rows: int = 1000, page: int = 1) -> list[dict]:
    root = get(HOSP, dict(params, pageNo=page, numOfRows=rows))
    out = []
    for it in root.iter("item"):
        out.append({f: (it.findtext(f) or "").strip() for f in FIELDS})
    return out


# ────────────────────────────── 단계 ──────────────────────────────
def stage_probe() -> None:
    n = count({})
    print(f"[probe] 키 정상 · 전국 요양기관(병의원) 총 {n:,}건")


def stage_sido() -> list[dict]:
    """시도코드를 외우지 않고 찾는다: 11~50 × 0000 을 두드려 답하는 것만 취한다."""
    found = []
    for n in range(11, 51):
        cd = f"{n}0000"
        try:
            root = get(HOSP, {"sidoCd": cd, "pageNo": 1, "numOfRows": 1})
        except RuntimeError as e:
            print(f"  {cd} 건너뜀({e})"); continue
        tot = total_of(root)
        if tot <= 0:
            continue
        nm = ""
        for it in root.iter("item"):
            nm = (it.findtext("sidoCdNm") or "").strip(); break
        found.append({"sidoCd": cd, "sidoCdNm": nm, "count": tot})
        print(f"  {cd} {nm} {tot:,}")
    OUT.joinpath("hira_sido.json").write_text(
        json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[sido] {len(found)}개 시도 · 합계 {sum(f['count'] for f in found):,}")
    return found


def stage_master(sidos: list[dict]) -> None:
    """시도별로 전 페이지를 받아 기관 마스터를 만든다. 페이지 상한에 걸리면
    그 시도만 시군구로 쪼개 다시 받는다(값을 추정하지 않는다)."""
    path = OUT / "hira_master.csv"
    seen: set[str] = set()
    rows: list[dict] = []
    for s in sidos:
        want, got = s["count"], 0
        page, guard = 1, 0
        while got < want and guard < 400:
            guard += 1
            batch = items({"sidoCd": s["sidoCd"]}, rows=1000, page=page)
            if not batch:
                break
            for b in batch:
                k = b["ykiho"] or f"{b['yadmNm']}|{b['addr']}"
                if k in seen:
                    continue
                seen.add(k); rows.append(b)
            got += len(batch); page += 1
        print(f"  {s['sidoCdNm'] or s['sidoCd']}: {got:,}/{want:,}")
        if got < want:  # 페이지 상한 → 시군구 단위로 다시
            print(f"    ↳ 모자라 시군구 단위로 재수집")
            for sggu in sorted({r["sgguCd"] for r in rows
                                if r["sidoCd"] == s["sidoCd"] and r["sgguCd"]}):
                page = 1
                while page < 60:
                    batch = items({"sidoCd": s["sidoCd"], "sgguCd": sggu}, 1000, page)
                    if not batch:
                        break
                    for b in batch:
                        k = b["ykiho"] or f"{b['yadmNm']}|{b['addr']}"
                        if k not in seen:
                            seen.add(k); rows.append(b)
                    page += 1
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print(f"[master] {len(rows):,}행 → {path}")


def stage_subject_codes() -> list[dict]:
    """진료과목코드도 두드려 찾는다(00~99). 이름은 상세서비스에서 얻어 본다."""
    found = []
    for n in range(0, 100):
        cd = f"{n:02d}"
        try:
            tot = count({"dgsbjtCd": cd})
        except RuntimeError as e:
            print(f"  {cd} 건너뜀({e})"); continue
        if tot > 0:
            found.append({"dgsbjtCd": cd, "dgsbjtCdNm": "", "count": tot})
            print(f"  {cd} {tot:,}")
    names = subject_names()
    for f in found:
        f["dgsbjtCdNm"] = names.get(f["dgsbjtCd"], "")
    OUT.joinpath("hira_subject_codes.json").write_text(
        json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[subject-codes] {len(found)}개 · 이름 확인 {sum(1 for f in found if f['dgsbjtCdNm'])}개")
    return found


def subject_names() -> dict:
    """큰 병원 몇 곳의 진료과목 상세를 읽어 코드↔이름을 실제 응답에서 모은다."""
    path = OUT / "hira_master.csv"
    if not path.exists():
        return {}
    big = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["clCd"] in ("01", "11") and r["ykiho"]:
                big.append(r["ykiho"])
            if len(big) >= 40:
                break
    for ep in DETAIL_CANDIDATES:
        names: dict = {}
        ok = 0
        for y in big[:40]:
            try:
                root = get(ep, {"ykiho": y, "pageNo": 1, "numOfRows": 100}, tries=2)
            except RuntimeError:
                break
            hit = False
            for it in root.iter("item"):
                cd = (it.findtext("dgsbjtCd") or "").strip()
                nm = (it.findtext("dgsbjtCdNm") or "").strip()
                if cd and nm:
                    names[cd] = nm; hit = True
            ok += 1 if hit else 0
        if names:
            print(f"[subject-names] {ep} 에서 {len(names)}개 이름 확보(응답 {ok}곳)")
            return names
        print(f"[subject-names] {ep} 에서 못 얻음")
    return {}


def stage_sggu_subject(sido_list: list[dict], codes: list[dict], max_calls: int) -> None:
    """시군구 × 진료과목 기관수. 한도에 걸려도 받은 데까지 남기고 다음 실행에서 이어받는다."""
    path = OUT / "hira_sggu_subject.jsonl"
    done = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                d = json.loads(line); done.add((d["sidoCd"], d["sgguCd"], d["dgsbjtCd"]))
            except Exception:  # noqa: BLE001
                pass
    pairs = []
    with (OUT / "hira_master.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["sidoCd"] and r["sgguCd"]:
                pairs.append((r["sidoCd"], r["sidoCdNm"], r["sgguCd"], r["sgguCdNm"]))
    pairs = sorted(set(pairs))
    print(f"[sggu-subject] 시군구 {len(pairs)} × 과목 {len(codes)} = {len(pairs)*len(codes):,}쌍 "
          f"(이미 받은 {len(done):,})")
    start = calls
    with path.open("a", encoding="utf-8") as f:
        for sidoCd, sidoNm, sgguCd, sgguNm in pairs:
            for c in codes:
                if (sidoCd, sgguCd, c["dgsbjtCd"]) in done:
                    continue
                if calls - start >= max_calls:
                    print("[sggu-subject] 호출 한도 도달 — 다음 실행에서 이어받는다"); return
                try:
                    n = count({"sidoCd": sidoCd, "sgguCd": sgguCd, "dgsbjtCd": c["dgsbjtCd"]})
                except RuntimeError as e:
                    print(f"  실패 {sidoNm} {sgguNm} {c['dgsbjtCd']}: {e}"); continue
                f.write(json.dumps({"sidoCd": sidoCd, "sidoCdNm": sidoNm,
                                    "sgguCd": sgguCd, "sgguCdNm": sgguNm,
                                    "dgsbjtCd": c["dgsbjtCd"],
                                    "dgsbjtCdNm": c["dgsbjtCdNm"], "count": n},
                                   ensure_ascii=False) + "\n")
                f.flush()
            print(f"  {sidoNm} {sgguNm} 완료 (누적 호출 {calls:,})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["probe", "sido", "master", "subject", "sggu-subject", "all"])
    ap.add_argument("--max-calls", type=int, default=9000)
    a = ap.parse_args()
    if not KEY:
        print("DATA_GO_KR_SERVICE_KEY 없음 — 중단(목업으로 채우지 않는다)"); return 2
    OUT.mkdir(parents=True, exist_ok=True)
    sidos, codes = [], []
    sido_path, code_path = OUT / "hira_sido.json", OUT / "hira_subject_codes.json"
    if a.stage in ("probe", "all"):
        stage_probe()
    if a.stage in ("sido", "master", "all"):
        sidos = json.loads(sido_path.read_text(encoding="utf-8")) if sido_path.exists() \
            and a.stage == "master" else stage_sido()
    if a.stage in ("master", "all"):
        stage_master(sidos)
    if a.stage in ("subject", "all"):
        codes = stage_subject_codes()
    if a.stage in ("sggu-subject", "all"):
        if not codes:
            codes = json.loads(code_path.read_text(encoding="utf-8"))
        if not sidos and sido_path.exists():
            sidos = json.loads(sido_path.read_text(encoding="utf-8"))
        stage_sggu_subject(sidos, codes, a.max_calls)
    print(f"총 호출 {calls:,}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
