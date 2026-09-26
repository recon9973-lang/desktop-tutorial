#!/usr/bin/env python3
"""세종 인구를 공식 통로에서 받아 온다(러너 전용).

왜 필요한가: 행안부 행정동 인구 자료(ANSEO)에 세종이 통째로 빠져 있다.
세종은 시 아래 구·군이 없어 「시도/시군구/동」을 기대한 변환기가 24줄을 버린 것으로 보인다.
그래서 전국 252곳 가운데 세종만 인구가 «—» 다.

[실측 2026-09-26] jumin.mois.go.kr · kosis.kr · sejong.go.kr 은 이 컨테이너에서도
막혀 있다. apis.data.go.kr(400) 과 sgisapi.mods.go.kr(200) 은 열려 있다 — 열쇠가 있으면 된다.

먼저 **어느 열쇠가 들어와 있는지** 이름만 찍고(값은 절대 찍지 않는다), 있는 쪽으로 받는다.
"""
import json, os, pathlib, sys, urllib.parse, urllib.request

OUT = pathlib.Path("data/market")
NAMES = ["DATA_GO_KR_SERVICE_KEY", "DATA_GO_KR_KEY", "SGIS_CONSUMER_KEY",
         "SGIS_CONSUMER_SECRET", "KAKAO_REST_API_KEY", "NAVER_CLIENT_ID"]
# 공공데이터포털 쪽 후보 — 어느 것이 답하는지 두드려 본다(외워 쓰지 않는다).
CANDIDATES = [
    "https://apis.data.go.kr/1741000/admmSexdAgePpltnOfMm/getAdmmSexdAgePpltnOfMm",
    "https://apis.data.go.kr/1741000/stdgCtpvSexdAgePpltn/getStdgCtpvSexdAgePpltn",
    "https://apis.data.go.kr/1741000/RegistrationPopulation/getRegistrationPopulation",
    "https://apis.data.go.kr/1741000/ppltnSttus/getPpltnSttus",
    "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong",
]


def show_keys() -> dict:
    have = {n: bool(os.environ.get(n, "").strip()) for n in NAMES}
    print("열쇠 들어와 있나 (값은 찍지 않는다):")
    for n, ok in have.items():
        print(f"  {'있음' if ok else '없음 '}  {n}")
    return have


def get(url: str, timeout: int = 25):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()[:1200]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:600]
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode()


