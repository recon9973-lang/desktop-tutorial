# location-auto — 데이터 수집 가이드

모든 수집은 **실측 > 추론 > 날조 금지**. 막히면 총계만 잡고 정밀치는 사용자 업로드 요청. 출처는 ✅/🟡/🔴로.

## 도구 로드
```
ToolSearch: select:mcp__PlayMCP__NaverSearch-search_local,mcp__PlayMCP__NaverSearch-datalab_search,mcp__PlayMCP__NaverSearch-datalab_shopping_keyword_by_gender,mcp__PlayMCP__NaverSearch-datalab_shopping_keyword_by_age,mcp__PlayMCP__NaverSearch-get_current_korean_time,mcp__PlayMCP__NaverSearch-find_category
```
WebSearch는 기본 제공. WebFetch는 외부 원문에서 403(조직 egress) 자주 발생 → **재시도 금지**, 대체 경로 사용.

## ① 인구·남녀·세대 (행안부 주민등록)
- **1차(자동):** WebSearch `"<구>" 인구 <연도> 남자 여자 세대수` → 총인구 확보(예: superkts 스니펫). 요약기가 남/여 숫자는 잘 안 내보냄 → 총계까지만.
- **정밀(업로드):** 사용자에게 [행안부 주민등록통계](https://jumin.mois.go.kr/) → 시군구 → 행정동별 성별 CSV(또는 대구/각 구청 공공데이터) 업로드 요청.
- **CSV 파싱(동별 합산, cp949):**
```python
import csv
rows=[r for r in csv.reader(open(PATH,encoding="cp949",errors="replace"))][1:]
세대=총=남=여=외=0
for r in rows:
    if len(r)<8 or not r[3].strip().isdigit(): continue
    세대+=int(r[3]); 총+=int(r[4]); 남+=int(r[5]); 여+=int(r[6]); 외+=int(r[7])
assert 남+여+외==총            # 교차검증 필수
# 컬럼: 동,통,반,세대수,총인구(외국인포함),남,여,외국인,담당부서,기준일자
```
- 산출: 총인구·남·여·세대·성비(남/여×100)·여성비중·인구밀도(총÷면적㎢)·구 인구비중(구÷시도총).

## ② 병원 밀집도·종별 (심평원 요양기관 명부)
- **1차(자동):** WebSearch `<구> 의료기관 수 의원 한의원` → 총계.
- **정밀(업로드):** [심평원 보건의료빅데이터](https://opendata.hira.or.kr/) "병원·약국 현황(hospBasisList)" xlsx. 전국 전수라 구 필터로 카운트.
- **xlsx 파싱(구 필터·종별 카운트):**
```python
import openpyxl
from collections import Counter
ws=openpyxl.load_workbook(PATH,data_only=True,read_only=True)["hospBasisList"]
it=ws.iter_rows(values_only=True); next(it)  # 헤더
# 컬럼: 0암호기호 1기관명 3종별코드명 5시도코드명 7시군구코드명 8읍면동 ...
cnt=Counter(); emd=Counter(); sido=Counter()
for r in it:
    if not r or r[5] is None: continue
    if r[5]==SIDO: sido[str(r[3])]+=1                 # 시도 전체(비중 계산용)
    if TARGET_SGG in str(r[7] or ""):                 # 예: "대구달서구"
        cnt[str(r[3])]+=1; emd[str(r[8] or "")]+=1
# 산출: 총기관·의원·한의원·치과의원·병원 등, 의원:한의원 배수, 읍면동 밀집 순위, 구/시도 기관비중
```
- **핵심 해석:** 의원(양방) 수가 한의원보다 많아도 "다이어트 검색"은 한방이 점유하는 경우 → **공급이 아닌 "마케팅 공백"** 으로 프레이밍(양방 의원 마케팅 기회).

## ③ 의료 수요 (심평원 진료통계, 선택)
- 사용자가 주민 주상병별 진료인원 CSV 제공 시: 비만/대사 코드 추출로 **실수요** 실측.
```python
import csv
rows=list(csv.reader(open(PATH,encoding="cp949")))[1:]  # 진료년도,주소지,연령,주상병코드,주상병명,진료인원
tgt={"E66":"비만","E11":"2형당뇨","E78":"고지혈","I10":"고혈압","E88":"기타대사","E03":"갑상선저하"}
from collections import defaultdict
tot=defaultdict(int)
for r in rows:
    c=r[3][:3]
    if c in tgt and r[5].strip().isdigit(): tot[c]+=int(r[5])   # '*'는 마스킹→하한
```
- 인사이트: 비만(E66) 직접 진료 극소수 vs 대사질환 대량 → **"검색수요↔의료전환 갭 = 기회"** + 대사질환 배후 = 의학 비만치료 타깃.

## ④ 키워드·경쟁 (Naver DataLab + 지역검색)
- **키워드 추이:** `datalab_search`(timeUnit month, 24~42개월). 진료과별 키워드군 예:
  - 다이어트·비만: `["다이어트"]`, `["다이어트주사","삭센다","위고비"]`, `["다이어트한약","한방다이어트"]`, `["<시>다이어트","<시>비만클리닉"]`
  - 피부: `["여드름","기미","레이저토닝"]`, `["<시>피부과"]`
  - 성형: `["쌍꺼풀","코성형","리프팅"]`
  - 정형: `["도수치료","무릎","척추"]`
  - 치과: `["임플란트","교정","치아미백"]`
  - 한방: `["한약","추나","한방다이어트"]`
- **성별/연령:** `find_category`로 카테고리코드 → `datalab_shopping_keyword_by_gender/age`(f/m, 10~60). 각 시리즈 자기최대=100 정규화라 **절대비 단정 금지**(연령 비교는 동일시리즈라 가능).
- **경쟁 상위·읍면동 밀집:** `search_local`(sort:comment) — `"<구> <진료과>"`, `"<구> <핵심키워드>"`. **주의: total이 표시수(≤5)로 캡** → 개수 아님, "상위 샘플"로만. 위치(읍면동) 수집.

## 출처 3등급 표기
- ✅ 실측: 위 파싱·DataLab 지수·search_local 샘플.
- 🟡 정성/추정: 업계 통상(수요 계절성·여초 경향 등) — "추정" 명시.
- 🔴 미실측: 업로드 못 받은 정밀치(예: 여성×연령 코어, f:m 절대비) — 비우고 확정법 명시.
