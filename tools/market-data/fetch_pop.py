#!/usr/bin/env python3
"""행정안전부 주민등록 인구를 **API 로** 받아 온다(러너 전용).

왜 만드나: 인구는 달마다 바뀐다. 손으로 파일을 올리면 그때뿐이고 다음 달이면 낡는다.
사장님 지시 2026-09-27: «인구는 계속 변하는 데이터인데, 파일로 올리는건 장기적 관점에서
허점이 많아. api 데이터 활용 방안을 마련해»

지금까지 인구는 ANSEO 사본에 들어 있는 파일을 읽어 쓰고 있다. 그 사본에 세종이 통째로
빠져 있어 세종만 손으로 채웠다. API 로 바꾸면 그 구멍도 메워지고 달마다 새로 받을 수 있다.

[실측 2026-09-26] `apis.data.go.kr/1741000/admmPpltnHhStus` 는 https/http × 경로 셋 ×
값 꼴 셋 = 열두 번 모두 무응답이었다. 그래서 **주소를 외워 쓰지 않고 두드려 찾는다.**

`--mode probe` 로 어느 주소가 답하는지 먼저 알아내고, 알아낸 대로 `--mode collect` 한다.
"""
import argparse, json, os, pathlib, re, sys, time, urllib.parse, urllib.request

OUT = pathlib.Path("data/market")
RAW = OUT / "raw"
KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
calls = 0


def get(url: str, timeout: int = 20, cap: int | None = 3000):
    global calls
    calls += 1
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, (body[:cap] if cap else body), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:cap or 3000], time.time() - t0
    except Exception as e:                                   # noqa: BLE001
        return 0, str(e).encode(), time.time() - t0


def k() -> str:
    return KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")


# ── 두드려 볼 곳 ────────────────────────────────────────────────────────────
# 셋으로 나눈다: ① 호스트가 살아 있나 ② 자료 목록을 물어볼 수 있나
# ③ 인구 자료 자체를 받을 수 있나. ①이 죽으면 ②③은 볼 것도 없다.
HOSTS = ["https://apis.data.go.kr", "https://api.odcloud.kr",
         "https://www.data.go.kr", "https://kosis.kr",
         "https://sgisapi.kostat.go.kr"]

# 파일 자료를 포털이 API 로 바꿔 주는 통로. 자료번호로 부른다.
#   15097972 지역별(행정동) 성별 연령별 주민등록 인구수  ← 나이대가 여기 있다
#   15108065 행정동별(통반단위) 주민등록 인구 및 세대현황 ← 동별 인구·남녀
#   15059351 공공데이터포털목록조회서비스              ← 주소를 «찾는» 데 쓴다
ODCLOUD = ["15097972", "15108065", "15107303", "15059351"]

# 기관이 직접 여는 통로. 앞 판에서 무응답이던 것도 한 번 더 본다(그때는 답이 없었다고만 안다).
AGENCY = [
    "https://apis.data.go.kr/1741000/admmPpltnHhStus/getAdmmPpltnHhStus",
    "https://apis.data.go.kr/1741000/admmSexdstnAgrdePpltnStus/getAdmmSexdstnAgrdePpltnStus",
    "https://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList",
]