def try_sgis(key: str, sec: str) -> bool:
    st, body = get("https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json?"
                   + urllib.parse.urlencode({"consumer_key": key, "consumer_secret": sec}))
    print(f"[SGIS] 인증 {st} {body[:160].decode('utf-8','replace')}")
    try:
        tok = json.loads(body)["result"]["accessToken"]
    except Exception:  # noqa: BLE001
        return False
    for year in ("2025", "2024", "2023"):
        st, body = get("https://sgisapi.mods.go.kr/OpenAPI3/stats/population.json?"
                       + urllib.parse.urlencode({"accessToken": tok, "year": year,
                                                 "adm_cd": "36", "low_search": "0"}))
        print(f"[SGIS] 세종 인구 {year} → {st} {body[:300].decode('utf-8','replace')}")
        try:
            d = json.loads(body)
            rows = d.get("result") or []
            if rows:
                OUT.mkdir(parents=True, exist_ok=True)
                (OUT / "sejong_population.json").write_text(json.dumps(
                    {"출처": "통계청 SGIS 인구 통계", "기준연도": year, "행정구역코드": "36",
                     "원본": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"[SGIS] 받았다 → {OUT/'sejong_population.json'}")
                return True
        except Exception:  # noqa: BLE001
            pass
    return False


def try_portal(key: str) -> None:
    k = key if "%" in key else urllib.parse.quote(key, safe="")
    for base in CANDIDATES:
        st, body = get(f"{base}?serviceKey={k}&pageNo=1&numOfRows=1&type=json")
        head = body[:200].decode("utf-8", "replace").replace("\n", " ")
        print(f"[포털] {st} {base.split('/')[-1]:<40} {head}")


def try_url(base: str, key: str) -> bool:
    """사장님이 주신 요청주소로 받는다.

    [실측 2026-09-26] `https://apis.data.go.kr/1741000/admmPpltnHhStus` 는 아홉 번 모두
    **시간 초과**였다(오류 응답이 아니라 무응답). 같은 호스트의 다른 경로는 400 을 즉시
    돌려주므로 호스트가 죽은 것은 아니다. 그래서 잘못 짚은 자리를 넓게, **빠르게**
    훑는다 — 한 번에 10초만 기다리고 다음으로 넘어간다.
    """
    k = key if "%" in key else urllib.parse.quote(key, safe="")
    raw = base.split("?")[0].strip().rstrip("/")
    host_path = re.sub(r"^https?://", "", raw)
    seg = host_path.split("/")[-1]
    paths = [host_path, f"{host_path}/get{seg[0].upper()}{seg[1:]}", f"{host_path}/{seg}"]
    shapes = [
        {"pageNo": "1", "numOfRows": "10", "type": "json"},
        {"pageNo": "1", "numOfRows": "10", "_type": "json"},
        {"pageNo": "1", "numOfRows": "10", "type": "json", "srchFrYm": "202606",
         "srchToYm": "202606", "regSeCd": "1", "lv": "1"},
    ]
    hits = []
    for scheme in ("https", "http"):
        for pth in paths:
            for sh in shapes:
                url = f"{scheme}://{pth}?serviceKey={k}&" + urllib.parse.urlencode(sh)
                st, body = get(url, timeout=10)
                txt = body.decode("utf-8", "replace")
                flat = " ".join(txt.split())[:260]
                tag = pth.split("/1741000/")[-1]
                print(f"[{st:>3}] {scheme:<5} {tag:<42} {'+'.join(list(sh)[:3]):<28} {flat}")
                bad = any(w in txt.upper() for w in
                          ("NO_OPENAPI_SERVICE", "SERVICE_ACCESS_DENIED", "NOT_REGISTERED",
                           "APPLICATION_ERROR", "UNKNOWN_ERROR", "HTTP_ERROR", "TIMED OUT"))
                if st == 200 and not bad and len(txt) > 150:
                    OUT.mkdir(parents=True, exist_ok=True)
                    (OUT / "sejong_population_raw.json").write_text(txt, encoding="utf-8")
                    print(f"→ 받았다: {scheme}://{pth} · {urllib.parse.urlencode(sh)}")
                    return True
                if st and st != 0:
                    hits.append((st, scheme, pth, urllib.parse.urlencode(sh), flat))
    if hits:
        print("\n대답은 한 것들(무응답 아님):")
        for h in hits[:6]:
            print(f"  [{h[0]}] {h[1]}://{h[2]} · {h[3]}\n      {h[4]}")
    else:
        print("\n전부 무응답이다 — 주소나 길 자체가 닿지 않는다")
    return False


def main() -> int:
    have = show_keys()
    if have["SGIS_CONSUMER_KEY"] and have["SGIS_CONSUMER_SECRET"]:
        if try_sgis(os.environ["SGIS_CONSUMER_KEY"], os.environ["SGIS_CONSUMER_SECRET"]):
            return 0
    key = (os.environ.get("DATA_GO_KR_SERVICE_KEY") or os.environ.get("DATA_GO_KR_KEY") or "").strip()
    url = (os.environ.get("SEJONG_URL") or "").strip()
    if key and url:
        if try_url(url, key):
            return 0
        print("[요청주소] 그 주소로는 못 받았다 — 위 응답을 보고 다시 맞춘다")
        return 0
    if key:
        try_portal(key)
    else:
        print("공공데이터포털 열쇠가 두 이름 모두 비어 있다 — 받을 수 없다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
