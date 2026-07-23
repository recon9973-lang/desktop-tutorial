// location-auto 분석 PPT 템플릿 — 상단 DATA만 채우고 `node deck_template.js` 실행.
// npm install pptxgenjs (최초 1회). 색상 '#'·8자리 금지. LAYOUT_WIDE 고정. 한글 Malgun Gothic.
// 실행 후: validate.py 로 PASS 확인 → markitdown 로 내용 점검.

const DATA = {
  outFile: "/home/user/desktop-tutorial/docs/analysis/<시도><구>-<진료과>-상권분석.pptx",
  region: "<시도> <구>",            // 예: 대구 달서구
  cat: "다이어트·비만",             // 진료과
  asOf: "2026.03",                  // 인구·기관 기준월
  // ① 인구
  pop: "515,142", popRank: "대구 8개 구·군 중 1위", household: "239,483", perHH: "2.15",
  density: "≈ 8,300", trend: "517,059(2025.12) → 515,142 감소 지속", shareOfCity: "21.9",
  female: "263,101", male: "252,041", femalePct: 51.1, sexRatio: "95.8", femaleLead: "11,060",
  // ② 병원
  fac: "872", facShare: "20.6", cityFac: "4,225", per10k: "16.9",
  facTypes: { labels: ["의원","치과의원","한의원","병원"], values: [429,216,173,21] },
  uiHani: "2.5 : 1", uiHaniNote: "의원(429) : 한의원(173)",
  cluster: "상인동 129 > 감삼 83 > 월성 81 > 이곡 79",
  // ③ 의료수요(심평원 진료) — 없으면 medDemand:null 로 두면 슬라이드 생략
  medDemand: { obesity: "174", metabolic: "≈ 135,000",
    rows: [["본태성고혈압 (I10)","67,929"],["2형당뇨 (E11)","34,443"],["지질대사·고지혈 (E78)","32,723"]] },
  // ④ 연령(다이어트 소비지수, 피크=100) & 키워드 추이(분기)
  ageLabels: ["10대","20대","30대","40대","50대","60대"], ageVals: [6,35,78,100,53,14],
  kwQ: ["23Q1","23Q2","23Q3","23Q4","24Q1","24Q2","24Q3","24Q4","25Q1","25Q2","25Q3","25Q4","26Q1","26Q2"],
  kwSeries: [
    { name:"주사·삭센다·위고비", vals:[7.5,10.7,11.1,12,9.8,13.2,16.9,52.2,35.7,72.9,49.3,26.5,21.3,15.3] },
    { name:"일반 키워드", vals:[13.3,12.3,10.1,7.6,9.7,10.1,8.9,7.1,7.8,7.5,6.5,4.7,5.2,4.6] },
    { name:"한방", vals:[2.4,2.5,2.1,1.7,2.3,2.5,2.3,2,2.8,2.5,2,1.5,1.5,1.4] },
  ],
  // 경쟁 상위 샘플(search_local)
  compHani: [["더편한한의원","용산동"],["손모아한의원","진천동"],["미올한의원","상인동"]],
  compYang: [["대곡연세의원·가정의학과","두류동"],["웰리브의원","대곡동"],["더데이의원","월성동"]],
};

