# -*- coding: utf-8 -*-
"""index-series.json / raw-datalab.csv → 배포용 엑셀 워크북.
   집계값은 하드코딩하지 않고 전부 수식으로 걸어, 키워드를 추가하면 다시 계산되게 만든다."""
import json, csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as CL

D = json.load(open('index-series.json', encoding='utf-8'))
K, MONTHS = D['keywords'], D['meta']['months']
DEPTS  = ['치과', '한의원', '피부과', '정형외과', '안과', '내과', '성형외과']
METROS = ['서울', '부산', '대구', '인천', '광주', '대전', '울산']
GROUP_KO = {'metro': '지역명+진료과', 'city': '중소도시', 'district': '상권',
            'generic': '진료과단독', 'proc': '시술질환', 'control': '대조군',
            'extra': '기타진료과(참고)'}

# 월별지수 행 순서: 진료과 단위로 7개 도시가 붙어 있어야 계절지수를 구간 평균으로 뽑을 수 있다
order = [r + d for d in DEPTS for r in METROS]
order += [k for k in K if K[k]['group'] == 'city']
order += [k for k in K if K[k]['group'] == 'district']
order += [k for k in K if K[k]['group'] == 'generic']
order += [k for k in K if K[k]['group'] == 'proc']
order += [k for k in K if K[k]['group'] == 'control']
order += [k for k in K if K[k]['group'] == 'extra']
assert len(order) == len(K) and len(set(order)) == len(K), (len(order), len(K))
ROW = {k: i + 2 for i, k in enumerate(order)}
LAST = len(order) + 1   # 키워드지표 마지막 데이터 행          # 월별지수 · 키워드지표 · 계절_월별 공통 행번호

ARIAL   = 'Arial'
HFILL   = PatternFill('solid', fgColor='E9EDE9')
GFILL   = PatternFill('solid', fgColor='F5F1E6')
THIN    = Side(style='thin', color='D5DAD5')
BORDER  = Border(bottom=THIN)
IDX_FMT = '0.0'
PCT_FMT = '0.0%;[Red]-0.0%;-'
DT = {t['dept']: t for t in D['deptTotals']}
RT = {t['region']: t for t in D['regionTotals']}
DS = {x['dept']: x['seasonal'] for x in D['deptSeasonal']}
CORE_AVG = sum(t['avg'] for t in D['deptTotals'])          # 49개 키워드 3년평균 합
wb = Workbook()

def style_header(ws, row=1, upto=None):
    for c in ws[row][:upto]:
        c.font = Font(name=ARIAL, bold=True, size=9)
        c.fill = HFILL
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c.border = BORDER

CACHE = {}          # {시트명: {셀주소: 계산값}} — 저장 후 xlsx XML에 <v>로 주입한다

def put(ws, r, c, v, fmt=None, bold=False, size=10, align=None, color=None, cached=None):
    cell = ws.cell(row=r, column=c, value=v)
    if cached is not None and isinstance(v, str) and v.startswith('='):
        CACHE.setdefault(ws.title, {})[cell.coordinate] = cached
    cell.font = Font(name=ARIAL, bold=bold, size=size, color=color)
    if fmt: cell.number_format = fmt
    if align: cell.alignment = Alignment(horizontal=align)
    return cell

def widths(ws, spec):
    for col, w in spec.items(): ws.column_dimensions[col].width = w