def probe() -> int:
    print(f"열쇠 {'있음' if KEY else '없음'}\n")
    tried = []

    def note(무엇, url, st, body, sec, 메모=""):
        txt = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
        row = {"무엇": 무엇, "주소": url.replace(k(), "<열쇠>"), "http": st,
               "걸린초": round(sec, 1), "맛보기": " ".join(txt.split())[:300], "메모": 메모}
        tried.append(row)
        print(f"[{st:>3}] {sec:5.1f}s {무엇:<34} {row['맛보기'][:110]}")

    print("── ① 호스트가 답하나 ──")
    for h in HOSTS:
        st, b, s = get(h, timeout=12, cap=200)
        note(f"호스트 {h.split('//')[1]}", h, st, b, s)

    print("\n── ② 파일 자료를 API 로 (api.odcloud.kr) ──")
    for lid in ODCLOUD:
        for path in (f"/api/{lid}/v1", f"/api/{lid}/v1/uddi:"):
            url = f"https://api.odcloud.kr{path}?page=1&perPage=5&serviceKey={k()}"
            st, b, s = get(url)
            note(f"odcloud {lid}{path[len('/api/'+lid):]}", url, st, b, s)

    print("\n── ③ 기관이 직접 여는 통로 ──")
    for base in AGENCY:
        url = (f"{base}?serviceKey={k()}&type=json&pageNo=1&numOfRows=5"
               f"&pIndex=1&pSize=5")
        st, b, s = get(url, timeout=25)
        note(f"기관 {base.split('/')[-1]}", url, st, b, s)

    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "pop_probe.json").write_text(
        json.dumps({"시도한 것": tried, "두드린 날": time.strftime("%Y-%m-%d")},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [t for t in tried if t["http"] == 200]
    print(f"\n답한 곳 {len(ok)}개:")
    for t in ok:
        print(f"  {t['무엇']} — {t['맛보기'][:150]}")
    print(f"호출 {calls}회 → {RAW/'pop_probe.json'}")
    return 0


# 소개 화면에서 주소를 읽어 올 자료들. 번호는 포털 주소에 그대로 들어 있다.
PAGES = {
    "15097972": "지역별(행정동) 성별 연령별 주민등록 인구수",
    "15108065": "행정동별(통반단위) 주민등록 인구 및 세대현황",
    "15107303": "통계연보_지역별 주민등록인구",
    "15108092": "도로명별 주민등록 인구 및 세대현황",
    "15051059": "심평원_전국 병의원 및 약국 현황",
}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def find() -> int:
    """포털 **소개 화면에서 요청주소를 읽어 온다** — 외워 쓰지 않는다.

    [실측 2026-09-27 · 러너] `www.data.go.kr` 이 200 으로 답한다(2026-09-18 에는
    안 열렸다고 적혀 있었다 — 그때는 정말 안 열렸는지 다시 봐야 한다).
    화면 글 속에 `apis.data.go.kr/...` 과 `api.odcloud.kr/api/<번호>/v1/uddi:<긴번호>`
    가 그대로 들어 있어, 그것을 뽑아 두면 다음부터 기계가 바로 부를 수 있다.
    """
    found = {}
    for pk, nm in PAGES.items():
        got = {"이름": nm, "주소후보": [], "uddi": [], "오퍼레이션": []}
        for kind in ("openapi", "fileData"):
            url = f"https://www.data.go.kr/data/{pk}/{kind}.do"
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept-Language": "ko"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    st, html = r.status, r.read().decode("utf-8", "replace")
            except Exception as e:                          # noqa: BLE001
                print(f"  [{pk} {kind}] 못 열었다 — {e}"); continue
            got["주소후보"] += re.findall(r"https?://apis?\.(?:data\.go\.kr|odcloud\.kr)"
                                      r"[A-Za-z0-9_\-/.:]{4,120}", html)
            got["uddi"] += re.findall(r"uddi:[0-9a-fA-F\-]{8,60}", html)
            got["오퍼레이션"] += re.findall(r"\bget[A-Z][A-Za-z0-9]{3,40}\b", html)
            print(f"  [{st}] {pk} {kind} — 글자 {len(html):,} · "
                  f"주소 {len(got['주소후보'])} · uddi {len(got['uddi'])}")
        for key in ("주소후보", "uddi", "오퍼레이션"):
            got[key] = sorted(set(got[key]))[:12]
        found[pk] = got
        print(f"{pk} {nm}")
        for key in ("주소후보", "uddi", "오퍼레이션"):
            if got[key]:
                print(f"   {key}: {got[key]}")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "pop_endpoints.json").write_text(
        json.dumps({"찾은 것": found, "찾은 날": time.strftime("%Y-%m-%d"),
                    "어디서": "공공데이터포털 소개 화면(www.data.go.kr)"},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {RAW/'pop_endpoints.json'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="probe", choices=["probe", "find"])
    a = ap.parse_args()
    if a.mode == "find":
        return find()               # 이 길은 열쇠가 없어도 된다
    if not KEY:
        print("DATA_GO_KR_SERVICE_KEY 없음 — 중단"); return 2
    return probe()


if __name__ == "__main__":
    sys.exit(main())