const pptxgen = require("pptxgenjs");
const p = new pptxgen(); p.layout = "LAYOUT_WIDE"; const W=13.3;
const INK="0F3B3A",TEAL="0E7C7B",MINT="2BB79A",CORAL="FF6B5B",PANEL="F1F6F5",LINE="D9E5E3",DARKTX="16302E",MUTED="5B6B6A",WHITE="FFFFFF",FSER="Cambria",FSAN="Malgun Gothic";
const D=DATA, src=`행안부(${D.asOf}) · 심평원 · Naver DataLab`;
function head(s,k,t){s.addText(k,{x:0.6,y:0.42,w:9,h:0.3,fontFace:FSAN,fontSize:12,bold:true,color:TEAL,charSpacing:2});s.addText(t,{x:0.6,y:0.68,w:12.1,h:0.7,fontFace:FSAN,fontSize:28,bold:true,color:DARKTX});s.addText(`VENOM · ${D.region} ${D.cat}`,{x:9.4,y:0.46,w:3.3,h:0.3,align:"right",fontFace:FSAN,fontSize:9,color:MUTED});}
function foot(s,n){s.addText(src,{x:0.6,y:7.05,w:9.5,h:0.3,fontFace:FSAN,fontSize:8,color:MUTED});s.addText(String(n),{x:12.4,y:7.05,w:0.5,h:0.3,align:"right",fontFace:FSAN,fontSize:9,color:MUTED});}
function card(s,x,y,w,h,num,unit,label,clr){s.addShape(p.ShapeType.roundRect,{x,y,w,h,rectRadius:0.09,fill:{color:WHITE},line:{color:LINE,width:1}});s.addText([{text:num,options:{fontFace:FSER,fontSize:30,bold:true,color:clr}},{text:unit?" "+unit:"",options:{fontFace:FSAN,fontSize:12,bold:true,color:clr}}],{x:x+0.05,y:y+0.16,w:w-0.1,h:0.65,align:"center",margin:0});s.addText(label,{x:x+0.12,y:y+h-0.62,w:w-0.24,h:0.5,align:"center",fontFace:FSAN,fontSize:10.5,color:MUTED,valign:"top"});}
let n=0;

// 1 표지
let s=p.addSlide(); s.background={color:INK};
s.addShape(p.ShapeType.rect,{x:0,y:0,w:W,h:0.14,fill:{color:CORAL}});
s.addText("MARKET INTELLIGENCE",{x:0.9,y:1.7,w:8,h:0.35,fontFace:FSAN,fontSize:13,bold:true,color:MINT,charSpacing:3});
s.addText(`${D.region}\n${D.cat} 진료 상권 분석`,{x:0.9,y:2.15,w:11.5,h:1.9,fontFace:FSAN,fontSize:42,bold:true,color:WHITE,lineSpacingMultiple:1.05});
s.addText("인구 · 병원 밀집도 · 남녀·연령 · 키워드",{x:0.92,y:4.35,w:11,h:0.5,fontFace:FSAN,fontSize:18,color:"CADCFC"});
[[D.pop,"인구 (해당 구 1위)"],[D.fac,`의료기관 (시의 ${D.facShare}%)`],["실측","행안부·심평원·DataLab"]].forEach((d,i)=>{const x=0.9+i*3.95;s.addText(d[0],{x,y:5.55,w:3.7,h:0.6,fontFace:FSER,fontSize:24,bold:true,color:MINT});s.addText(d[1],{x,y:6.2,w:3.7,h:0.4,fontFace:FSAN,fontSize:12,color:"9FBAB7"});});
s.addText("VENOM 병원마케팅 · 실측 기반 확정본",{x:0.9,y:6.85,w:11,h:0.3,fontFace:FSAN,fontSize:11,color:"7FA09D"});