# ─────────────────────────── 1. 읽기전 (범례·방법·한계)
ws = wb.active; ws.title = '읽기전'
widths(ws, {'A': 22, 'B': 116})
lines = [
    ('제목',        '전국 「지역명+진료과」 키워드 3년 검색수요 분석'),
    ('출처',        '네이버 데이터랩 검색어트렌드 API (PlayMCP NaverSearch-datalab_search)'),
    ('대상 기간',   '2023-09 ~ 2026-08 (36개월, 월간)'),
    ('수집일',      '2026-09-09'),
    ('키워드 수',   f'{len(K)}개 (API 요청 21회, 모든 요청에 앵커 「서울피부과」 동봉)'),
    ('', ''),
    ('■ 단위 — 반드시 먼저 읽을 것', ''),
    ('',  '이 파일의 모든 수치는 「월간 검색량(회)」이 아니라 상대지수다.'),
    ('',  '데이터랩은 절대 검색 횟수를 공개하지 않고, 요청 안의 최댓값을 100으로 둔 비율만 준다.'),
    ('',  '기준: 앵커 「서울피부과」의 36개월 평균 = 100. 지수 200이면 서울피부과의 약 2배가 검색됐다는 뜻이다.'),
    ('',  '절대 조회수·입찰가가 필요하면 네이버 검색광고 키워드도구(월간검색수 PC/모바일)를 별도로 붙여야 한다.'),
    ('', ''),
    ('■ 요청 간 스케일을 맞춘 방법', ''),
    ('',  '데이터랩은 요청마다 최댓값을 100으로 재조정하므로 요청이 다르면 값을 비교할 수 없다 (응답 = c × 실제검색량, c는 요청마다 다름).'),
    ('',  '21번의 요청 전부에 앵커 「서울피부과」를 한 자리 고정으로 넣고, 각 요청 응답을 그 요청의 앵커 36개월 평균으로 나눠 c를 소거했다.'),
    ('',  '결과: 지수 = 실제검색량 ÷ 서울피부과 평균검색량 × 100. 앵커 자신의 시계열은 보존되므로 수준 비교와 추이 비교를 동시에 할 수 있다.'),
    ('', ''),
    ('■ 연차 구분', ''),
    ('',  '1년차 = 2023.09–2024.08  |  2년차 = 2024.09–2025.08  |  3년차 = 2025.09–2026.08  |  3년 변화 = 3년차 ÷ 1년차 − 1'),
    ('', ''),
    ('■ 시트 구성', ''),
    ('',  '요약_진료과 / 요약_지역 — 7대 도시·7개 진료과 합산 (수식)'),
    ('',  '수요검증 — 「환자 검색 수요가 실제로 줄었나」에 답하는 4개 묶음 비교. 대조군은 의료와 무관한 기준선'),
    ('',  'TOP3 — 진료과별 대표 키워드 상위 3개'),
    ('',  '매트릭스 — 7개 진료과 × 7대 도시 규모·변화율'),
    ('',  '키워드지표 — 78개 키워드 전체 지표 (전부 월별지수를 참조하는 수식)'),
    ('',  '월별지수 — 78개 키워드 × 36개월 원지수 ★ 이 시트가 유일한 입력값이다'),
    ('',  '계절지수 / 계절_월별 — 월별 성수기·비수기 (연평균 100 기준)'),
    ('',  '원자료 — 데이터랩 API 원응답 98행 (앵커 포함, 정규화 전)'),
    ('', ''),
    ('■ 편집 안내', ''),
    ('',  '값을 직접 넣는 시트는 「월별지수」와 「원자료」뿐이다. 나머지 시트는 전부 수식이므로 덮어쓰지 말 것.'),
    ('',  '키워드를 추가하려면 월별지수 맨 아래에 행을 추가하고 키워드지표의 마지막 행 수식을 아래로 복사하면 된다.'),
    ('', ''),
    ('■ 한계', ''),
    ('',  '① 절대 검색량이 아니다.  ② PC+모바일 합산·전 연령/성별 값이라 세그먼트 분해 불가.'),
    ('',  '③ 「광주」는 광주광역시와 경기 광주시가 섞인다. 광주 수치는 별도 검증 후 사용을 권한다.'),
    ('',  '④ 지역명 키워드는 표본이 작아 단발 이슈에 크게 흔들린다 (키워드지표의 변동계수·스파이크 열로 확인).'),
    ('',  '⑤ 데이터랩은 일정 기준 미만 검색량을 0으로 처리하므로 초소형 키워드는 과소 집계될 수 있다.'),
    ('',  '⑥ 검색 수요만 다루며 경쟁 강도·입찰가·전환율·실제 내원은 포함하지 않는다.'),
    ('',  '⑦ 데이터랩 지수가 네이버 전체 트래픽 변화를 보정하는지는 공식 문서로 확인하지 못했다(문서 접근 불가).'),
    ('',  '   「수요검증」 시트의 대조군(날씨·지하철·환율·로또)이 그 확인을 대신한 간접 검증이다.'),
    ('', ''),
    ('■ 의료광고법', ''),
    ('',  '이 문서는 검색 수요 통계만 다루며 치료 효과·전후 비교·최상급 표현을 포함하지 않는다.'),
]
put(ws, 1, 1, '읽기 전에', bold=True, size=14)
r = 3
for label, text in lines:
    if label.startswith('■'):
        put(ws, r, 1, label, bold=True, size=11, color='0F5F52')
    elif label:
        put(ws, r, 1, label, bold=True, size=10)
    if text: put(ws, r, 2, text, size=10)
    r += 1
