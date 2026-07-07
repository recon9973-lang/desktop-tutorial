/*!
 * VENOM 용어사전 — SEO · AI · 마케팅 3종 데이터 + 렌더/필터
 * (사전 전환 · 초성 ㄱㄴㄷ · ABC · 카테고리 · 검색)
 * 사용: <div id="glossary-root"></div> 후 Glossary.mount('glossary-root')
 */
(function (root) {
  'use strict';

  // 사전(3종). 각 카테고리는 dict 로 소속 사전을 가진다.
  var DICTS = {
    seo:       { label: 'SEO 용어사전' },
    ai:        { label: 'AI 용어사전' },
    marketing: { label: '마케팅 용어사전' }
  };

  var CATS = {
    // ── SEO ───────────────────────────────
    basic:     { label: '기본 용어',  color: '#533afd', dict: 'seo' },
    engine:    { label: '검색엔진',   color: '#0ea5e9', dict: 'seo' },
    keyword:   { label: '키워드',     color: '#16a34a', dict: 'seo' },
    technical: { label: '테크니컬',   color: '#ea580c', dict: 'seo' },
    link:      { label: '링크빌딩',   color: '#9333ea', dict: 'seo' },
    optimize:  { label: '최적화',     color: '#e11d48', dict: 'seo' },
    // ── AI ────────────────────────────────
    ai_basic:  { label: 'AI 기본',    color: '#0d9488', dict: 'ai' },
    ai_geo:    { label: 'GEO·AEO',    color: '#0891b2', dict: 'ai' },
    ai_tech:   { label: 'AI 기술',    color: '#7c3aed', dict: 'ai' },
    // ── 마케팅 ─────────────────────────────
    mkt_metric:   { label: '지표·측정', color: '#dc2626', dict: 'marketing' },
    mkt_channel:  { label: '채널·매체', color: '#2563eb', dict: 'marketing' },
    mkt_strategy: { label: '전략·전환', color: '#d97706', dict: 'marketing' }
  };

  // [ko, en, def, cat, dict]  (dict 생략 시 'seo')
  var TERMS = [
    // ═══════════════ SEO 용어사전 ═══════════════
    ['검색엔진 최적화','SEO','검색엔진에서 찾기 쉽도록 사이트를 개선하는 프로세스.','basic','seo'],
    ['검색 엔진','Search engine','구글, 야후, 네이버와 같이 정보를 찾아주는 엔진.','basic','seo'],
    ['SERP','SERP','Search Engine Results Pages의 약자로 검색엔진 결과 페이지를 의미.','basic','seo'],
    ['온페이지 SEO','on-page SEO','소유하고 있는 웹사이트상에서 수행하는 최적화 작업.','basic','seo'],
    ['오프페이지 SEO','Off-page SEO','해당 웹사이트가 아닌 다른 공간에서 이루어지는 최적화 작업.','basic','seo'],
    ['온서프 SEO','on-SERP SEO','검색결과 페이지에서 이루어지는 최적화 작업.','basic','seo'],
    ['블랙햇 SEO','Black hat SEO','검색엔진의 정책에 반하는 SEO 작업.','basic','seo'],
    ['화이트햇 SEO','White hat SEO','검색엔진이 권장하는 방식의 SEO 작업.','basic','seo'],
    ['그레이햇 SEO','Grey hat SEO','블랙햇과 화이트햇의 경계에 있는 SEO 작업.','basic','seo'],
    ['크롤링','Crawling','신규 또는 업데이트된 웹페이지를 찾는 프로세스.','basic','seo'],
    ['피쳐드 스니펫','Featured snippets','특정 검색어에 제공되는 검색결과 상위의 오가닉 답변 박스.','basic','seo'],
    ['이미지 캐러셀','Image carousels','특정 검색결과에 보여지는 좌우 스크롤형 이미지 모음집.','basic','seo'],
    ['인덱싱','Indexing','수집 페이지를 분석한 후 빠르게 찾아볼 수 있도록 저장하는 작업.','basic','seo'],
    ['KPI','KPI','Key Performance Indicator의 약자로 목표 달성 성과를 객관적으로 평가하는 핵심 기준.','basic','seo'],
    ['로컬 팩','Local pack','검색어 주제와 검색자의 지리적 위치를 고려한 위치 기반 결과.','basic','seo'],
    ['오가닉','Organic','유료 광고가 아닌 자연적으로 얻어진 검색결과 순위.','basic','seo'],
    ['관련 질문','People Also Ask','검색결과에 보여지는 드롭다운 형태의 연관 추가 질문 모음.','basic','seo'],
    ['쿼리','Query','사용자가 검색창에 입력하는 검색어.','basic','seo'],
    ['랭킹','Ranking','검색어에 대한 연관순 검색결과 나열.','basic','seo'],
    ['트래픽','Traffic','웹사이트로의 방문 유입.','basic','seo'],
    ['URL','URL','Uniform Resource Locators의 약자로 콘텐츠의 주소·위치.','basic','seo'],

    ['알고리즘','Algorithms','검색 의도에 가장 적합한 결과를 전달하기 위해 정보를 채굴·정렬하는 프로세스·공식.','engine','seo'],
    ['크롤러','Crawler','스파이더·로봇으로 불리며 웹 페이지를 수집·색인 생성하는 자동 소프트웨어.','engine','seo'],
    ['크롤 버짓','Crawl budget','검색엔진 수집봇이 웹사이트에서 평균적으로 수집하는 페이지 수.','engine','seo'],
    ['페이지 랭크','PageRank','구글 검색 결과에서 웹페이지 순위를 정하는 구글의 알고리즘.','engine','seo'],
    ['색인','Index','제공할 가치가 있는 콘텐츠를 선별해 모아놓은 거대한 데이터베이스.','engine','seo'],
    ['2xx 상태 코드','2xx status codes','서버 요청 처리 성공 응답(상태) 코드.','engine','seo'],
    ['301 리디렉션','301 redirect','도메인·URL을 영구적으로 변경할 때 사용하는 리디렉션.','engine','seo'],
    ['302 리디렉션','302 redirect','페이지·사이트를 일시적으로 옮길 때 사용하는 리디렉션.','engine','seo'],
    ['404 에러','404 error','요청한 파일이 없어 불러올 수 없을 때 표시하는 에러.','engine','seo'],
    ['5xx 상태 코드','5xx status codes','서버 오류로 인한 요청 처리 불가 상태 코드.','engine','seo'],
    ['캐싱','Caching','웹페이지의 저장본.','engine','seo'],
    ['카페인','Caffeine','구글의 색인 시스템으로 수집된 웹 콘텐츠의 모음집.','engine','seo'],
    ['클로킹','Cloaking','검색엔진과 방문자에게 서로 다른 콘텐츠를 보여주는 편법.','engine','seo'],
    ['구글 서치 콘솔','Google Search Console','구글이 사이트를 어떻게 인식하는지 점검하는 관리자용 무료 툴.','engine','seo'],
    ['HTML','HTML','Hypertext markup language의 약자로 웹 페이지를 만드는 데 쓰이는 언어.','engine','seo'],
    ['내부 링크','Internal links','같은 웹사이트의 다른 페이지로 이동시키는 링크.','engine','seo'],
    ['자바스크립트','JavaScript','웹 페이지에 행동 요소를 추가하는 프로그래밍 언어.','engine','seo'],
    ['노인덱스 태그','NoIndex tag','검색엔진에게 특정 페이지를 색인하지 말라고 알려주는 메타 태그.','engine','seo'],
    ['로봇 배제 표준','Robots.txt','검색엔진 로봇의 접근을 제어하고 사이트맵 위치를 알려주는 규약.','engine','seo'],
    ['사이트 맵','Sitemap.xml','웹사이트 내의 모든 페이지들을 나열한 파일.','engine','seo'],

    ['키워드 경쟁지수','Keyword Difficulty','특정 키워드를 사용하는 경쟁자가 얼마나 많은지 숫자로 나타낸 수치.','keyword','seo'],
    ['롱테일 키워드','Long-tail keywords','검색량은 적지만 검색의도가 구체적으로 표현된 키워드.','keyword','seo'],
    ['검색량','Search volume','해당 키워드를 얼마나 검색했는지 보여주는 수치.','keyword','seo'],
    ['시드 키워드','Seed keywords','제공하는 제품·서비스를 설명하는 기본적인 단어.','keyword','seo'],
    ['LSI 키워드','LSI keywords','Latent Semantic Indexing, 특정 주제와 밀접하게 관련되어 자주 쓰이는 단어.','keyword','seo'],
    ['키워드 카니발리제이션','Keyword cannibalization','여러 콘텐츠가 동일 키워드로 경쟁해 어느 것도 상위가 아닌 상태.','keyword','seo'],

    ['오픈 그래프','Open Graph Protocol','페이스북 등에서 웹사이트의 디테일한 정보를 제공하게 하는 기능.','technical','seo'],
    ['트위터 카드','Twitter card','트위터에서 링크 공유 시 글·이미지를 미리보기로 보는 기능.','technical','seo'],
    ['이미지 대체 텍스트','Image alt text','웹 수집봇에게 이미지를 설명하는 문자열.','technical','seo'],
    ['앵커 텍스트','Anchor text','링크가 삽입된 텍스트.','technical','seo'],
    ['이미지 사이트 맵','Image sitemap','웹사이트에 업로드된 이미지의 URL만 나열한 파일.','technical','seo'],
    ['키워드 스터핑','Keyword stuffing','같은 키워드를 의도적으로 반복하는 정책 위반 작업.','technical','seo'],
    ['타이틀 태그','Title tag','검색결과에서 페이지의 제목을 보여주는 HTML 태그.','technical','seo'],
    ['메타 디스크립션','Meta descriptions','웹페이지에 대한 요약 설명글.','technical','seo'],
    ['보안 프로토콜','Security Protocol(HTTPS)','HTTP 보안 강화 버전으로 SSL·TLS로 세션 데이터를 암호화.','technical','seo'],
    ['캐노니컬 태그','Rel=canonical','원본 및 중복 URL 주소를 검색엔진에게 알려주는 태그.','technical','seo'],
    ['SSL','SSL','Secure Sockets Layer, 서버·브라우저 간 데이터를 암호화하는 보안 기술.','technical','seo'],
    ['썸네일','Thumbnails','큰 이미지의 작은 버전.','technical','seo'],
    ['AMP','AMP','Accelerated Mobile Pages, 더 빠른 로딩을 제공하는 페이지 복사본.','technical','seo'],
    ['브라우저','Browser','웹에서 정보를 얻을 수 있게 하는 소프트웨어(크롬·익스플로러 등).','technical','seo'],
    ['서브 도메인','Subdomain','상위 도메인의 하위에 있는 독립적인 웹사이트.','technical','seo'],
    ['서브 폴더','Subfolder','루트 폴더 하위에 속한 폴더.','technical','seo'],
    ['ccTLD','ccTLD','country code top level domain, 특정 국가 관련 도메인(.kr·.uk 등).','technical','seo'],
    ['CSS','CSS','Cascading Style Sheet, 웹 페이지의 디자인 요소를 설정하는 언어.','technical','seo'],
    ['Hreflang','Hreflang','문서의 언어 및 지역을 지정하는 HTML 메타 요소.','technical','seo'],
    ['IP 주소','IP address','Internet Protocol, 네트워크 상 컴퓨터의 고유 주소.','technical','seo'],
    ['모바일 중심 색인','Mobile-first indexing','모바일 버전 수집봇으로 모바일 페이지를 중점 크롤링·색인하는 구글 방식.','technical','seo'],
    ['렌더링','Rendering','코드를 사용자가 볼 수 있는 비주얼 형식으로 변환하는 프로세스.','technical','seo'],
    ['반응형 웹 디자인','Responsive design','각 기기에 최적화된 사이즈로 변하는 구글 권장 웹 디자인.','technical','seo'],
    ['리치 스니펫','Rich snippet','이미지·비디오·FAQ 등이 추가되어 개선된 검색결과(리치 결과).','technical','seo'],
    ['구조화된 데이터','Structured Data','검색엔진이 콘텐츠를 더 잘 이해하도록 조직화해 제공하는 데이터.','technical','seo'],
    ['코어 웹 바이탈','Core Web Vitals','LCP·INP·CLS 3지표로 페이지 로딩·반응·시각 안정성을 측정하는 구글의 핵심 웹 지표.','technical','seo'],

    ['도메인 점수','Domain Authority','DA, 웹사이트가 상위 랭킹에 오를 가능성을 예측한 점수.','link','seo'],
    ['백링크','Backlinks','다른 도메인의 사이트에서 해당 페이지로 연결된 링크.','link','seo'],
    ['링크 주스','Link Juice','하이퍼링크를 통해 다른 사이트로 전달하는 가치·권력.','link','seo'],
    ['노팔로우 링크','rel=nofollow','링크 주스를 제공하지 않고 검색 순위에 기여하지 않는 링크.','link','seo'],
    ['팔로우 링크','DoFollow links','모든 링크의 기본 상태로 링크 주스를 제공하는 링크.','link','seo'],
    ['구글 애널리틱스','Google Analytics','사이트와 사용자의 상호작용 인사이트를 제공하는 구글 무료 툴.','link','seo'],
    ['링크 빌딩','Link building','다른 사이트로부터 방문자 유입 링크를 얻어 권위를 높이는 작업.','link','seo'],

    ['이탈율','Bounce rate','사이트를 방문한 후 상호작용 없이 이탈한 비율.','optimize','seo'],
    ['채널','Channel','소셜미디어·자연검색 등 유입을 얻기 위한 다양한 수단.','optimize','seo'],
    ['클릭율','Click-through rate','CTR, 노출 대비 얻은 URL 클릭수의 비율.','optimize','seo'],
    ['전환율','Conversion rate','유입된 방문자 수 대비 전환수의 비율.','optimize','seo'],
    ['구글 애널리틱스 목표','GA goals','구글 애널리틱스로 전환율을 추적하기 위해 설정하는 목표.','optimize','seo'],
    ['구글 태그 관리자','Google Tag Manager','웹사이트의 여러 트래킹 코드를 관리하는 구글 무료 툴.','optimize','seo'],
    ['구글봇','Googlebot','구글의 웹 수집봇.','optimize','seo'],
    ['프루닝','Pruning','부진한 콘텐츠를 버려 웹사이트 전체 퀄리티를 높이는 작업.','optimize','seo'],
    ['서치 트래픽','Search traffic','구글과 같은 검색엔진을 통해 유입된 웹사이트 방문.','optimize','seo'],
    ['페이지 체류시간','Time on page','사용자가 한 페이지에 체류하는 시간.','optimize','seo'],
    ['UTM 코드','UTM code','Urchin tracking module, URL 끝에 삽입해 유입 경로를 추적하는 코드.','optimize','seo'],
    ['E-E-A-T','E-E-A-T','경험·전문성·권위성·신뢰성, 구글이 YMYL 콘텐츠 품질을 평가하는 기준.','optimize','seo'],

    // ═══════════════ AI 용어사전 ═══════════════
    ['생성형 AI','Generative AI','텍스트·이미지·음성 등 새로운 콘텐츠를 스스로 만들어내는 인공지능. ChatGPT·Gemini 등이 대표적.','ai_basic','ai'],
    ['대규모 언어모델','LLM','Large Language Model, 방대한 텍스트로 학습해 사람처럼 언어를 이해·생성하는 AI 모델.','ai_basic','ai'],
    ['프롬프트','Prompt','생성형 AI에게 원하는 결과를 얻기 위해 입력하는 명령·질문 문장.','ai_basic','ai'],
    ['프롬프트 엔지니어링','Prompt engineering','AI가 더 정확하고 유용한 답을 내도록 프롬프트를 설계·개선하는 기법.','ai_basic','ai'],
    ['할루시네이션','Hallucination','AI가 사실이 아닌 내용을 그럴듯하게 지어내는 현상. 의료 정보에서 특히 주의가 필요.','ai_basic','ai'],
    ['챗봇','Chatbot','사람과 대화하듯 질문에 답하고 상담·예약을 돕는 AI 대화형 프로그램.','ai_basic','ai'],
    ['AI 에이전트','AI Agent','목표를 스스로 계획하고 도구를 사용해 여러 단계를 자동 수행하는 AI.','ai_basic','ai'],
    ['멀티모달','Multimodal','텍스트·이미지·음성·영상 등 여러 형태의 데이터를 함께 이해·생성하는 AI 능력.','ai_basic','ai'],

    ['GEO','GEO','Generative Engine Optimization, 생성형 AI가 병원·브랜드를 추천·인용하도록 최적화하는 전략.','ai_geo','ai'],
    ['AEO','AEO','Answer Engine Optimization, AI 답변 엔진이 우리 콘텐츠를 답변으로 채택하도록 최적화하는 작업.','ai_geo','ai'],
    ['AI 오버뷰','AI Overviews','구글 검색 상단에 AI가 요약해 보여주는 생성형 답변 영역. 노출 시 브랜드 신뢰도가 크게 상승.','ai_geo','ai'],
    ['시맨틱 검색','Semantic search','단어의 표면적 일치가 아닌 검색 의도와 문맥의 의미를 이해해 결과를 제공하는 검색.','ai_geo','ai'],
    ['엔티티','Entity','사람·장소·브랜드·개념 등 검색엔진과 AI가 하나의 대상으로 인식하는 개체.','ai_geo','ai'],
    ['지식 그래프','Knowledge Graph','엔티티와 그 관계를 연결해 구글이 정보를 이해하는 데 쓰는 지식 데이터베이스.','ai_geo','ai'],
    ['제로클릭 검색','Zero-click search','검색결과나 AI 답변만으로 정보가 해결돼 사이트를 클릭하지 않고 끝나는 검색.','ai_geo','ai'],
    ['시맨틱 마크업','Semantic markup','AI·검색엔진이 콘텐츠의 의미를 파악하도록 구조화 데이터로 표시하는 작업.','ai_geo','ai'],

    ['RAG','RAG','Retrieval-Augmented Generation, 외부 문서를 검색해 근거로 삼아 답변 정확도를 높이는 기법.','ai_tech','ai'],
    ['임베딩','Embedding','단어·문장의 의미를 숫자 벡터로 변환해 AI가 유사도를 계산하도록 하는 표현.','ai_tech','ai'],
    ['벡터 데이터베이스','Vector database','임베딩 벡터를 저장하고 의미가 비슷한 데이터를 빠르게 검색하는 데이터베이스.','ai_tech','ai'],
    ['파인튜닝','Fine-tuning','사전학습된 AI 모델을 특정 도메인·업무 데이터로 추가 학습시켜 전문화하는 작업.','ai_tech','ai'],
    ['토큰','Token','AI가 텍스트를 처리하는 최소 단위. 단어·글자 조각으로 나뉘며 사용량·비용의 기준이 됨.','ai_tech','ai'],
    ['컨텍스트 윈도우','Context window','AI가 한 번에 기억·처리할 수 있는 토큰(문맥)의 최대 범위.','ai_tech','ai'],
    ['파운데이션 모델','Foundation model','대규모 데이터로 사전학습돼 다양한 작업에 두루 응용되는 기반 AI 모델.','ai_tech','ai'],
    ['파라미터','Parameter','모델이 학습으로 조정하는 내부 가중치. 수가 많을수록 표현력이 커지는 경향.','ai_tech','ai'],

    // ═══════════════ 마케팅 용어사전 ═══════════════
    ['CTR','Click-Through Rate','클릭률. 광고·검색결과 노출 대비 클릭이 발생한 비율(클릭수 ÷ 노출수).','mkt_metric','marketing'],
    ['CPC','Cost Per Click','클릭당 비용. 광고 클릭 1회에 지불하는 평균 단가.','mkt_metric','marketing'],
    ['CPM','Cost Per Mille','노출 1,000회당 광고 비용. 브랜드 인지도 캠페인의 대표 과금 방식.','mkt_metric','marketing'],
    ['CPA','Cost Per Action','전환(예약·구매 등) 1건을 얻는 데 든 광고 비용.','mkt_metric','marketing'],
    ['ROAS','Return On Ad Spend','광고비 대비 매출. 광고에 쓴 1원이 만든 매출을 나타내는 핵심 효율 지표.','mkt_metric','marketing'],
    ['ROI','Return On Investment','투자 대비 수익. 마케팅에 투입한 비용이 만든 순이익의 비율.','mkt_metric','marketing'],
    ['전환율','CVR','Conversion Rate, 방문자 중 실제 예약·문의·구매로 이어진 비율.','mkt_metric','marketing'],
    ['LTV','Lifetime Value','고객 생애 가치. 한 고객이 이탈까지 우리에게 창출하는 총수익의 예측값.','mkt_metric','marketing'],
    ['CAC','Customer Acquisition Cost','신규 고객 1명을 확보하는 데 든 총 마케팅·영업 비용.','mkt_metric','marketing'],
    ['바운스율','Bounce Rate','랜딩 후 아무 상호작용 없이 이탈한 방문 비율. 높을수록 페이지 매력도가 낮음.','mkt_metric','marketing'],
    ['세션','Session','방문자가 사이트에 들어와 활동하고 이탈하기까지의 한 번의 방문 단위.','mkt_metric','marketing'],
    ['도달','Reach','광고·콘텐츠를 본 순 사용자(중복 제외)의 수.','mkt_metric','marketing'],
    ['노출','Impression','광고·콘텐츠가 화면에 표시된 총 횟수(중복 포함).','mkt_metric','marketing'],
    ['인게이지먼트','Engagement','좋아요·댓글·저장·클릭 등 사용자가 콘텐츠에 보인 참여 반응.','mkt_metric','marketing'],

    ['퍼포먼스 마케팅','Performance Marketing','노출·클릭·전환을 데이터로 측정하고 성과에 따라 예산을 최적화하는 마케팅.','mkt_strategy','marketing'],
    ['그로스 해킹','Growth Hacking','실험과 데이터로 빠른 성장 지렛대를 찾아 저비용으로 성장을 이끄는 방법론.','mkt_strategy','marketing'],
    ['퍼널','Funnel','인지→관심→고려→전환→재방문으로 이어지는 고객 여정의 단계 구조.','mkt_strategy','marketing'],
    ['전환','Conversion','방문자가 예약·문의·구매 등 목표한 행동을 완료한 것.','mkt_strategy','marketing'],
    ['리드','Lead','상담·이벤트 신청 등으로 연락처를 남긴 잠재 고객.','mkt_strategy','marketing'],
    ['리타겟팅','Retargeting','사이트를 방문했던 사용자에게 다시 광고를 노출해 전환을 유도하는 기법.','mkt_strategy','marketing'],
    ['A/B 테스트','A/B Test','두 가지 안(A·B)을 나눠 노출해 성과가 높은 쪽을 데이터로 선택하는 실험.','mkt_strategy','marketing'],
    ['랜딩페이지','Landing Page','광고·검색을 통해 처음 도착하는, 전환 유도에 최적화된 단일 페이지.','mkt_strategy','marketing'],
    ['CTA','Call To Action','\'지금 예약하기\'처럼 사용자의 다음 행동을 유도하는 문구·버튼.','mkt_strategy','marketing'],
    ['브랜딩','Branding','로고·톤·경험을 일관되게 관리해 브랜드 인식과 신뢰를 쌓는 활동.','mkt_strategy','marketing'],

    ['오가닉/페이드','Organic / Paid','자연 유입(오가닉)과 유료 광고 유입(페이드)으로 트래픽을 구분하는 개념.','mkt_channel','marketing'],
    ['키워드 광고','Keyword Advertising','검색어에 입찰해 검색결과 상단에 노출하는 검색 광고(네이버 파워링크·구글 검색광고 등).','mkt_channel','marketing'],
    ['디스플레이 광고','Display Ad','배너·이미지·영상 형태로 웹·앱 지면에 노출하는 광고.','mkt_channel','marketing'],
    ['네이버 플레이스','Naver Place','네이버 지도·검색에 노출되는 지역 업체 정보. 병원 로컬 마케팅의 핵심 채널.','mkt_channel','marketing'],
    ['카카오톡 채널','KakaoTalk Channel','카카오톡으로 소식·상담·예약을 제공하는 비즈니스 메시지 채널.','mkt_channel','marketing'],
    ['UTM','UTM Parameter','URL 뒤에 붙여 유입 캠페인·매체·소재를 구분해 추적하는 표준 파라미터.','mkt_channel','marketing']
  ];

  var CHO = ['ㄱ','ㄱ','ㄴ','ㄷ','ㄷ','ㄹ','ㅁ','ㅂ','ㅂ','ㅅ','ㅅ','ㅇ','ㅈ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
  var CHO_LIST = ['ㄱ','ㄴ','ㄷ','ㄹ','ㅁ','ㅂ','ㅅ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
  function chosung(ko) { var c = ko.charCodeAt(0); if (c >= 0xAC00 && c <= 0xD7A3) return CHO[Math.floor((c - 0xAC00) / 588)]; return null; }
  function abcLead(en) { var m = String(en).match(/[A-Za-z]/); return m ? m[0].toUpperCase() : '#'; }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function dictOf(t) { return t[4] || 'seo'; }

  var state = { dict: 'seo', mode: 'all', val: '', cat: 'all', q: '' };
  var rootEl = null;

  function chip(label, active, attrs) { return '<button class="gl-chip' + (active ? ' on' : '') + '" ' + attrs + '>' + label + '</button>'; }

  function dictCount(d) { var n = 0; TERMS.forEach(function (t) { if (dictOf(t) === d) n++; }); return n; }

  // 현재 사전에 속한 용어만
  function dictTerms() { return TERMS.filter(function (t) { return dictOf(t) === state.dict; }); }

  function buildControls() {
    var cur = dictTerms();
    // 사전 전환 세그먼트
    var dictTabs = '';
    Object.keys(DICTS).forEach(function (d) {
      dictTabs += '<button class="gl-dict' + (state.dict === d ? ' on' : '') + '" data-dict="' + d + '">'
        + DICTS[d].label + '<span class="gl-dict-n">' + dictCount(d) + '</span></button>';
    });
    // 현재 사전의 카테고리만
    var abcSet = {}; cur.forEach(function (t) { abcSet[abcLead(t[1])] = 1; });
    var abcKeys = Object.keys(abcSet).sort();
    var catChips = '<button class="gl-chip cat' + (state.cat === 'all' ? ' on' : '') + '" data-cat="all">전체</button>';
    Object.keys(CATS).forEach(function (k) {
      if (CATS[k].dict !== state.dict) return;
      catChips += '<button class="gl-chip cat' + (state.cat === k ? ' on' : '') + '" data-cat="' + k + '" style="--c:' + CATS[k].color + '">' + CATS[k].label + '</button>';
    });
    var choChips = chip('전체', state.mode === 'all', 'data-mode="all"');
    CHO_LIST.forEach(function (c) { choChips += chip(c, state.mode === 'cho' && state.val === c, 'data-mode="cho" data-val="' + c + '"'); });
    var abcChips = ''; abcKeys.forEach(function (a) { abcChips += chip(a, state.mode === 'abc' && state.val === a, 'data-mode="abc" data-val="' + a + '"'); });
    return '<div class="gl-dicts">' + dictTabs + '</div>'
      + '<div class="gl-search"><input type="search" id="gl-q" placeholder="용어 검색 — 한글·영문·설명" value="' + esc(state.q) + '" autocomplete="off"></div>'
      + '<div class="gl-row"><span class="gl-row-lbl">카테고리</span>' + catChips + '</div>'
      + '<div class="gl-row"><span class="gl-row-lbl">가나다</span>' + choChips + '</div>'
      + '<div class="gl-row"><span class="gl-row-lbl">ABC</span>' + abcChips + '</div>';
  }

  function match(t) {
    if (dictOf(t) !== state.dict) return false;
    var cho = chosung(t[0]), abc = abcLead(t[1]);
    if (state.cat !== 'all' && t[3] !== state.cat) return false;
    if (state.mode === 'cho' && cho !== state.val) return false;
    if (state.mode === 'abc' && abc !== state.val) return false;
    if (state.q) { var hay = (t[0] + ' ' + t[1] + ' ' + t[2]).toLowerCase(); if (hay.indexOf(state.q.toLowerCase()) < 0) return false; }
    return true;
  }

  function buildCards() {
    var list = TERMS.filter(match).sort(function (a, b) { return a[0].localeCompare(b[0], 'ko'); });
    if (!list.length) return '<p class="gl-empty">검색 결과가 없습니다. 다른 키워드로 찾아보세요.</p>';
    var cards = list.map(function (t) {
      var c = CATS[t[3]] || CATS.basic;
      return '<div class="gl-card">'
        + '<div class="gl-top"><span class="gl-term">' + esc(t[0]) + '</span><span class="gl-cat" style="--c:' + c.color + '">' + c.label + '</span></div>'
        + '<div class="gl-en">' + esc(t[1]) + '</div>'
        + '<p class="gl-def">' + esc(t[2]) + '</p></div>';
    }).join('');
    return '<div class="gl-count">' + DICTS[state.dict].label + ' · ' + list.length + '개 용어</div><div class="gl-grid">' + cards + '</div>';
  }

  function renderCards() { var c = rootEl.querySelector('#gl-cards'); if (c) c.innerHTML = buildCards(); }
  function renderAll() {
    rootEl.querySelector('#gl-controls').innerHTML = buildControls();
    renderCards();
    var q = rootEl.querySelector('#gl-q'); if (q) { q.focus(); try { q.setSelectionRange(q.value.length, q.value.length); } catch (e) {} }
  }

  function onClick(e) {
    var d = e.target.closest ? e.target.closest('.gl-dict') : null;
    if (d) { state.dict = d.getAttribute('data-dict'); state.cat = 'all'; state.mode = 'all'; state.val = ''; state.q = ''; renderAll(); return; }
    var b = e.target.closest ? e.target.closest('.gl-chip') : null; if (!b) return;
    if (b.hasAttribute('data-cat')) { state.cat = b.getAttribute('data-cat'); }
    else { state.mode = b.getAttribute('data-mode'); state.val = b.getAttribute('data-val') || ''; }
    renderAll();
  }
  function onInput(e) { if (e.target && e.target.id === 'gl-q') { state.q = e.target.value; renderCards(); } }

  function mount(id) {
    rootEl = document.getElementById(id || 'glossary-root'); if (!rootEl) return;
    if (rootEl.getAttribute('data-mounted')) return;
    rootEl.setAttribute('data-mounted', '1');
    injectCSS();
    rootEl.innerHTML = '<div id="gl-controls"></div><div id="gl-cards"></div>';
    rootEl.querySelector('#gl-controls').innerHTML = buildControls();
    renderCards();
    rootEl.addEventListener('click', onClick);
    rootEl.addEventListener('input', onInput);
  }

  function injectCSS() {
    if (document.getElementById('gl-css')) return;
    var s = document.createElement('style'); s.id = 'gl-css';
    s.textContent = [
      '.gl-dicts{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}',
      '.gl-dict{display:inline-flex;align-items:center;gap:7px;border:1.5px solid var(--border,#e3e8ee);background:#fff;color:#334155;border-radius:12px;padding:11px 18px;font-size:14.5px;font-weight:800;cursor:pointer;font-family:inherit;transition:.15s}',
      '.gl-dict:hover{border-color:var(--p,#533afd);color:var(--p,#533afd)}',
      '.gl-dict.on{background:var(--p,#533afd);border-color:var(--p,#533afd);color:#fff}',
      '.gl-dict-n{font-size:11.5px;font-weight:800;background:color-mix(in srgb,var(--p,#533afd) 12%,#fff);color:var(--p,#533afd);padding:2px 8px;border-radius:10px}',
      '.gl-dict.on .gl-dict-n{background:rgba(255,255,255,.24);color:#fff}',
      '.gl-search input{width:100%;box-sizing:border-box;padding:14px 18px;border:1.5px solid var(--border,#e3e8ee);border-radius:12px;font-size:15px;font-family:inherit;margin-bottom:16px}',
      '.gl-search input:focus{outline:none;border-color:var(--p,#533afd)}',
      '.gl-row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:10px}',
      '.gl-row-lbl{font-size:12px;font-weight:800;color:var(--mute,#64748d);width:56px;flex-shrink:0}',
      '.gl-chip{border:1px solid var(--border,#e3e8ee);background:#fff;color:#334155;border-radius:20px;padding:6px 13px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s}',
      '.gl-chip:hover{border-color:var(--p,#533afd);color:var(--p,#533afd)}',
      '.gl-chip.on{background:var(--p,#533afd);border-color:var(--p,#533afd);color:#fff}',
      '.gl-chip.cat.on{background:var(--c,#533afd);border-color:var(--c,#533afd)}',
      '.gl-count{margin:18px 2px 12px;font-size:13px;font-weight:700;color:var(--mute,#64748d)}',
      '.gl-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}',
      '.gl-card{border:1px solid var(--border,#e3e8ee);border-radius:14px;padding:16px 18px;background:#fff;transition:.15s}',
      '.gl-card:hover{border-color:var(--p,#533afd);box-shadow:0 8px 22px -12px rgba(83,58,253,.35);transform:translateY(-2px)}',
      '.gl-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}',
      '.gl-term{font-size:16px;font-weight:800;color:var(--bd,#1c1e54);word-break:keep-all}',
      '.gl-cat{font-size:10.5px;font-weight:800;color:var(--c,#533afd);background:color-mix(in srgb,var(--c,#533afd) 12%,#fff);padding:3px 9px;border-radius:12px;white-space:nowrap;flex-shrink:0}',
      '.gl-en{font-size:12px;font-weight:700;color:var(--p,#533afd);margin:2px 0 8px}',
      '.gl-def{font-size:13.5px;line-height:1.65;color:var(--ink2,#475569);margin:0}',
      '.gl-empty{padding:40px;text-align:center;color:var(--mute,#64748d)}'
    ].join('');
    document.head.appendChild(s);
  }

  root.Glossary = { mount: mount, TERMS: TERMS, DICTS: DICTS, count: TERMS.length };
})(typeof window !== 'undefined' ? window : this);