// 2 인구(성별)
s=p.addSlide(); s.background={color:WHITE}; head(s,"① 인구 분석",`${D.region} · 여성 우세, 고밀도 정주 시장`);
s.addShape(p.ShapeType.roundRect,{x:0.6,y:1.85,w:4.15,h:4.7,rectRadius:0.12,fill:{color:INK}});
s.addText(`주민등록 인구 (${D.asOf})`,{x:0.85,y:2.1,w:3.7,h:0.4,fontFace:FSAN,fontSize:13,color:MINT});
s.addText(D.pop,{x:0.6,y:2.5,w:4.15,h:0.95,align:"center",fontFace:FSER,fontSize:44,bold:true,color:WHITE});
s.addText(D.popRank,{x:0.6,y:3.45,w:4.15,h:0.35,align:"center",fontFace:FSAN,fontSize:12,color:"CADCFC"});
s.addText([{text:`${D.household} 세대 `,options:{bold:true,color:WHITE}},{text:`(세대당 ${D.perHH}명)\n`,options:{color:"9FBAB7"}},{text:`밀도 ${D.density}명/㎢\n`,options:{bold:true,color:WHITE}},{text:D.trend,options:{color:"9FBAB7"}}],{x:0.85,y:4.15,w:3.7,h:2.2,fontFace:FSAN,fontSize:11.5,lineSpacingMultiple:1.35,valign:"top"});
s.addShape(p.ShapeType.roundRect,{x:4.95,y:1.85,w:7.75,h:2.25,rectRadius:0.1,fill:{color:WHITE},line:{color:LINE,width:1}});
s.addText("성별 구성",{x:5.2,y:2.05,w:7.2,h:0.4,fontFace:FSAN,fontSize:15,bold:true,color:DARKTX});
s.addText([{text:"여자  ",options:{fontSize:13,color:MUTED}},{text:D.female,options:{fontFace:FSER,fontSize:24,bold:true,color:CORAL}}],{x:5.2,y:2.5,w:3.6,h:0.5,margin:0,valign:"middle"});
s.addText([{text:"남자  ",options:{fontSize:13,color:MUTED}},{text:D.male,options:{fontFace:FSER,fontSize:24,bold:true,color:TEAL}}],{x:8.95,y:2.5,w:3.6,h:0.5,margin:0,valign:"middle"});
const bw=7.25,fw=bw*D.femalePct/100;
s.addShape(p.ShapeType.roundRect,{x:5.2,y:3.12,w:fw,h:0.42,rectRadius:0.05,fill:{color:CORAL}});
s.addShape(p.ShapeType.roundRect,{x:5.2+fw,y:3.12,w:bw-fw,h:0.42,rectRadius:0.05,fill:{color:TEAL}});
s.addText(`성비 ${D.sexRatio} · 여성이 ${D.femaleLead}명 더 많음`,{x:5.2,y:3.62,w:7.2,h:0.35,fontFace:FSAN,fontSize:11,italic:true,color:MUTED});
s.addShape(p.ShapeType.roundRect,{x:4.95,y:4.35,w:7.75,h:2.2,rectRadius:0.1,fill:{color:PANEL},line:{color:LINE,width:1}});
s.addText("마케팅 함의",{x:5.2,y:4.55,w:7.2,h:0.4,fontFace:FSAN,fontSize:15,bold:true,color:TEAL});
s.addText([{text:`여성 ${D.female} = 1차 타깃 모수 상한.  `,options:{bold:true,color:DARKTX}},{text:"주 소구층 여성 절대수가 최대.\n",options:{color:MUTED}},{text:"고밀·정주형  ",options:{bold:true,color:DARKTX}},{text:"→ 회차·패키지·재방문(LTV) 마케팅에 유리.",options:{color:MUTED}}],{x:5.2,y:4.95,w:7.25,h:1.5,fontFace:FSAN,fontSize:12,lineSpacingMultiple:1.15,valign:"top"});
foot(s,2);