ws.sheet_view.showGridLines = False

# ─────────────────────────── 2. 월별지수 (유일한 입력 시트)
ws = wb.create_sheet('월별지수')
put(ws, 1, 1, '키워드'); put(ws, 1, 2, '분류')
for i, m in enumerate(MONTHS): put(ws, 1, 3 + i, m)
for k in order:
    r = ROW[k]
    put(ws, r, 1, k, size=10)
    put(ws, r, 2, GROUP_KO[K[k]['group']], size=10)
    for i, v in enumerate(K[k]['series']): put(ws, r, 3 + i, v, IDX_FMT)
style_header(ws)
widths(ws, {'A': 17, 'B': 14})
for i in range(36): ws.column_dimensions[CL(3 + i)].width = 9
ws.freeze_panes = 'C2'

MC = {i: CL(3 + i) for i in range(36)}          # 월 인덱스 → 열문자
Y1 = f'{MC[0]}{{r}}:{MC[11]}{{r}}'
Y2 = f'{MC[12]}{{r}}:{MC[23]}{{r}}'
Y3 = f'{MC[24]}{{r}}:{MC[35]}{{r}}'
ALL = f'{MC[0]}{{r}}:{MC[35]}{{r}}'

# ─────────────────────────── 3. 계절_월별 (도우미: 키워드별 1~12월 계절지수)
ws = wb.create_sheet('계절_월별')
put(ws, 1, 1, '키워드')
for m in range(1, 13): put(ws, 1, 1 + m, m)
for k in order:
    r = ROW[k]
    put(ws, r, 1, k, size=10)
    for m in range(1, 13):
        i0 = (m - 9) % 12                                    # 배열 0번 = 2023-09
        refs = ','.join(f'월별지수!{MC[i0 + off]}{r}' for off in (0, 12, 24))
        put(ws, r, 1 + m, f'=IFERROR(AVERAGE({refs})/키워드지표!$C{r}*100,"")', '0',
            cached=K[k]['seasonal'][m - 1])
style_header(ws)
widths(ws, {'A': 17})
for m in range(1, 13): ws.column_dimensions[CL(1 + m)].width = 7
ws.freeze_panes = 'B2'

# ─────────────────────────── 4. 키워드지표 (전부 수식)
ws = wb.create_sheet('키워드지표')
hdr = ['키워드', '분류', '3년 평균', '1년차\n2023.09–2024.08', '2년차\n2024.09–2025.08',
       '3년차\n2025.09–2026.08', '3년 변화', '변동계수', '스파이크\n최대÷중앙', '피크월', '지역', '진료과']
for c, h in enumerate(hdr, 1): put(ws, 1, c, h)
for k in order:
    r = ROW[k]
    g = K[k]['group']
    put(ws, r, 1, k, size=10)
    put(ws, r, 2, GROUP_KO[g], size=10)
    v = K[k]
    put(ws, r, 3, f'=AVERAGE(월별지수!{ALL.format(r=r)})', IDX_FMT, cached=v['avg'])
    put(ws, r, 4, f'=AVERAGE(월별지수!{Y1.format(r=r)})', IDX_FMT, cached=v['y1'])
    put(ws, r, 5, f'=AVERAGE(월별지수!{Y2.format(r=r)})', IDX_FMT, cached=v['y2'])
    put(ws, r, 6, f'=AVERAGE(월별지수!{Y3.format(r=r)})', IDX_FMT, cached=v['y3'])
    put(ws, r, 7, f'=IFERROR(F{r}/D{r}-1,"")', PCT_FMT, cached=v['g31'] / 100)
    put(ws, r, 8, f'=IFERROR(STDEVP(월별지수!{ALL.format(r=r)})/C{r},"")', '0.0%', cached=v['cv'] / 100)
    put(ws, r, 9, f'=IFERROR(MAX(월별지수!{ALL.format(r=r)})/MEDIAN(월별지수!{ALL.format(r=r)}),"")', '0.0"x"',
        cached=v['spike'])
    put(ws, r, 10, f'=INDEX(계절_월별!$B$1:$M$1,MATCH(MAX(계절_월별!B{r}:M{r}),계절_월별!B{r}:M{r},0))', '0"월"',
        cached=v['peakMonth'])
    # 지역/진료과 열은 요약 시트의 SUMIFS 키다. 'metro' 조합에만 채워 합산 누수를 막는다.
    put(ws, r, 11, k[:2] if g == 'metro' else '', size=10)
    put(ws, r, 12, k[2:] if g == 'metro' else '', size=10)
