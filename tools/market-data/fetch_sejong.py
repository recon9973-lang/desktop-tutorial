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


def main() -> int:
    have = show_keys()
    if have["SGIS_CONSUMER_KEY"] and have["SGIS_CONSUMER_SECRET"]:
        if try_sgis(os.environ["SGIS_CONSUMER_KEY"], os.environ["SGIS_CONSUMER_SECRET"]):
            return 0
    key = (os.environ.get("DATA_GO_KR_SERVICE_KEY") or os.environ.get("DATA_GO_KR_KEY") or "").strip()
    if key:
        try_portal(key)
    else:
        print("공공데이터포털 열쇠가 두 이름 모두 비어 있다 — 받을 수 없다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