// 3 병원 밀집도
s=p.addSlide(); s.background={color:WHITE}; head(s,"② 병원 밀집도","공급은 양방 우세 — 빈틈은 '마케팅'");
card(s,0.6,1.8,3.0,1.9,D.fac,"개",`${D.region} 요양기관 (심평원 ${D.asOf})`,TEAL);
card(s,3.75,1.8,3.0,1.9,D.facShare,"%",`시 전체 ${D.cityFac}개 중 점유율`,MINT);
card(s,6.9,1.8,3.0,1.9,D.per10k,"개","인구 1만 명당 기관",CORAL);
card(s,10.05,1.8,2.65,1.9,D.uiHani,"",D.uiHaniNote,INK);
s.addText("종별 기관 수",{x:0.6,y:3.9,w:5.7,h:0.35,fontFace:FSAN,fontSize:13,bold:true,color:DARKTX});
s.addChart(p.ChartType.bar,[{name:"기관수",labels:D.facTypes.labels,values:D.facTypes.values}],{x:0.55,y:4.3,w:5.75,h:2.25,barDir:"bar",chartColors:[CORAL,MINT,TEAL,INK],showTitle:false,showLegend:false,showValue:true,dataLabelPosition:"outEnd",dataLabelColor:DARKTX,dataLabelFontFace:FSAN,dataLabelFontSize:11,dataLabelFontBold:true,catAxisLabelColor:DARKTX,catAxisLabelFontFace:FSAN,catAxisLabelFontSize:12,valAxisHidden:true,valGridLine:{style:"none"},catGridLine:{style:"none"},barGapWidthPct:40,valAxisMaxVal:Math.max(...D.facTypes.values)*1.2});
s.addShape(p.ShapeType.roundRect,{x:6.5,y:4.0,w:6.2,h:2.55,rectRadius:0.1,fill:{color:PANEL},line:{color:LINE,width:1}});
s.addText("핵심 = 공급 아닌 '마케팅'의 빈틈",{x:6.75,y:4.18,w:5.7,h:0.4,fontFace:FSAN,fontSize:15,bold:true,color:TEAL});
s.addText([{text:"양방 의원이 한의원보다 많은데도 '검색' 상위는 한의원 점유 → 다수 양방 의원이 다이어트를 마케팅하지 않을 뿐.\n",options:{color:MUTED}},{text:"→ 기존 양방 의원의 포지셔닝(주사·처방·대사)이 곧 기회.\n",options:{bold:true,color:CORAL}},{text:`밀집: ${D.cluster}`,options:{color:MUTED}}],{x:6.75,y:4.6,w:5.75,h:1.9,fontFace:FSAN,fontSize:12,lineSpacingMultiple:1.12,valign:"top"});
foot(s,3);

// 4 의료수요(있을 때만)
if(D.medDemand){s=p.addSlide(); s.background={color:WHITE}; head(s,"③ 실측 의료 수요","비만은 아직 '병원 밖' — 의료화 갭이 기회");
s.addShape(p.ShapeType.roundRect,{x:0.6,y:1.9,w:5.55,h:1.95,rectRadius:0.12,fill:{color:INK}});
s.addText("비만(E66) 직접 진료",{x:0.85,y:2.08,w:5.1,h:0.35,fontFace:FSAN,fontSize:12,color:MINT});
s.addText([{text:D.medDemand.obesity,options:{fontFace:FSER,fontSize:48,bold:true,color:WHITE}},{text:"  명",options:{fontFace:FSAN,fontSize:18,color:"CADCFC"}}],{x:0.85,y:2.5,w:5.1,h:0.9,margin:0,valign:"middle"});
s.addText("병원에서 비만을 직접 치료받은 인원 — 극소수",{x:0.85,y:3.42,w:5.1,h:0.35,fontFace:FSAN,fontSize:11.5,italic:true,color:"9FBAB7"});
s.addShape(p.ShapeType.roundRect,{x:0.6,y:4.05,w:5.55,h:2.5,rectRadius:0.1,fill:{color:PANEL},line:{color:LINE,width:1}});
s.addText("대사질환 진료 배후",{x:0.85,y:4.22,w:5.1,h:0.35,fontFace:FSAN,fontSize:13,bold:true,color:TEAL});
s.addText([{text:D.medDemand.metabolic,options:{fontFace:FSER,fontSize:28,bold:true,color:DARKTX}},{text:" 명",options:{fontFace:FSAN,fontSize:14,color:MUTED}}],{x:0.85,y:4.6,w:5.1,h:0.55,margin:0,valign:"middle"});
D.medDemand.rows.forEach((r,i)=>{const yy=5.32+i*0.4;s.addText(r[0],{x:0.85,y:yy,w:3.4,h:0.36,valign:"middle",fontFace:FSAN,fontSize:12,color:DARKTX,margin:0});s.addText(r[1]+" 명",{x:4.05,y:yy,w:2.0,h:0.36,align:"right",valign:"middle",fontFace:FSAN,fontSize:12,bold:true,color:TEAL,margin:0});});
s.addShape(p.ShapeType.roundRect,{x:6.4,y:1.9,w:6.3,h:4.65,rectRadius:0.1,fill:{color:WHITE},line:{color:LINE,width:1}});
s.addText("갭 = 기회",{x:6.65,y:2.1,w:5.8,h:0.4,fontFace:FSAN,fontSize:16,bold:true,color:TEAL});
s.addText([{text:"검색 수요 ↔ 의료 전환의 갭\n",options:{bold:true,color:DARKTX,fontSize:14}},{text:"주사·시술 검색은 폭증하는데 비만 직접 진료는 극소수. 미개척 의료화 시장 선점 여지.\n\n",options:{color:MUTED}},{text:"대사질환 배후\n",options:{bold:true,color:DARKTX,fontSize:14}},{text:"체중감량으로 대사개선이 필요한 대량 모수 = 의학 비만치료 1차 타깃(남 40~50대).",options:{color:MUTED}}],{x:6.65,y:2.55,w:5.8,h:3.5,fontFace:FSAN,fontSize:12.5,lineSpacingMultiple:1.15,valign:"top"});
foot(s,4);}