style_header(ws)
widths(ws, {'A': 17, 'B': 14, 'C': 10, 'D': 15, 'E': 15, 'F': 15,
            'G': 11, 'H': 11, 'I': 12, 'J': 9, 'K': 9, 'L': 11})
ws.freeze_panes = 'C2'
ws.auto_filter.ref = f'A1:L{1 + len(order)}'

MET = '키워드지표'
# 전체 열(A:A) 참조는 LibreOffice가 100만 행을 훑어 재계산이 끝나지 않는다. 데이터 범위로 못박는다.
def rng(col):  return f'{MET}!${col}$2:${col}${LAST}'
def mi(col, key):   # 키워드지표에서 값 끌어오기
    return f'=IFERROR(INDEX({rng(col)},MATCH({key},{rng("A")},0)),"")'

# ─────────────────────────── 5. 요약_진료과 / 요약_지역
def summary_sheet(name, label, items, match_col, tot):
    ws = wb.create_sheet(name)
    for c, h in enumerate([label, '3년 평균', '1년차\n2023.09–2024.08', '2년차\n2024.09–2025.08',
                           '3년차\n2025.09–2026.08', '3년 변화'], 1):
        put(ws, 1, c, h)
    for i, it in enumerate(items):
        r = i + 2
        put(ws, r, 1, it, bold=True, size=10)
        for c, src, key in ((2, 'C', 'avg'), (3, 'D', 'y1'), (4, 'E', 'y2'), (5, 'F', 'y3')):
            put(ws, r, c, f'=SUMIFS({rng(src)},{rng(match_col)},$A{r},'
                          f'{rng("B")},"지역명+진료과")', IDX_FMT, cached=tot[it][key])
        put(ws, r, 6, f'=IFERROR(E{r}/C{r}-1,"")', PCT_FMT, cached=tot[it]['g31'] / 100)
    style_header(ws)
    widths(ws, {'A': 12, 'B': 11, 'C': 15, 'D': 15, 'E': 15, 'F': 11})
    put(ws, len(items) + 3, 1, '7대 특·광역시 × 7개 진료과 49개 키워드만 합산한 값이다. 중소도시·상권·진료과단독 키워드는 제외.', size=9)
    return ws
summary_sheet('요약_진료과', '진료과', DEPTS, 'L', DT)
summary_sheet('요약_지역', '지역', METROS, 'K', RT)

# ─────────────────────────── 6. 수요검증
ws = wb.create_sheet('수요검증')
put(ws, 1, 1, '「환자 검색 수요가 실제로 줄었나」 — 성격이 다른 네 묶음 비교', bold=True, size=12)
put(ws, 2, 1, '대조군(의료와 무관한 생활 키워드)을 넣은 이유: 네이버 검색 트래픽 자체가 줄고 있다면 모든 키워드가 같이 내려가 의료 수요 감소처럼 보이기 때문이다.', size=9)
hr = 4
for c, h in enumerate(['묶음', '키워드', '1년차\n2023.09–2024.08', '2년차\n2024.09–2025.08',
                       '3년차\n2025.09–2026.08', '3년 평균', '3년 변화'], 1):
    put(ws, hr, c, h)
