#!/usr/bin/env python3
"""심평원 병원정보서비스가 **어떤 조합에 답하는지** 짧게 두드린다(러너 전용).

왜: 시군구 × 진료과목으로 11,800번 부르려다 5시간 51분에 **188번**밖에 못 불렀다.
거의 다 `urlopen error timed out` 이었다. 그런데 **과목만으로 전국**을 묻는 것은
3분에 끝났다. 무엇과 무엇을 함께 물을 때 멈추는지 가려야 한다.

한 조합마다 **한 번만** 부르고 짧게 끊는다(오래 매달리지 않는다).
"""
import json, os, pathlib, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

BASE = "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
OUT = pathlib.Path("data/market/raw")


def one(params: dict, timeout: int):
    k = KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")
    url = f"{BASE}?serviceKey={k}&" + urllib.parse.urlencode(params)
    t0 = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
        el = ET.fromstring(body)
        tot = el.findtext(".//totalCount")
        code = el.findtext(".//resultCode")
        return round(time.time() - t0, 1), (tot if tot is not None else f"rc={code}")
    except urllib.error.HTTPError as e:
        # [내가 빠뜨린 것] 거절 «이유» 를 안 적어 뒀다 — 「한도 초과」인지 「열쇠」인지
        # 그 한 줄이면 바로 아는데 종류만 적고 버렸다(2026-10-01).
        body = e.read()[:400].decode("utf-8", "replace")
        return round(time.time() - t0, 1), f"http {e.code} · {' '.join(body.split())[:260]}"
    except Exception as e:                                   # noqa: BLE001
        return round(time.time() - t0, 1), f"못 받음({type(e).__name__}: {str(e)[:120]})"


def main() -> int:
    if not KEY:
        print("열쇠 없음"); return 2
    SEOUL, GANGNAM, PEDIA = "110000", "110019", "10"     # 서울 · 강남구 · 소아청소년과
    shapes = [
        ("① 전국·과목만",        {"dgsbjtCd": PEDIA}),
        ("② 시도만",             {"sidoCd": SEOUL}),
        ("③ 시도+과목",          {"sidoCd": SEOUL, "dgsbjtCd": PEDIA}),
        ("④ 시군구만",           {"sidoCd": SEOUL, "sgguCd": GANGNAM}),
        ("⑤ 시군구+과목",        {"sidoCd": SEOUL, "sgguCd": GANGNAM, "dgsbjtCd": PEDIA}),
        ("⑥ 시군구코드만(시도 없이)", {"sgguCd": GANGNAM}),
        ("⑦ 시군구+과목(줄까지)", {"sidoCd": SEOUL, "sgguCd": GANGNAM,
                                  "dgsbjtCd": PEDIA, "numOfRows": "3"}),
    ]
    got = []
    for name, p in shapes:
        q = dict(p); q.setdefault("numOfRows", "1"); q.setdefault("pageNo", "1")
        for timeout in (20, 45):            # 짧게 한 번, 안 되면 조금 길게 한 번
            sec, ans = one(q, timeout)
            print(f"  {name:<24} {sec:>5.1f}초  {ans}")
            got.append({"조합": name, "값": p, "초": sec, "답": ans, "기다린초": timeout})
            if "못 받음" not in ans:
                break
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hira_shape_probe.json").write_text(
        json.dumps({"두드린 것": got, "두드린 날": time.strftime("%Y-%m-%d")},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [g for g in got if "못 받음" not in g["답"]]
    print(f"\n답한 조합 {len({g['조합'] for g in ok})} / {len(shapes)}")
    print(f"→ {OUT/'hira_shape_probe.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