// 5 경쟁 지형
s=p.addSlide(); s.background={color:WHITE}; head(s,"경쟁 지형 (샘플)","리뷰순 상위 · 읍면동 밀집 축");
function panel(x,title,clr,rows){s.addShape(p.ShapeType.roundRect,{x,y:1.85,w:5.85,h:3.3,rectRadius:0.1,fill:{color:WHITE},line:{color:LINE,width:1}});s.addShape(p.ShapeType.roundRect,{x,y:1.85,w:5.85,h:0.62,rectRadius:0.1,fill:{color:clr}});s.addText(title,{x:x+0.25,y:1.85,w:5.4,h:0.62,valign:"middle",fontFace:FSAN,fontSize:14,bold:true,color:WHITE,margin:0});rows.forEach((r,i)=>{const yy=2.68+i*0.6;s.addText(r[0],{x:x+0.25,y:yy,w:3.6,h:0.5,valign:"middle",fontFace:FSAN,fontSize:12.5,bold:true,color:DARKTX,margin:0});s.addText(r[1],{x:x+3.8,y:yy,w:1.8,h:0.5,align:"right",valign:"middle",fontFace:FSAN,fontSize:11,color:MUTED,margin:0});});}
panel(0.6,"한방 (검색 상위 점유)",TEAL,D.compHani);
panel(6.85,"양방 의원 (마케팅 공백)",CORAL,D.compYang);
s.addShape(p.ShapeType.roundRect,{x:0.6,y:5.35,w:12.1,h:1.05,rectRadius:0.1,fill:{color:INK}});
s.addText([{text:"입지  ",options:{bold:true,color:MINT}},{text:`밀집 ${D.cluster}. 양방 다이어트 브랜딩이 얇아 검색·브랜딩 선점 이익이 큼.`,options:{color:WHITE}}],{x:0.9,y:5.35,w:11.5,h:1.05,valign:"middle",fontFace:FSAN,fontSize:12.5,margin:0});
foot(s,5);

// 6 연령
s=p.addSlide(); s.background={color:WHITE}; head(s,"③ 연령 구조",`소비 코어 연령대 (${D.cat})`);
s.addChart(p.ChartType.bar,[{name:"소비지수",labels:D.ageLabels,values:D.ageVals}],{x:0.6,y:1.9,w:7.3,h:4.6,barDir:"col",chartColors:[MINT,MINT,TEAL,CORAL,TEAL,MINT],showTitle:false,showLegend:false,showValue:true,dataLabelPosition:"outEnd",dataLabelColor:DARKTX,dataLabelFontFace:FSAN,dataLabelFontSize:12,dataLabelFontBold:true,catAxisLabelColor:DARKTX,catAxisLabelFontFace:FSAN,catAxisLabelFontSize:12,valAxisHidden:true,valGridLine:{style:"none"},catGridLine:{style:"none"},barGapWidthPct:45,valAxisMaxVal:115});
s.addText("Naver DataLab 쇼핑 지수 (피크=100)",{x:0.6,y:6.35,w:7.3,h:0.3,fontFace:FSAN,fontSize:9,italic:true,color:MUTED});
s.addShape(p.ShapeType.roundRect,{x:8.2,y:1.9,w:4.5,h:4.6,rectRadius:0.1,fill:{color:PANEL},line:{color:LINE,width:1}});
s.addText("함의",{x:8.45,y:2.15,w:4,h:0.4,fontFace:FSAN,fontSize:15,bold:true,color:TEAL});
s.addText("코어 연령대에 맞춰 크리에이티브 축(건강·대사·신뢰 vs 체형·감성)을 분기. 성별은 여성 우세 + 남성 대사 세그먼트 이원화.",{x:8.45,y:2.6,w:4.05,h:3.6,fontFace:FSAN,fontSize:12.5,color:MUTED,lineSpacingMultiple:1.15,valign:"top"});
foot(s,6);