rows = [('지역명+진료과 (병원 탐색)', '49개 키워드 합산', None)]
rows += [('진료과 단독 (전국 관심도)', k, k) for k in [x['keyword'] for x in D['genericEach']]]
rows += [('시술·질환 (치료 의향)',    k, k) for k in [x['keyword'] for x in D['procEach']]]
rows += [('대조군 — 의료와 무관',     k, k) for k in [x['keyword'] for x in D['controlEach']]]
r = hr + 1
prev = None
for grp, name, key in rows:
    put(ws, r, 1, grp if grp != prev else '', bold=(grp != prev), size=10)
    if grp != prev: ws.cell(row=r, column=1).fill = GFILL
    prev = grp
    put(ws, r, 2, name, size=10, bold=(key is None))
    bk = D['buckets']['지역명+진료과 49개 합산']
    vals = ({'y1': bk['y1'], 'y2': bk['y2'], 'y3': bk['y3'], 'avg': CORE_AVG, 'g31': bk['g31']}
            if key is None else K[key])
    if key is None:
        for c, src, kk in ((3, 'D', 'y1'), (4, 'E', 'y2'), (5, 'F', 'y3'), (6, 'C', 'avg')):
            put(ws, r, c, f'=SUMIFS({rng(src)},{rng("B")},"지역명+진료과")', IDX_FMT, bold=True,
                cached=vals[kk])
    else:
        for c, src, kk in ((3, 'D', 'y1'), (4, 'E', 'y2'), (5, 'F', 'y3'), (6, 'C', 'avg')):
            put(ws, r, c, mi(src, f'$B{r}'), IDX_FMT, cached=vals[kk])
    put(ws, r, 7, f'=IFERROR(E{r}/C{r}-1,"")', PCT_FMT, bold=(key is None), cached=vals['g31'] / 100)
    r += 1
style_header(ws, hr)
widths(ws, {'A': 24, 'B': 16, 'C': 15, 'D': 15, 'E': 15, 'F': 11, 'G': 11})
notes = [
    '',
    '읽는 법',
    '① 대조군은 일률적으로 내려가지 않았다(로또·환율 큰 폭 상승). 따라서 네이버 지수 전반의 하향 편향은 없고, 의료 키워드 하락은 실제 신호다.',
    '② 시장 축소의 증거는 시술 키워드에 있다. 라식·임플란트는 지도앱으로 대체되지 않으므로 치료 의향 자체가 빠졌다고 읽는 편이 자연스럽다.',
    '③ 그런데 지역명+진료과 총량은 거의 그대로다. 줄어든 게 아니라 자리가 바뀌었다 — 내과·한의원에서 피부과·성형외과로, 수도권에서 지방으로.',
    '④ 대조군 안에서도 지하철·날씨가 내려간 것은 「검색창 → 앱」 이동 흔적이다. 「병원」 단독 검색의 낙폭이 이와 비슷한 점은 병원 찾기가 지도·플레이스로 옮겨갔을 가능성을 시사한다.',
    '',
    '주의 — 도수치료는 실손보험 제도 이슈로 2026년 6월 지수가 100까지 튄 예외 계열이라 추세로 읽으면 안 된다. 시술 키워드 4개는 진료과 전체를 대표하지 않는다.',
    '묶음끼리 절대 크기는 비교하지 말 것. 같은 행의 연차별 변화만 볼 것.',
]
for i, t in enumerate(notes):
    put(ws, r + 1 + i, 1, t, size=9, bold=(t == '읽는 법'))

# ─────────────────────────── 7. TOP3
ws = wb.create_sheet('TOP3')
put(ws, 1, 1, '진료과별 대표 키워드 상위 3개 (7대 특·광역시 안에서 · 도시 후보 수가 같아 진료과끼리 공정 비교)', bold=True, size=12)
hr = 3
for c, h in enumerate(['진료과', '순위', '키워드', '1년차\n2023.09–2024.08', '2년차\n2024.09–2025.08',
                       '3년차\n2025.09–2026.08', '3년 평균', '3년 변화', '피크월'], 1):
    put(ws, hr, c, h)
r = hr + 1
for g in D['top3']:
    for i, t in enumerate(g['rows']):
        put(ws, r, 1, g['dept'] if i == 0 else '', bold=(i == 0), size=10)
        if i == 0: ws.cell(row=r, column=1).fill = GFILL
        put(ws, r, 2, t['rank'], align='center')
        put(ws, r, 3, t['keyword'], size=10)
        for c, src, kk in ((4, 'D', 'y1'), (5, 'E', 'y2'), (6, 'F', 'y3'), (7, 'C', 'avg')):
            put(ws, r, c, mi(src, f'$C{r}'), IDX_FMT, cached=t[kk])
        put(ws, r, 8, f'=IFERROR(F{r}/D{r}-1,"")', PCT_FMT, cached=t['g31'] / 100)
        put(ws, r, 9, mi('J', f'$C{r}'), '0"월"', cached=t['peakMonth'])
        r += 1
    if g['outside']:
        put(ws, r, 3, '7대 도시 밖 참고 — ' + ' · '.join(
            f"{o['keyword']} {o['avg']}" for o in g['outside']), size=9)
        r += 1
style_header(ws, hr)
widths(ws, {'A': 11, 'B': 6, 'C': 46, 'D': 15, 'E': 15, 'F': 15, 'G': 11, 'H': 11, 'I': 9})
put(ws, r + 1, 1, '순위는 7대 도시 안에서만 매겼다. 중소도시·상권 키워드는 수집 범위가 진료과마다 달라 순위에 넣지 않고 참고로만 적었다.', size=9)

# ─────────────────────────── 8. 매트릭스
ws = wb.create_sheet('매트릭스')
def block(top, title, src_col, fmt, as_pct):
    put(ws, top, 1, title, bold=True, size=11, color='0F5F52')
    put(ws, top + 1, 1, '진료과')
    for j, m in enumerate(METROS): put(ws, top + 1, 2 + j, m)
    put(ws, top + 1, 9, '합계' if not as_pct else '')
    for i, d in enumerate(DEPTS):
        rr = top + 2 + i
        put(ws, rr, 1, d, bold=True, size=10)
        for j, m in enumerate(METROS):
            key = f'{CL(2 + j)}${top + 1}&$A{rr}'
            if as_pct:
                f3 = f'INDEX({rng("F")},MATCH({key},{rng("A")},0))'
                f1 = f'INDEX({rng("D")},MATCH({key},{rng("A")},0))'
                put(ws, rr, 2 + j, f'=IFERROR({f3}/{f1}-1,"")', fmt,
                    cached=D['matrix']['g31'][d][m] / 100)
            else:
                put(ws, rr, 2 + j, mi(src_col, key), fmt, cached=D['matrix']['avg'][d][m])
        if not as_pct:
            put(ws, rr, 9, f'=SUM(B{rr}:H{rr})', IDX_FMT, bold=True, cached=DT[d]['avg'])
    style_header(ws, top + 1, 9)
block(1, '① 수요 규모 — 3년 평균 지수 (서울피부과 36개월 평균 = 100)', 'C', IDX_FMT, False)
block(12, '② 3년 변화율 — 3년차 ÷ 1년차 − 1', None, PCT_FMT, True)
widths(ws, {'A': 12, **{CL(2 + j): 10 for j in range(7)}, 'I': 10})
put(ws, 21, 1, '셀은 「지역명+진료과」 키워드를 그대로 조회한다(예: 대전 + 피부과 = 대전피부과).', size=9)

# ─────────────────────────── 9. 계절지수
ws = wb.create_sheet('계절지수')
put(ws, 1, 1, '진료과 × 월 계절지수 — 7대 도시 평균, 각 진료과의 연평균 = 100', bold=True, size=12)
put(ws, 3, 1, '진료과')
for m in range(1, 13): put(ws, 3, 1 + m, f'{m}월')
put(ws, 3, 14, '피크월'); put(ws, 3, 15, '비수기')
for i, d in enumerate(DEPTS):
    r = 4 + i
    start = ROW[METROS[0] + d]
    put(ws, r, 1, d, bold=True, size=10)
    sea = DS[d]
    for m in range(1, 13):
        c = CL(1 + m)
        put(ws, r, 1 + m, f'=AVERAGE(계절_월별!{c}{start}:{c}{start + 6})', '0', cached=sea[m - 1])
    put(ws, r, 14, f'=INDEX($B$3:$M$3,MATCH(MAX(B{r}:M{r}),B{r}:M{r},0))',
        cached=f'{sea.index(max(sea)) + 1}월')
    put(ws, r, 15, f'=INDEX($B$3:$M$3,MATCH(MIN(B{r}:M{r}),B{r}:M{r},0))',
        cached=f'{sea.index(min(sea)) + 1}월')
style_header(ws, 3, 15)
widths(ws, {'A': 12, **{CL(1 + m): 7 for m in range(1, 13)}, 'N': 9, 'O': 9})
put(ws, 12, 1, '100보다 크면 성수기. 각 도시의 계절지수를 먼저 구하고 7개 도시를 단순평균한 값이다(계절_월별 시트).', size=9)

# ─────────────────────────── 10. 원자료
ws = wb.create_sheet('원자료')
put(ws, 1, 1, '요청'); put(ws, 1, 2, '키워드'); put(ws, 1, 3, '앵커')
for i, m in enumerate(MONTHS): put(ws, 1, 4 + i, m)
with open('raw-datalab.csv', encoding='utf-8') as fh:
    r = 2
    for row in csv.DictReader(fh):
        put(ws, r, 1, row['req'], size=10)
        put(ws, r, 2, row['keyword'], size=10)
        put(ws, r, 3, '앵커' if row['is_anchor'] == '1' else '', size=10, align='center')
        for i, v in enumerate(row['v'].split(',')): put(ws, r, 4 + i, float(v), '0.00')
        r += 1