// 7 키워드 추이
s=p.addSlide(); s.background={color:WHITE}; head(s,"④ 키워드 트렌드","수요 이동 = 의학 시술어 중심 재편");
s.addChart(p.ChartType.line,D.kwSeries.map((k,i)=>({name:k.name,labels:D.kwQ,values:k.vals})),{x:0.6,y:1.95,w:9.0,h:4.4,chartColors:[CORAL,TEAL,MINT],lineSize:3,lineSmooth:true,showTitle:false,showLegend:true,legendPos:"t",legendColor:DARKTX,legendFontFace:FSAN,legendFontSize:11,catAxisLabelColor:MUTED,catAxisLabelFontFace:FSAN,catAxisLabelFontSize:10,valAxisLabelColor:MUTED,valAxisLabelFontFace:FSAN,valAxisLabelFontSize:10,valGridLine:{color:LINE,size:1},catGridLine:{style:"none"},valAxisMinVal:0});
s.addText("Naver DataLab 검색어 지수(분기, 최대=100)",{x:0.6,y:6.35,w:9,h:0.3,fontFace:FSAN,fontSize:9,italic:true,color:MUTED});
s.addShape(p.ShapeType.roundRect,{x:9.85,y:1.95,w:2.85,h:4.4,rectRadius:0.1,fill:{color:PANEL},line:{color:LINE,width:1}});
s.addText([{text:"핵심\n",options:{bold:true,color:TEAL,fontSize:14}},{text:"주사·시술어가 시장을 재편. 일반어는 하락 → 의학 포지션 선점 + 피크 선행 광고.",options:{color:MUTED,fontSize:12}}],{x:10.05,y:2.15,w:2.5,h:4,fontFace:FSAN,lineSpacingMultiple:1.15,valign:"top"});
foot(s,7);

// 8 출처
s=p.addSlide(); s.background={color:INK};
s.addShape(p.ShapeType.rect,{x:0,y:0,w:W,h:0.14,fill:{color:CORAL}});
s.addText("데이터 출처 · 신뢰성",{x:0.9,y:0.8,w:11,h:0.7,fontFace:FSAN,fontSize:28,bold:true,color:WHITE});
s.addText("원칙: 실측 > 추론 > 통계 날조 금지 — 미확정은 확정법 명시",{x:0.92,y:1.55,w:11.5,h:0.4,fontFace:FSAN,fontSize:13,color:MINT});
s.addText([{text:"인구  ",options:{bold:true,color:WHITE}},{text:`행안부 주민등록(${D.asOf})\n`,options:{color:"CADCFC"}},{text:"병원  ",options:{bold:true,color:WHITE}},{text:"심평원 요양기관 명부·진료통계\n",options:{color:"CADCFC"}},{text:"키워드  ",options:{bold:true,color:WHITE}},{text:"Naver DataLab·지역검색\n",options:{color:"CADCFC"}}],{x:0.9,y:2.4,w:11,h:3,fontFace:FSAN,fontSize:13,lineSpacingMultiple:1.6,valign:"top"});
s.addText("VENOM 병원마케팅 · 실측 기반",{x:0.9,y:6.7,w:11,h:0.35,fontFace:FSAN,fontSize:11,color:"7FA09D"});

p.writeFile({fileName:D.outFile}).then(f=>console.log("WROTE",f));