style_header(ws)
widths(ws, {'A': 8, 'B': 17, 'C': 7})
for i in range(36): ws.column_dimensions[CL(4 + i)].width = 9
ws.freeze_panes = 'D2'
put(ws, r + 1, 1, '데이터랩 API 원응답(정규화 전). 요청마다 최댓값이 100이 되도록 재조정돼 있어 요청이 다르면 서로 비교할 수 없다.', size=9)
put(ws, r + 2, 1, '각 요청의 앵커 「서울피부과」 36개월 평균으로 나눈 결과가 「월별지수」 시트다.', size=9)

OUT = '네이버_지역진료과_키워드분석_2026-09.xlsx'
wb.save(OUT)

# ─────────────────────────── 계산값 주입
# openpyxl은 수식만 쓰고 캐시값을 비워 둔다. 이 환경의 LibreOffice는 파일을 열지 못해
# recalc를 돌릴 수 없으므로, 시트 XML의 <f> 뒤에 <v>를 직접 넣어 값이 바로 보이게 한다.
# 동시에 workbook.xml에 fullCalcOnLoad를 켜 실제 엑셀에서 열면 다시 계산되도록 한다.
import re, shutil, zipfile
from xml.sax.saxutils import escape

def inject(path, cache):
    zin = zipfile.ZipFile(path)
    names = zin.namelist()
    book = zin.read('xl/workbook.xml').decode('utf-8')
    rels = zin.read('xl/_rels/workbook.xml.rels').decode('utf-8')
    # 속성 순서에 의존하지 않도록 XML 파서로 관계를 읽는다
    import xml.etree.ElementTree as ET
    R = '{http://schemas.openxmlformats.org/package/2006/relationships}'
    S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    rid2tgt = {e.get('Id'): e.get('Target') for e in ET.fromstring(rels).findall(f'{R}Relationship')}
    sheet2xml = {}
    for e in ET.fromstring(book).find(f'{S}sheets'):
        tgt = rid2tgt[e.get(RID)].lstrip('/')
        sheet2xml[e.get('name')] = tgt if tgt.startswith('xl/') else 'xl/' + tgt
    assert set(cache) <= set(sheet2xml), set(cache) - set(sheet2xml)

    patched, hit, miss = {}, 0, 0
    for sheet, cells in cache.items():
        xml = zin.read(sheet2xml[sheet]).decode('utf-8')
        def sub(mo):
            nonlocal hit, miss
            attrs, formula = mo.group(1), mo.group(2)
            ref = re.search(r'r="([A-Z]+[0-9]+)"', attrs).group(1)
            if ref not in cells:
                miss += 1
                return mo.group(0)
            v = cells[ref]; hit += 1
            if isinstance(v, str):
                attrs = attrs if ' t="' in attrs else attrs + ' t="str"'
                return f'<c{attrs}><f>{formula}</f><v>{escape(v)}</v></c>'
            return f'<c{attrs}><f>{formula}</f><v>{v:.10g}</v></c>'
        # openpyxl은 <c ...><f>수식</f><v /></c> 형태로 쓴다 (빈 <v /> 자리표시자 포함)
        patched[sheet2xml[sheet]] = re.sub(
            r'<c([^>]*)><f>(.*?)</f>(?:<v\s*/>|<v></v>)?</c>', sub, xml).encode('utf-8')

    if 'fullCalcOnLoad' not in book:
        book = (book.replace('<calcPr', '<calcPr fullCalcOnLoad="1" ', 1) if '<calcPr' in book
                else book.replace('</workbook>', '<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>'))
        patched['xl/workbook.xml'] = book.encode('utf-8')

    tmp = path + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, patched.get(n, zin.read(n)))
    zin.close(); shutil.move(tmp, path)
    return hit, miss

hit, miss = inject(OUT, CACHE)
print(f'saved · sheets: {len(wb.sheetnames)} · 수식 캐시값 주입 {hit}건, 미주입 {miss}건')
assert miss == 0, f'{miss}개 수식에 계산값이 없다'

