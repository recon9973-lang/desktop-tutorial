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
    marketing: { label: '마케팅 용어사전' },
    dev:       { label: '개발 용어사전' }
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
    ai_risk:   { label: 'AI 리스크',  color: '#dc2626', dict: 'ai' },
    ai_gov:    { label: 'AI 거버넌스', color: '#0369a1', dict: 'ai' },
    ai_metric: { label: 'AI 지표',    color: '#c2410c', dict: 'ai' },
    // ── 마케팅 ─────────────────────────────
    mkt_metric:   { label: '지표·측정', color: '#dc2626', dict: 'marketing' },
    mkt_channel:  { label: '채널·매체', color: '#2563eb', dict: 'marketing' },
    mkt_strategy: { label: '전략·전환', color: '#d97706', dict: 'marketing' },
    // ── 개발 ───────────────────────────────
    dev_frontend: { label: '프론트엔드',  color: '#2563eb', dict: 'dev' },
    dev_backend:  { label: '백엔드·API',  color: '#0d9488', dict: 'dev' },
    dev_infra:    { label: '인프라·배포', color: '#ea580c', dict: 'dev' },
    dev_common:   { label: '개발 일반',   color: '#7c3aed', dict: 'dev' }
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
    ['검색 의도','Search Intent','사용자가 검색으로 이루려는 실제 목적(정보·거래·이동 등).','keyword','seo'],
    ['토픽 클러스터','Topic Cluster','핵심 주제(필러) 글과 세부 글을 내부링크로 묶어 주제 권위를 높이는 콘텐츠 구조.','keyword','seo'],

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
    ['INP','Interaction to Next Paint','사용자 입력에 페이지가 반응하는 속도를 재는 코어 웹 바이탈 지표(2024년 FID 대체).','technical','seo'],
    ['스키마 마크업','Schema Markup','Schema.org 어휘로 콘텐츠 유형을 구조화 데이터로 표시해 리치 결과를 돕는 표준.','technical','seo'],
    ['브레드크럼','Breadcrumbs','현재 페이지의 사이트 내 위치를 계층으로 보여주는 탐색 경로.','technical','seo'],

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

    // ═══════════════ AI 용어사전 (검증본 150 + 보존 13) ═══════════════
    // [ko, en, def, cat, dict, {ac,detail,ex,rel,src:[[name,url],...]}]

    // ── AI 기본 ──
    ['검증 데이터','Validation Data','학습 중 모델 선택과 튜닝에 쓰는 별도 데이터.','ai_basic','ai',{detail:'하이퍼파라미터 조정, 조기 종료, 모델 비교에 사용하며 최종 성능 보고용 테스트 데이터와 구분한다.',ex:'여러 학습률 후보 중 검증 성능이 높은 값을 선택.',rel:'훈련 데이터;테스트 데이터;하이퍼파라미터',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/']]}],
    ['견고성','Robustness','예상치 못한 입력, 오류, 공격에도 성능과 안전성을 유지하는 능력.','ai_basic','ai',{detail:'분포 변화, 노이즈, 적대적 입력, 시스템 장애에 대한 내성을 포함한다.',ex:'오타가 있는 질문에도 안정적으로 의도 파악.',rel:'적대적 예제;모니터링;NIST AI RMF',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],
    ['대규모 언어모델','Large Language Model','방대한 텍스트로 학습해 언어를 이해하고 생성하는 모델.','ai_basic','ai',{ac:'LLM',detail:'토큰 시퀀스의 확률적 패턴을 학습해 문장 생성, 요약, 번역, 코드 작성, 질의응답을 수행하는 언어 모델이다.',ex:'챗봇이 질문에 자연어로 답변.',rel:'토큰;프롬프트;문맥창',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Brown et al. - Language Models are Few-Shot Learners','https://arxiv.org/abs/2005.14165']]}],
    ['딥러닝','Deep Learning','여러 층의 신경망으로 복잡한 패턴을 학습하는 머신러닝 기법.','ai_basic','ai',{ac:'DL',detail:'인공신경망의 여러 은닉층을 사용해 이미지, 음성, 텍스트 같은 비정형 데이터의 고수준 특징을 학습한다.',ex:'사진에서 객체를 인식하거나 음성을 텍스트로 변환.',rel:'신경망;CNN;Transformer',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['레이블','Label','지도학습에서 모델이 맞혀야 하는 정답 값.','ai_basic','ai',{detail:'입력 예제에 붙은 목표 출력이며 분류의 클래스나 회귀의 수치 값이 될 수 있다.',ex:'이메일 데이터의 스팸 여부.',rel:'지도학습;훈련 데이터;정답',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['머신러닝','Machine Learning','데이터에서 패턴을 학습해 예측이나 판단 성능을 높이는 AI 방법.','ai_basic','ai',{ac:'ML',detail:'명시적으로 모든 규칙을 코딩하기보다 데이터와 알고리즘으로 모델을 학습시켜 새 입력에 대해 예측하게 한다.',ex:'거래 데이터를 학습해 사기 거래를 분류.',rel:'데이터셋;모델;학습',src:[['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['멀티모달','Multimodal','텍스트, 이미지, 음성, 영상 등 여러 형태의 데이터를 함께 다루는 능력.','ai_basic','ai',{detail:'단일 모달리티가 아닌 여러 데이터 표현을 입력 또는 출력으로 통합해 더 풍부한 이해와 생성을 수행한다.',ex:'사진을 보고 텍스트 설명을 생성하거나 음성 명령으로 이미지를 분석.',rel:'비전-언어 모델;음성 인식;이미지 생성',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['문맥창','Context Window','모델이 한 번에 참고할 수 있는 입력과 출력 토큰의 범위.','ai_basic','ai',{detail:'시스템 지시, 대화 기록, 문서, 사용자 입력이 모두 이 한도 안에서 처리된다.',ex:'긴 보고서를 넣을 때 토큰 한도를 넘으면 일부를 요약해야 함.',rel:'토큰;프롬프트;RAG',src:[['Hugging Face Transformers Glossary','https://huggingface.co/docs/transformers/en/glossary'],['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview']]}],
    ['생성형 AI','Generative AI','텍스트, 이미지, 음성 등 새로운 콘텐츠를 만들어내는 AI.','ai_basic','ai',{ac:'GenAI',detail:'대규모 데이터에서 분포와 패턴을 학습해 사용자의 입력 조건에 맞는 새 산출물을 생성하는 모델과 시스템을 말한다.',ex:'프롬프트를 입력하면 이메일 초안이나 이미지를 생성.',rel:'LLM;확산 모델;멀티모달',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['설명가능성','Explainability','모델 결정 이유를 사람이 이해할 수 있게 설명하는 능력.','ai_basic','ai',{ac:'XAI',detail:'예측에 영향을 준 요인, 근거, 한계를 사용자나 감사자가 해석할 수 있게 제공한다.',ex:'대출 거절 사유로 소득 대비 부채 비율을 표시.',rel:'해석가능성;투명성;책임성',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],
    ['에이전트','Agent','목표를 위해 입력을 해석하고 계획과 행동을 수행하는 소프트웨어.','ai_basic','ai',{detail:'LLM, 도구, 메모리, 정책을 결합해 사용자를 대신해 다단계 작업을 수행할 수 있다.',ex:'여행 조건을 받아 항공권 검색과 일정 초안을 생성.',rel:'도구 사용;계획;에이전트 워크플로',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Function calling','https://developers.openai.com/api/docs/guides/function-calling']]}],
    ['인공지능','Artificial Intelligence','사람의 지능이 필요한 일을 기계가 수행하도록 만드는 기술 분야.','ai_basic','ai',{ac:'AI',detail:'추론, 인식, 예측, 생성, 의사결정처럼 인간 지능과 관련된 작업을 컴퓨터 시스템으로 구현하는 넓은 개념이다.',ex:'이미지 판독, 번역, 추천, 챗봇 응답 생성.',rel:'머신러닝;딥러닝;생성형 AI',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['책임성','Accountability','AI 시스템 결과와 운영에 대해 책임 주체와 절차를 명확히 하는 원칙.','ai_basic','ai',{detail:'의사결정, 검토, 사고 대응, 변경 관리가 추적 가능해야 한다.',ex:'모델 오류 사고 시 담당 팀과 조치 절차를 기록.',rel:'투명성;휴먼 인 더 루프;ISO 42001',src:[['OECD AI Principles','https://oecd.ai/en/ai-principles'],['ISO/IEC 42001:2023 AI management systems','https://www.iso.org/standard/42001']]}],
    ['추론','Inference','학습된 모델이 새 입력에 대해 예측이나 출력을 생성하는 과정.','ai_basic','ai',{detail:'운영 환경에서 모델 파라미터를 고정한 채 입력을 처리해 결과를 반환한다.',ex:'사용자 질문을 받아 챗봇 답변 생성.',rel:'모델 서빙;지연시간;처리량',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['테스트 데이터','Test Data','학습이 끝난 모델의 일반화 성능을 확인하는 별도 데이터.','ai_basic','ai',{detail:'훈련과 튜닝에 쓰지 않은 데이터로 모델이 새로운 사례에 얼마나 잘 작동하는지 평가한다.',ex:'출시 전 보류 데이터셋으로 최종 정확도 측정.',rel:'검증 데이터;일반화;벤치마크',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/']]}],
    ['토큰','Token','모델이 텍스트를 처리하는 기본 단위.','ai_basic','ai',{detail:'단어, 하위 단어, 문자 조각 등이 될 수 있으며 LLM 입력과 출력 길이 계산의 기준이 된다.',ex:'\'unbelievable\'이 여러 하위 토큰으로 나뉨.',rel:'토큰화;문맥창;어휘집',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Hugging Face Transformers Glossary','https://huggingface.co/docs/transformers/en/glossary']]}],
    ['투명성','Transparency','AI 시스템의 목적, 데이터, 한계, 책임 주체를 공개하고 이해 가능하게 하는 특성.','ai_basic','ai',{detail:'사용자와 감사자가 시스템 사용 여부, 성능, 위험, 운영 절차를 파악할 수 있어야 한다.',ex:'AI 생성 콘텐츠임을 표시하고 근거 출처 제공.',rel:'모델 카드;책임성;AI Act',src:[['OECD AI Principles','https://oecd.ai/en/ai-principles'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['특성','Feature','모델이 입력으로 사용하는 관측값이나 속성.','ai_basic','ai',{detail:'원본 데이터에서 예측에 필요한 정보를 수치, 범주, 텍스트 임베딩 등으로 표현한 입력 변수다.',ex:'나이, 구매 횟수, 최근 로그인 일수.',rel:'특성 공학;레이블;정규화',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['파라미터','Parameter','모델이 학습 과정에서 데이터로부터 조정하는 내부 값.','ai_basic','ai',{detail:'신경망의 가중치와 편향처럼 예측 함수를 구성하며 손실을 줄이도록 업데이트된다.',ex:'뉴런 연결 가중치가 학습 중 변경됨.',rel:'하이퍼파라미터;가중치;경사하강법',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['파운데이션 모델','Foundation Model','대규모 데이터로 사전학습되어 여러 작업에 재사용되는 범용 모델.','ai_basic','ai',{detail:'범용 표현을 학습한 뒤 프롬프트, 미세조정, 도구 연결 등을 통해 다양한 하위 업무에 적용되는 기반 모델이다.',ex:'하나의 언어 모델을 요약, 분류, 질의응답에 활용.',rel:'사전학습;미세조정;LLM',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['프롬프트','Prompt','모델에 원하는 작업을 전달하는 입력 지시문.','ai_basic','ai',{detail:'사용자 질문, 시스템 지시, 예시, 제약 조건을 포함해 모델 출력의 방향을 정한다.',ex:'\'초등학생도 이해하게 설명해줘\'라고 요청.',rel:'시스템 프롬프트;프롬프트 엔지니어링;문맥창',src:[['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview'],['OpenAI API - Structured model outputs','https://developers.openai.com/api/docs/guides/structured-outputs']]}],
    ['해석가능성','Interpretability','모델 내부 작동이나 예측 근거를 사람이 이해할 수 있는 정도.','ai_basic','ai',{detail:'단순 모델은 구조 자체가 해석 가능하고, 복잡한 모델은 사후 설명 기법을 보조적으로 쓴다.',ex:'결정트리의 분기 조건으로 예측 과정을 추적.',rel:'설명가능성;투명성;모델 카드',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['훈련 데이터','Training Data','모델이 패턴을 배우는 데 직접 사용하는 데이터.','ai_basic','ai',{detail:'모델 파라미터가 손실을 줄이도록 조정되는 학습 과정의 핵심 데이터다.',ex:'과거 구매 기록으로 추천 모델을 학습.',rel:'검증 데이터;테스트 데이터;데이터 누수',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/']]}],

    // ── GEO·AEO ──
    ['AI 오버뷰','AI Overview','검색 결과 위에 AI가 여러 출처를 종합해 보여주는 요약형 답변.','ai_geo','ai',{ac:'AIO',detail:'생성형 검색 경험의 한 형태로, 사용자의 질의에 대해 웹 출처를 바탕으로 요약 답변을 제공한다.',ex:'검색창 질문에 링크와 함께 요약 답변이 표시됨.',rel:'GEO;AEO;생성형 검색',src:[['Chen et al. - Generative Engine Optimization','https://arxiv.org/abs/2509.08919'],['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval']]}],
    ['답변 엔진 최적화','Answer Engine Optimization','질문형 검색과 AI 답변에서 직접 답변으로 선택되도록 콘텐츠를 설계하는 실무.','ai_geo','ai',{ac:'AEO',detail:'명확한 질문-답 구조, 근거, 저자성, 최신성을 강화해 답변 엔진의 이해와 인용을 돕는다.',ex:'FAQ 페이지에 간결한 답과 출처를 함께 제공.',rel:'GEO;시맨틱 검색;구조화 콘텐츠',src:[['Chen et al. - Generative Engine Optimization','https://arxiv.org/abs/2509.08919'],['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval']]}],
    ['생성형 엔진 최적화','Generative Engine Optimization','생성형 검색과 AI 답변에서 콘텐츠가 인용·노출되도록 최적화하는 접근.','ai_geo','ai',{ac:'GEO',detail:'전통 SEO와 달리 LLM 기반 답변 엔진의 출처 선택, 요약, 인용 가능성을 고려한다.',ex:'브랜드 설명을 구조화해 AI 검색 답변에서 출처로 선택될 가능성 개선.',rel:'AEO;시맨틱 검색;AI 오버뷰',src:[['Chen et al. - Generative Engine Optimization','https://arxiv.org/abs/2509.08919'],['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval']]}],
    ['시맨틱 검색','Semantic Search','단어의 표면 일치보다 의도와 의미 유사성을 기준으로 찾는 검색.','ai_geo','ai',{detail:'쿼리와 문서를 임베딩해 의미적으로 가까운 결과를 반환한다.',ex:'\'환불 언제 돼?\'가 \'반품 처리 기간\' 문서를 찾음.',rel:'임베딩;벡터 데이터베이스;RAG',src:[['OpenAI API - Vector embeddings','https://developers.openai.com/api/docs/guides/embeddings'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],

    // ── AI 기술 ──
    ['Evals','Evaluations','모델이나 에이전트가 요구사항을 충족하는지 반복 측정하는 평가 세트.','ai_tech','ai',{ac:'Evals',detail:'정답 기반 테스트, 등급자, 사람 평가, 회귀 테스트를 통해 변경 전후 품질을 추적한다.',ex:'프롬프트 수정 전후 고객응대 점수를 자동 비교.',rel:'모델 평가;레드팀;벤치마크',src:[['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['MMLU','Massive Multitask Language Understanding','다양한 과목의 객관식 문제로 언어 모델 지식을 평가하는 벤치마크.','ai_tech','ai',{ac:'MMLU',detail:'광범위한 학문 분야와 난이도를 포함해 범용 지식과 문제 풀이 능력을 측정한다.',ex:'새 LLM의 MMLU 점수로 기초 역량 비교.',rel:'벤치마크;LLM;평가',src:[['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals'],['Brown et al. - Language Models are Few-Shot Learners','https://arxiv.org/abs/2005.14165']]}],
    ['강화학습','Reinforcement Learning','보상과 벌점을 통해 에이전트가 행동 전략을 학습하는 방식.','ai_tech','ai',{ac:'RL',detail:'에이전트가 환경에서 행동하고 받은 보상을 최대화하도록 정책을 개선한다.',ex:'게임 AI가 승리에 가까운 행동을 반복 학습.',rel:'에이전트;정책;보상',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['검색 증강 생성','Retrieval-Augmented Generation','외부 자료를 검색해 모델 답변 생성에 함께 쓰는 방식.','ai_tech','ai',{ac:'RAG',detail:'질문과 관련된 문서 조각을 찾아 문맥에 넣고 LLM이 이를 바탕으로 답변하게 한다.',ex:'사내 위키를 검색해 정책 질문에 답변.',rel:'검색기;청킹;그라운딩',src:[['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['검색기','Retriever','질문과 관련된 문서나 후보를 찾아오는 구성요소.','ai_tech','ai',{detail:'키워드, 벡터 유사도, 하이브리드 검색으로 LLM에 제공할 근거 자료를 선별한다.',ex:'질문 임베딩과 가까운 문서 조각 5개 검색.',rel:'RAG;의미 검색;재랭킹',src:[['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval'],['OpenAI API - Vector embeddings','https://developers.openai.com/api/docs/guides/embeddings']]}],
    ['경사하강법','Gradient Descent','손실이 줄어드는 방향으로 파라미터를 반복 업데이트하는 최적화 방법.','ai_tech','ai',{detail:'손실 함수의 기울기를 계산해 반대 방향으로 조금씩 이동하며 더 나은 파라미터를 찾는다.',ex:'가중치를 학습률만큼 조정해 손실을 낮춤.',rel:'역전파;학습률;옵티마이저',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['계획','Planning','목표 달성을 위한 하위 작업과 순서를 정하는 과정.','ai_tech','ai',{detail:'에이전트나 모델이 문제를 단계로 나누고 필요한 도구와 검증 절차를 선택한다.',ex:'보고서 작성 전에 자료 수집, 분석, 초안, 검토 순서 생성.',rel:'에이전트;사고 연쇄;추론 모델',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],
    ['구조화 출력','Structured Outputs','모델 응답을 JSON 스키마 같은 정해진 구조에 맞게 생성하는 기능.','ai_tech','ai',{detail:'후처리와 시스템 연동을 위해 자유 텍스트 대신 검증 가능한 필드와 타입으로 답하게 한다.',ex:'계약서에서 당사자, 날짜, 금액을 JSON으로 추출.',rel:'JSON 스키마;함수 호출;프롬프트 템플릿',src:[['OpenAI API - Structured model outputs','https://developers.openai.com/api/docs/guides/structured-outputs'],['OpenAI API - Function calling','https://developers.openai.com/api/docs/guides/function-calling']]}],
    ['군집화','Clustering','레이블 없이 비슷한 데이터끼리 묶는 비지도학습 방법.','ai_tech','ai',{detail:'데이터 간 거리나 밀도 구조를 이용해 유사한 샘플을 같은 그룹으로 배정한다.',ex:'고객 행동 패턴별 세그먼트 생성.',rel:'비지도학습;임베딩;이상 탐지',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['그라운딩','Grounding','모델 답변을 실제 출처나 제공된 데이터에 근거시키는 방법.','ai_tech','ai',{detail:'외부 문서, 데이터베이스, 도구 결과를 참조해 답변의 사실성과 추적 가능성을 높인다.',ex:'검색된 계약 조항을 근거로 답변.',rel:'RAG;출처 인용;환각',src:[['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['대규모 멀티모달 모델','Large Multimodal Model','텍스트뿐 아니라 이미지, 음성, 영상 등 여러 입력 양식을 함께 처리하는 대형 모델.','ai_tech','ai',{ac:'LMM',detail:'언어와 시각 등 서로 다른 모달리티를 같은 추론 흐름에서 결합해 이해, 생성, 검색, 질의응답에 활용한다.',ex:'이미지와 질문을 함께 넣어 장면을 설명.',rel:'멀티모달;비전-언어 모델;임베딩',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval']]}],
    ['데이터 분할','Dataset Split','훈련, 검증, 테스트 용도로 데이터를 나누는 절차.','ai_tech','ai',{detail:'성능 평가가 오염되지 않도록 목적별 데이터셋을 분리하고, 시간 순서나 그룹 누수도 고려한다.',ex:'고객별로 train/validation/test를 나눠 같은 고객이 섞이지 않게 함.',rel:'데이터 누수;검증 데이터;테스트 데이터',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['데이터 전처리','Data Preprocessing','원본 데이터를 모델이 학습할 수 있는 형태로 정리하는 과정.','ai_tech','ai',{detail:'결측값 처리, 이상치 처리, 스케일 조정, 인코딩, 토큰화 등 품질과 형식을 맞추는 작업이다.',ex:'날짜 문자열을 연월일 숫자 특성으로 변환.',rel:'정규화;원-핫 인코딩;특성 공학',src:[['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['데이터 증강','Data Augmentation','기존 데이터를 변형해 학습 예제를 늘리는 방법.','ai_tech','ai',{detail:'이미지 회전, 문장 치환, 잡음 추가 등으로 모델의 일반화와 견고성을 높인다.',ex:'사진을 좌우 반전해 추가 훈련 샘플 생성.',rel:'합성 데이터;일반화;과적합',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['데이터셋 문서','Datasheet for Datasets','데이터셋의 수집, 구성, 용도, 한계, 윤리 이슈를 기록한 문서.','ai_tech','ai',{detail:'데이터 출처와 대표성, 라벨링 절차, 사용 제한을 명확히 해 재사용 위험을 줄인다.',ex:'얼굴 이미지 데이터셋의 수집 동의와 인구통계 분포 기록.',rel:'데이터 거버넌스;모델 카드;투명성',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],
    ['도구 사용','Tool Use','모델이 계산기, 검색, API 같은 외부 도구를 호출해 작업하는 방식.','ai_tech','ai',{detail:'모델 내부 지식만으로 부족한 정보 조회, 계산, 파일 작업을 외부 기능으로 보완한다.',ex:'캘린더 API를 조회해 가능한 회의 시간을 제안.',rel:'함수 호출;에이전트;가드레일',src:[['OpenAI API - Function calling','https://developers.openai.com/api/docs/guides/function-calling'],['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview']]}],
    ['도구 오케스트레이션','Tool Orchestration','여러 도구와 모델 호출을 목적에 맞게 조합하고 라우팅하는 방식.','ai_tech','ai',{detail:'작업별로 검색, 계산, 코드 실행, 저장소 업데이트를 순서대로 연결한다.',ex:'검색 후 요약하고 CRM에 결과를 기록.',rel:'에이전트;함수 호출;워크플로',src:[['OpenAI API - Function calling','https://developers.openai.com/api/docs/guides/function-calling'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['멀티헤드 어텐션','Multi-head Attention','여러 어텐션 계산을 병렬로 수행해 다양한 관계를 포착하는 구조.','ai_tech','ai',{detail:'각 헤드가 서로 다른 관점의 토큰 관계를 학습하고 결과를 결합한다.',ex:'한 헤드는 문법 관계, 다른 헤드는 의미 관계에 집중.',rel:'셀프 어텐션;트랜스포머;헤드',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Vaswani et al. - Attention Is All You Need','https://arxiv.org/abs/1706.03762']]}],
    ['모델 레지스트리','Model Registry','모델 버전, 메타데이터, 승인 상태를 관리하는 저장소.','ai_tech','ai',{detail:'실험에서 운영 배포까지 어떤 모델이 언제, 어떤 데이터와 설정으로 만들어졌는지 추적한다.',ex:'v3 모델을 승인 후 production 스테이지로 승격.',rel:'MLOps;모델 서빙;모델 카드',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['ISO/IEC 42001:2023 AI management systems','https://www.iso.org/standard/42001']]}],
    ['모델 모니터링','Model Monitoring','배포된 모델의 성능, 입력 분포, 오류, 안전성을 지속 추적하는 활동.','ai_tech','ai',{detail:'운영 데이터에서 성능 저하, 드리프트, 비용 증가, 정책 위반을 조기에 발견한다.',ex:'일별 환각 신고율과 응답 지연시간 대시보드.',rel:'데이터 드리프트;개념 드리프트;AI RMF',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['모델 서빙','Model Serving','학습된 모델을 API나 애플리케이션에서 호출 가능하게 운영하는 것.','ai_tech','ai',{detail:'모델 로딩, 요청 처리, 스케일링, 버전 관리, 관측성을 포함한 배포 계층이다.',ex:'추천 모델을 REST API로 배포.',rel:'추론;모델 레지스트리;모니터링',src:[['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['모델 카드','Model Card','모델의 용도, 성능, 한계, 윤리적 고려사항을 기록한 문서.','ai_tech','ai',{detail:'배포자와 사용자가 모델 적합성과 위험을 판단할 수 있도록 표준화된 설명을 제공한다.',ex:'분류 모델의 집단별 성능과 사용 금지 사례 기록.',rel:'투명성;모델 레지스트리;책임성',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['모델 평가','Model Evaluation','모델 성능, 안전성, 신뢰성을 기준과 데이터로 측정하는 과정.','ai_tech','ai',{detail:'정량 지표, 벤치마크, 사람 평가, 레드팀 테스트를 결합해 배포 적합성을 판단한다.',ex:'새 챗봇 버전을 기존 버전과 비교 평가.',rel:'벤치마크;Evals;레드팀',src:[['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['미세조정','Fine-tuning','사전학습 모델을 특정 작업이나 도메인 데이터로 추가 학습하는 과정.','ai_tech','ai',{detail:'기존 모델의 가중치를 출발점으로 삼아 목표 업무에 맞게 성능과 행동을 조정한다.',ex:'법률 문서 질의응답용으로 LLM을 추가 학습.',rel:'사전학습;SFT;전이학습',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],
    ['배치 크기','Batch Size','한 번의 파라미터 업데이트에 사용하는 샘플 수.','ai_tech','ai',{detail:'계산 효율, 메모리 사용량, 기울기 안정성에 영향을 주는 학습 설정이다.',ex:'배치 크기 64로 GPU 메모리에 맞춰 학습.',rel:'에포크;학습률;미니배치',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['벡터 데이터베이스','Vector Database','임베딩 벡터를 저장하고 유사도 기반으로 빠르게 검색하는 데이터베이스.','ai_tech','ai',{detail:'고차원 벡터 인덱싱과 근사 최근접 탐색을 제공해 RAG와 추천에 자주 쓰인다.',ex:'문서 조각 임베딩을 저장해 질문과 가까운 조각 검색.',rel:'임베딩;의미 검색;최근접 이웃 탐색',src:[['OpenAI API - Vector embeddings','https://developers.openai.com/api/docs/guides/embeddings'],['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval']]}],
    ['벤치마크','Benchmark','모델 비교를 위해 표준화된 데이터셋과 평가 절차.','ai_tech','ai',{detail:'같은 조건에서 여러 모델의 성능을 측정하지만 실제 업무 성능을 완전히 대체하지는 않는다.',ex:'질문답변 벤치마크로 모델 후보 비교.',rel:'평가;MMLU;테스트 데이터',src:[['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['분류','Classification','입력 데이터를 미리 정한 범주 중 하나로 나누는 예측 작업.','ai_tech','ai',{detail:'레이블이 있는 데이터로 결정 경계를 학습해 새 샘플의 클래스를 예측한다.',ex:'이메일을 스팸과 정상으로 분류.',rel:'정확도;정밀도;재현율',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['분산','Variance','데이터 변화에 따라 모델 예측이 크게 흔들리는 정도.','ai_tech','ai',{detail:'모델이 훈련 데이터의 세부 잡음에 민감하면 분산이 높고 과적합 위험이 커진다.',ex:'훈련 샘플을 조금 바꾸면 성능이 크게 달라짐.',rel:'편향;과적합;일반화',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['비지도학습','Unsupervised Learning','정답 레이블 없이 데이터의 구조나 패턴을 찾는 방식.','ai_tech','ai',{detail:'군집, 차원 축소, 표현 학습처럼 데이터 자체의 관계를 발견하는 데 사용된다.',ex:'뉴스 문서를 주제별로 자동 묶기.',rel:'군집화;임베딩;차원 축소',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['사고 연쇄','Chain-of-thought','복잡한 문제에서 중간 추론 단계를 유도하는 프롬프트 기법.','ai_tech','ai',{ac:'CoT',detail:'모델이 바로 답을 내기보다 문제를 단계적으로 분해해 추론하도록 지시한다.',ex:'수학 문제를 단계별로 풀게 요청.',rel:'추론 모델;프롬프트;자기검증',src:[['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],
    ['사전학습','Pretraining','대규모 일반 데이터로 모델의 기본 표현 능력을 먼저 학습하는 단계.','ai_tech','ai',{detail:'이후 미세조정이나 프롬프트 기반 사용을 위해 범용 지식을 축적하는 초기 학습 과정이다.',ex:'웹 텍스트로 언어 모델을 먼저 학습.',rel:'파운데이션 모델;미세조정;자기지도학습',src:[['Devlin et al. - BERT','https://arxiv.org/abs/1810.04805'],['Brown et al. - Language Models are Few-Shot Learners','https://arxiv.org/abs/2005.14165']]}],
    ['생성적 적대 신경망','Generative Adversarial Network','생성자와 판별자가 경쟁하며 현실적인 데이터를 만드는 생성 모델.','ai_tech','ai',{ac:'GAN',detail:'생성자는 진짜 같은 샘플을 만들고 판별자는 진짜와 가짜를 구분하며 서로 성능을 높인다.',ex:'가짜 얼굴 이미지를 생성.',rel:'확산 모델;생성형 AI;판별자',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['셀프 어텐션','Self-attention','같은 시퀀스 안의 토큰들이 서로를 참고해 표현을 갱신하는 방식.','ai_tech','ai',{detail:'각 토큰이 다른 모든 토큰과의 관련도를 계산해 문맥 정보를 반영한다.',ex:'문장 안에서 \'그것\'이 어떤 명사를 가리키는지 반영.',rel:'어텐션;트랜스포머;문맥창',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Vaswani et al. - Attention Is All You Need','https://arxiv.org/abs/1706.03762']]}],
    ['손실 함수','Loss Function','모델 예측과 정답의 차이를 수치화하는 함수.','ai_tech','ai',{detail:'학습 알고리즘은 이 값을 줄이는 방향으로 파라미터를 업데이트한다.',ex:'분류에서 크로스엔트로피 손실 사용.',rel:'목적 함수;최적화;경사하강법',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['순환 신경망','Recurrent Neural Network','순서가 있는 데이터의 이전 상태를 활용하는 신경망.','ai_tech','ai',{ac:'RNN',detail:'시퀀스의 과거 정보를 내부 상태로 전달해 텍스트, 음성, 시계열을 처리한다.',ex:'문장 단어 순서를 반영해 다음 단어 예측.',rel:'LSTM;시계열;Transformer',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['시계열 예측','Time Series Forecasting','시간 순서가 있는 데이터를 바탕으로 미래 값을 예측하는 작업.','ai_tech','ai',{detail:'추세, 계절성, 외부 요인을 모델링해 다음 시점의 수요, 가격, 센서 값을 추정한다.',ex:'다음 달 재고 수요 예측.',rel:'회귀;데이터 드리프트;모델 모니터링',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['시스템 프롬프트','System Prompt','모델의 역할, 규칙, 제약을 우선적으로 설정하는 지시문.','ai_tech','ai',{detail:'대화 전체에서 모델의 행동 기준을 제공하며 사용자 입력보다 높은 수준의 정책이나 형식을 정한다.',ex:'고객지원 상담원 역할과 금지 응답을 지정.',rel:'프롬프트;가드레일;프롬프트 인젝션',src:[['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview'],['OpenAI API - Structured model outputs','https://developers.openai.com/api/docs/guides/structured-outputs']]}],
    ['신경망','Neural Network','노드와 가중치가 층으로 연결된 학습 모델.','ai_tech','ai',{detail:'입력층, 은닉층, 출력층을 거치며 비선형 변환을 누적해 복잡한 함수를 근사한다.',ex:'이미지 픽셀을 여러 층으로 처리해 클래스를 예측.',rel:'딥러닝;활성화 함수;역전파',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['액티브 러닝','Active Learning','모델이 학습에 가장 도움이 되는 데이터의 라벨링을 요청하는 방식.','ai_tech','ai',{detail:'라벨링 비용을 줄이기 위해 불확실하거나 대표성이 큰 샘플을 선택해 사람이 라벨을 붙인다.',ex:'분류 모델이 애매한 문서만 리뷰어에게 요청.',rel:'준지도학습;레이블;휴먼 인 더 루프',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['어텐션','Attention','입력의 어떤 부분이 중요한지 가중치를 두어 참고하는 메커니즘.','ai_tech','ai',{detail:'모델이 출력 생성 시 관련 토큰이나 특징에 더 큰 가중치를 부여하도록 한다.',ex:'번역 중 대명사가 가리키는 앞 단어에 집중.',rel:'셀프 어텐션;멀티헤드 어텐션;트랜스포머',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Vaswani et al. - Attention Is All You Need','https://arxiv.org/abs/1706.03762']]}],
    ['에이전트 워크플로','Agentic Workflow','에이전트가 관찰, 추론, 행동, 피드백을 반복하는 작업 흐름.','ai_tech','ai',{detail:'복잡한 목표를 하위 단계로 나누고 도구 호출 결과를 반영해 다음 행동을 조정한다.',ex:'코드 수정 후 테스트 결과를 보고 다시 패치.',rel:'에이전트;계획;도구 오케스트레이션',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Function calling','https://developers.openai.com/api/docs/guides/function-calling']]}],
    ['에포크','Epoch','훈련 데이터 전체를 한 번 학습에 사용한 단위.','ai_tech','ai',{detail:'여러 에포크 동안 데이터를 반복해 보며 모델 파라미터를 점진적으로 개선한다.',ex:'10에포크 동안 모델 학습.',rel:'배치 크기;학습률;훈련 데이터',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['역전파','Backpropagation','신경망의 각 파라미터가 손실에 미치는 영향을 계산하는 알고리즘.','ai_tech','ai',{detail:'출력층의 오류를 뒤쪽 층에서 앞쪽 층으로 전파해 기울기를 효율적으로 구한다.',ex:'딥러닝 모델이 모든 층의 가중치를 업데이트.',rel:'경사하강법;신경망;손실 함수',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['연합학습','Federated Learning','데이터를 중앙으로 모으지 않고 여러 장치나 기관에서 모델을 공동 학습하는 방식.','ai_tech','ai',{detail:'로컬 데이터는 각 참여자에게 남기고 모델 업데이트만 집계해 개인정보 노출을 줄인다.',ex:'스마트폰 키보드 예측 모델을 기기별 데이터로 학습.',rel:'개인정보보호 ML;차등 개인정보보호;분산 학습',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['오토인코더','Autoencoder','입력을 압축했다가 다시 복원하도록 학습하는 신경망.','ai_tech','ai',{detail:'인코더와 디코더로 구성되며 차원 축소, 노이즈 제거, 이상 탐지에 활용된다.',ex:'센서 데이터를 복원하지 못하는 경우 이상으로 탐지.',rel:'인코더;디코더;이상 탐지',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['옵티마이저','Optimizer','손실을 줄이도록 파라미터 업데이트 규칙을 정하는 알고리즘.','ai_tech','ai',{detail:'SGD, Adam, AdaGrad처럼 기울기와 과거 업데이트 정보를 이용해 학습을 진행한다.',ex:'Adam 옵티마이저로 언어 모델 미세조정.',rel:'경사하강법;학습률;파라미터',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['원-핫 인코딩','One-hot Encoding','범주형 값을 0과 1의 벡터로 바꾸는 표현 방식.','ai_tech','ai',{detail:'각 범주를 별도 차원으로 두고 해당 범주 위치만 1로 표시해 모델 입력으로 사용한다.',ex:'색상=빨강을 [1,0,0]으로 표현.',rel:'범주형 특성;토큰화;임베딩',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['음성 인식','Speech Recognition','사람의 음성을 텍스트나 명령으로 변환하는 기술.','ai_tech','ai',{ac:'ASR',detail:'오디오 신호에서 음소, 단어, 문맥을 추정해 자동 전사나 음성 인터페이스에 활용한다.',ex:'회의 녹음을 자동 회의록으로 변환.',rel:'음성 합성;멀티모달;자연어 처리',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['이상 탐지','Anomaly Detection','정상 패턴에서 크게 벗어난 데이터를 찾아내는 기법.','ai_tech','ai',{detail:'분포, 거리, 재구성 오류 등을 기준으로 드문 사건이나 잠재적 문제를 식별한다.',ex:'서버 로그에서 비정상 트래픽 탐지.',rel:'아웃라이어;모니터링;데이터 드리프트',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['인간 피드백 기반 강화학습','Reinforcement Learning from Human Feedback','사람의 선호 피드백을 보상 신호로 사용해 모델 출력을 조정하는 방법.','ai_tech','ai',{ac:'RLHF',detail:'사람이 더 선호하는 답변을 학습해 유용성, 안전성, 지시 준수 성향을 높인다.',ex:'두 답변 중 더 나은 답을 사람이 고르고 모델이 선호를 학습.',rel:'강화학습;SFT;정렬',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['일반화','Generalization','학습하지 않은 새 데이터에서도 성능을 유지하는 능력.','ai_tech','ai',{detail:'훈련 데이터의 특수한 우연이 아니라 문제의 본질적 패턴을 학습했는지를 나타낸다.',ex:'새 지역 고객 데이터에서도 이탈 예측이 안정적으로 작동.',rel:'테스트 데이터;과적합;검증',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['임베딩','Embedding','단어나 문서 같은 대상을 의미가 담긴 숫자 벡터로 표현한 것.','ai_tech','ai',{detail:'의미가 비슷한 항목이 벡터 공간에서 가까워지도록 학습된 표현이며 검색, 군집, 추천에 쓰인다.',ex:'질문과 문서 조각을 임베딩해 유사도 검색.',rel:'벡터 데이터베이스;의미 검색;토큰',src:[['OpenAI API - Vector embeddings','https://developers.openai.com/api/docs/guides/embeddings'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['자기지도학습','Self-supervised Learning','데이터 자체에서 학습 신호를 만들어 표현을 학습하는 방식.','ai_tech','ai',{detail:'일부 토큰 예측, 다음 문장 예측, 이미지 일부 복원처럼 사람이 붙인 레이블 없이 훈련 목표를 만든다.',ex:'언어 모델이 빈칸 토큰을 맞히며 사전학습.',rel:'사전학습;BERT;LLM',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Devlin et al. - BERT','https://arxiv.org/abs/1810.04805']]}],
    ['자연어 처리','Natural Language Processing','사람의 언어를 컴퓨터가 분석, 이해, 생성하도록 하는 분야.','ai_tech','ai',{ac:'NLP',detail:'텍스트나 음성 언어를 토큰화, 임베딩, 분류, 생성 등의 방식으로 처리하는 AI 분야다.',ex:'문서 요약, 감성 분석, 번역.',rel:'LLM;토큰화;의미 검색',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['재랭킹','Re-ranking','초기 검색 결과를 더 정교한 모델로 다시 순위화하는 단계.','ai_tech','ai',{detail:'빠른 검색기가 넓게 후보를 찾고, 재랭커가 질문과 문서의 관련성을 더 정확히 평가한다.',ex:'상위 50개 후보를 교차 인코더로 재정렬.',rel:'검색기;RAG;하이브리드 검색',src:[['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['전이학습','Transfer Learning','한 문제에서 얻은 지식을 관련 문제에 재사용하는 학습 방식.','ai_tech','ai',{detail:'사전학습 모델의 표현이나 가중치를 새 도메인에 맞게 조정해 데이터와 계산 비용을 줄인다.',ex:'이미지넷 모델을 제품 불량 탐지에 재학습.',rel:'사전학습;미세조정;파운데이션 모델',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['정규화','Normalization','서로 다른 규모의 값을 비슷한 범위로 맞추는 전처리.','ai_tech','ai',{detail:'큰 스케일의 특성이 학습을 지배하지 않도록 값의 범위나 분포를 조정한다.',ex:'키와 소득 값을 0~1 범위로 변환.',rel:'표준화;특성;경사하강법',src:[['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['정규화 기법','Regularization','과적합을 줄이기 위해 모델 복잡도나 가중치를 제약하는 방법.','ai_tech','ai',{detail:'손실 함수에 패널티를 추가하거나 드롭아웃처럼 학습 경로를 제한해 일반화를 돕는다.',ex:'L2 패널티로 큰 가중치 억제.',rel:'과적합;손실 함수;드롭아웃',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['제로샷 프롬프팅','Zero-shot Prompting','예시 없이 작업 지시만으로 모델에 답하게 하는 방식.','ai_tech','ai',{detail:'모델의 사전학습 지식과 지시 이해 능력에 의존해 새 작업을 수행한다.',ex:'예시 없이 \'이 리뷰의 감성을 분류해줘\'라고 요청.',rel:'퓨샷 프롬프팅;프롬프트;LLM',src:[['Brown et al. - Language Models are Few-Shot Learners','https://arxiv.org/abs/2005.14165'],['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview']]}],
    ['준지도학습','Semi-supervised Learning','소량의 레이블 데이터와 대량의 비레이블 데이터를 함께 쓰는 학습 방식.','ai_tech','ai',{detail:'레이블 비용이 높은 상황에서 비레이블 데이터의 구조를 활용해 성능을 높인다.',ex:'일부만 라벨링된 의료 이미지로 진단 모델 학습.',rel:'지도학습;비지도학습;액티브 러닝',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['지도학습','Supervised Learning','정답 레이블이 있는 데이터로 입력과 출력의 관계를 학습하는 방식.','ai_tech','ai',{detail:'모델이 예측한 출력과 실제 레이블의 차이를 줄이도록 학습한다.',ex:'고객 이탈 여부가 표시된 데이터로 이탈 예측.',rel:'분류;회귀;레이블',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['지시문 튜닝','Instruction Tuning','모델이 자연어 지시를 더 잘 따르도록 학습시키는 과정.','ai_tech','ai',{detail:'명령, 입력, 기대 답변 예시를 사용해 범용 언어 모델을 대화형 작업 수행에 맞춘다.',ex:'\'다음 문서를 요약하라\' 같은 지시에 맞춰 답변.',rel:'SFT;RLHF;프롬프트',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Brown et al. - Language Models are Few-Shot Learners','https://arxiv.org/abs/2005.14165']]}],
    ['지연시간','Latency','요청을 보낸 뒤 응답을 받기까지 걸리는 시간.','ai_tech','ai',{detail:'사용자 경험과 비용에 직접 영향을 주며 모델 크기, 토큰 수, 인프라, 캐싱에 좌우된다.',ex:'챗봇 첫 토큰 응답이 800ms 걸림.',rel:'처리량;추론;캐싱',src:[['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['청킹','Chunking','긴 문서를 검색과 문맥 투입에 적합한 작은 단위로 나누는 작업.','ai_tech','ai',{detail:'문단, 제목, 토큰 길이, 의미 단락을 기준으로 문서 조각을 만들어 검색 품질을 높인다.',ex:'40쪽 PDF를 800토큰 단위 조각으로 분할.',rel:'RAG;문맥창;검색기',src:[['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['추론 모델','Reasoning Model','복잡한 문제 해결을 위해 더 많은 내부 추론을 수행하도록 설계된 모델.','ai_tech','ai',{detail:'수학, 코딩, 계획처럼 단계적 사고가 필요한 작업에서 정확도와 검증 능력을 높이는 데 초점을 둔다.',ex:'코딩 문제의 원인을 단계적으로 분석해 수정안 제시.',rel:'사고 연쇄;계획;평가',src:[['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals'],['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview']]}],
    ['추천 시스템','Recommender System','사용자와 항목의 패턴을 학습해 적합한 콘텐츠나 상품을 제안하는 시스템.','ai_tech','ai',{detail:'사용자 행동, 유사 사용자, 항목 특징을 모델링해 개인화된 순위나 후보를 만든다.',ex:'쇼핑몰의 개인 맞춤 상품 추천.',rel:'랭킹;임베딩;협업 필터링',src:[['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['컴퓨터 비전','Computer Vision','이미지와 영상에서 객체, 장면, 패턴을 인식하는 AI 분야.','ai_tech','ai',{ac:'CV',detail:'픽셀 기반 데이터를 모델 입력으로 사용해 분류, 탐지, 분할, 추적 같은 시각 인식 작업을 수행한다.',ex:'공장 카메라로 불량품 탐지.',rel:'CNN;객체 탐지;멀티모달',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['토큰화','Tokenization','텍스트를 모델이 처리할 토큰 단위로 나누는 과정.','ai_tech','ai',{detail:'문자열을 모델의 어휘집에 맞는 정수 토큰 시퀀스로 변환한다.',ex:'문장을 하위 단어 토큰 ID 목록으로 변환.',rel:'토큰;어휘집;LLM',src:[['Hugging Face Transformers Glossary','https://huggingface.co/docs/transformers/en/glossary'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['트랜스포머','Transformer','주의 메커니즘을 중심으로 시퀀스를 병렬 처리하는 신경망 구조.','ai_tech','ai',{detail:'순환이나 합성곱 없이 self-attention으로 토큰 간 관계를 계산해 현대 LLM의 기반이 되었다.',ex:'번역 모델이 문장 전체 토큰 관계를 동시에 계산.',rel:'어텐션;LLM;인코더',src:[['Vaswani et al. - Attention Is All You Need','https://arxiv.org/abs/1706.03762'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['특성 공학','Feature Engineering','원본 데이터에서 예측에 유용한 특성을 설계하는 작업.','ai_tech','ai',{detail:'도메인 지식과 통계 처리를 이용해 모델이 더 쉽게 학습할 수 있는 입력 표현을 만든다.',ex:'구매일로부터 경과일, 최근 30일 구매액을 생성.',rel:'특성;정규화;데이터 전처리',src:[['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['편향','Bias','모델이나 데이터가 특정 방향으로 체계적으로 치우치는 현상.','ai_tech','ai',{detail:'통계적 오차, 데이터 대표성 부족, 사회적 편향이 예측 결과와 영향에 반영될 수 있다.',ex:'특정 집단에 대해 대출 승인율이 낮게 예측됨.',rel:'공정성;분산;AI 거버넌스',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['퓨샷 프롬프팅','Few-shot Prompting','입력과 출력 예시 몇 개를 함께 제공해 모델을 유도하는 방식.','ai_tech','ai',{detail:'작업 패턴과 답변 형식을 예시로 보여줘 모델이 같은 규칙을 따르게 한다.',ex:'긍정/부정 분류 예시 3개를 넣은 뒤 새 리뷰 분류.',rel:'제로샷;프롬프트 템플릿;인컨텍스트 러닝',src:[['Brown et al. - Language Models are Few-Shot Learners','https://arxiv.org/abs/2005.14165'],['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview']]}],
    ['프롬프트 엔지니어링','Prompt Engineering','모델이 원하는 결과를 내도록 입력 구조와 표현을 설계하는 방법.','ai_tech','ai',{detail:'역할, 맥락, 예시, 출력 형식, 검증 절차를 조합해 응답 품질과 일관성을 높인다.',ex:'요약 길이와 대상 독자를 명확히 지정.',rel:'프롬프트;퓨샷;구조화 출력',src:[['Anthropic Docs - Prompt engineering overview','https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview'],['OpenAI API - Structured model outputs','https://developers.openai.com/api/docs/guides/structured-outputs']]}],
    ['하이브리드 검색','Hybrid Search','키워드 검색과 벡터 검색을 함께 사용하는 검색 방식.','ai_tech','ai',{detail:'정확한 용어 일치와 의미 유사도를 결합해 단독 검색의 약점을 보완한다.',ex:'제품 코드 키워드와 설명 의미를 함께 고려.',rel:'시맨틱 검색;BM25;RAG',src:[['OpenAI API - Retrieval','https://developers.openai.com/api/docs/guides/retrieval'],['OpenAI API - Vector embeddings','https://developers.openai.com/api/docs/guides/embeddings']]}],
    ['하이퍼파라미터','Hyperparameter','학습 전에 사람이 정하는 모델과 학습 과정의 설정값.','ai_tech','ai',{detail:'모델이 데이터로 직접 학습하는 파라미터와 달리 학습률, 배치 크기, 트리 깊이처럼 외부에서 조정한다.',ex:'학습률 0.001, 배치 크기 32.',rel:'파라미터;검증 데이터;튜닝',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['학습률','Learning Rate','한 번의 업데이트에서 파라미터를 얼마나 크게 바꿀지 정하는 값.','ai_tech','ai',{detail:'너무 크면 학습이 불안정하고 너무 작으면 수렴이 느려질 수 있다.',ex:'0.1에서 발산해 0.001로 낮춤.',rel:'경사하강법;하이퍼파라미터;옵티마이저',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['함수 호출','Function Calling','모델이 정해진 함수나 API 호출 인자를 생성하도록 하는 기능.','ai_tech','ai',{detail:'자연어 요청을 구조화된 도구 호출로 바꿔 외부 시스템 조회나 작업 실행에 연결한다.',ex:'날씨 질문을 weather_api(city=\'Seoul\') 호출로 변환.',rel:'도구 사용;구조화 출력;에이전트',src:[['OpenAI API - Function calling','https://developers.openai.com/api/docs/guides/function-calling'],['OpenAI API - Structured model outputs','https://developers.openai.com/api/docs/guides/structured-outputs']]}],
    ['합성 데이터','Synthetic Data','실제 관측이 아니라 모델이나 규칙으로 생성한 데이터.','ai_tech','ai',{detail:'개인정보 보호, 희소 사례 보강, 시뮬레이션 테스트를 위해 인공적으로 만든 데이터다.',ex:'자율주행 시뮬레이터로 사고 상황 이미지 생성.',rel:'데이터 증강;개인정보보호;생성형 AI',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['합성곱 신경망','Convolutional Neural Network','이미지처럼 격자 구조 데이터에서 지역 패턴을 잘 잡는 신경망.','ai_tech','ai',{ac:'CNN',detail:'합성곱 필터로 가장자리, 질감, 형태 같은 공간적 특징을 계층적으로 학습한다.',ex:'사진에서 고양이와 개 분류.',rel:'컴퓨터 비전;객체 탐지;딥러닝',src:[['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['확산 모델','Diffusion Model','노이즈를 점진적으로 제거하며 데이터를 생성하는 생성 모델.','ai_tech','ai',{detail:'학습 중 데이터에 노이즈를 추가하고, 생성 시 노이즈에서 시작해 원본 같은 샘플로 복원한다.',ex:'텍스트 조건으로 이미지를 생성하는 모델.',rel:'이미지 생성;생성형 AI;잠재 공간',src:[['Ho et al. - Denoising Diffusion Probabilistic Models','https://arxiv.org/abs/2006.11239'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['활성화 함수','Activation Function','신경망이 비선형 관계를 학습하도록 하는 함수.','ai_tech','ai',{detail:'각 뉴런의 선형 결합 결과를 변환해 복잡한 패턴을 표현할 수 있게 한다.',ex:'ReLU로 음수 입력은 0, 양수는 그대로 통과.',rel:'ReLU;Sigmoid;신경망',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['Microsoft Learn - Deep learning vs. machine learning','https://learn.microsoft.com/en-us/azure/machine-learning/concept-deep-learning-vs-machine-learning?view=azureml-api-2']]}],
    ['회귀','Regression','연속적인 숫자 값을 예측하는 머신러닝 작업.','ai_tech','ai',{detail:'입력 특성과 목표 변수 사이의 관계를 학습해 가격, 수요, 점수처럼 수치형 결과를 예측한다.',ex:'주택 특성으로 예상 매매가 예측.',rel:'손실 함수;평균제곱오차;지도학습',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],

    // ── AI 리스크 ──
    ['가드레일','Guardrail','모델 입력, 출력, 행동을 제한하고 검사하는 안전 장치.','ai_risk','ai',{detail:'정책 필터, 도구 권한 제한, 출력 검증, 사람 승인 등을 포함해 위험한 사용을 줄인다.',ex:'결제 실행 전 사람 승인 요구.',rel:'모더레이션;휴먼 인 더 루프;과도한 대행성',src:[['OpenAI API - Function calling','https://developers.openai.com/api/docs/guides/function-calling'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['개념 드리프트','Concept Drift','입력과 정답 사이의 관계 자체가 시간이 지나며 변하는 현상.','ai_risk','ai',{detail:'같은 특성이라도 목표 변수와의 의미가 달라져 과거 모델의 판단 기준이 낡아진다.',ex:'사기 거래 패턴이 공격자 변화로 달라짐.',rel:'데이터 드리프트;모델 모니터링;재학습',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['개인정보보호 머신러닝','Privacy-preserving Machine Learning','데이터 노출을 줄이면서 모델을 학습하거나 사용하는 기술 묶음.','ai_risk','ai',{ac:'PPML',detail:'연합학습, 차등 개인정보보호, 암호화 계산 등으로 민감 정보 위험을 낮춘다.',ex:'병원별 데이터를 중앙에 모으지 않고 공동 모델 학습.',rel:'연합학습;차등 개인정보보호;민감 정보 노출',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],
    ['공정성','Fairness','AI가 개인이나 집단에 부당한 차별적 영향을 주지 않도록 하는 원칙.','ai_risk','ai',{detail:'데이터, 모델, 배포 맥락에서 집단별 오류율과 영향 차이를 분석하고 완화한다.',ex:'채용 모델의 성별별 추천율과 오류율 점검.',rel:'편향;책임성;AI 거버넌스',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],
    ['과도한 대행성','Excessive Agency','AI 시스템에 필요 이상으로 큰 권한이나 자율성을 주는 위험.','ai_risk','ai',{detail:'도구 접근, 권한, 자동 실행 범위가 넓으면 작은 오류나 공격이 큰 피해로 이어질 수 있다.',ex:'검토 없이 환불, 삭제, 송금을 자동 실행.',rel:'가드레일;휴먼 인 더 루프;OWASP LLM08',src:[['OWASP Top 10 for LLM Applications','https://owasp.org/www-project-top-10-for-large-language-model-applications/'],['OpenAI API - Function calling','https://developers.openai.com/api/docs/guides/function-calling']]}],
    ['과소적합','Underfitting','모델이 데이터의 핵심 패턴을 충분히 배우지 못한 상태.','ai_risk','ai',{detail:'모델 표현력이 부족하거나 학습이 덜 되어 훈련과 테스트 모두 성능이 낮다.',ex:'선형 모델로 복잡한 이미지 분류를 시도.',rel:'과적합;모델 용량;손실 함수',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['과적합','Overfitting','훈련 데이터에는 잘 맞지만 새 데이터에는 약한 상태.','ai_risk','ai',{detail:'모델이 실제 패턴보다 훈련 데이터의 잡음과 우연한 특징까지 학습한 경우다.',ex:'훈련 정확도는 99%인데 테스트 정확도는 70%.',rel:'일반화;정규화;검증 데이터',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['데이터 누수','Data Leakage','평가나 운영 시점에 알 수 없는 정보가 학습에 섞이는 문제.','ai_risk','ai',{detail:'훈련 데이터에 미래 정보나 테스트 데이터의 단서가 들어가 실제보다 성능이 과대평가된다.',ex:'해지 예측 모델에 해지 처리일 컬럼이 포함됨.',rel:'데이터 분할;일반화;검증 데이터',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['AWS - What is Machine Learning?','https://aws.amazon.com/what-is/machine-learning/']]}],
    ['데이터 드리프트','Data Drift','운영 입력 데이터의 분포가 학습 당시와 달라지는 현상.','ai_risk','ai',{detail:'사용자 행동, 시장 변화, 센서 변화로 입력 특성이 바뀌어 성능 저하를 유발할 수 있다.',ex:'코로나 이후 구매 패턴이 학습 데이터와 달라짐.',rel:'모델 모니터링;개념 드리프트;일반화',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['데이터 포이즈닝','Data Poisoning','훈련 데이터에 악의적 데이터를 섞어 모델을 오염시키는 공격.','ai_risk','ai',{detail:'모델 성능을 낮추거나 특정 조건에서 공격자가 원하는 행동을 하도록 학습 데이터를 조작한다.',ex:'스팸 필터 학습 데이터에 정상처럼 보이는 스팸을 대량 삽입.',rel:'백도어;공급망 취약점;MITRE ATLAS',src:[['OWASP Top 10 for LLM Applications','https://owasp.org/www-project-top-10-for-large-language-model-applications/'],['MITRE ATLAS','https://atlas.mitre.org/']]}],
    ['레드팀','Red Teaming','공격자 관점에서 모델과 시스템의 취약점을 찾아보는 평가 활동.','ai_risk','ai',{detail:'유해 출력, 보안 우회, 데이터 노출, 도구 오남용을 의도적으로 시험한다.',ex:'금지 요청 우회 프롬프트로 챗봇 안전성 테스트.',rel:'프롬프트 인젝션;가드레일;평가',src:[['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['멤버십 추론','Membership Inference','특정 데이터가 모델 학습에 포함됐는지 추정하는 공격.','ai_risk','ai',{detail:'모델이 학습 샘플에 과도하게 자신감을 보이는 패턴을 이용해 개인정보 노출 위험을 만든다.',ex:'특정 환자 기록이 학습셋에 있었는지 추정.',rel:'모델 역추론;과적합;개인정보보호',src:[['MITRE ATLAS','https://atlas.mitre.org/'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['모더레이션','Moderation','유해하거나 정책 위반인 입력과 출력을 탐지하고 처리하는 절차.','ai_risk','ai',{detail:'폭력, 혐오, 개인정보, 자해 등 위험 콘텐츠를 분류해 차단, 경고, 라우팅한다.',ex:'게시 전 생성 문구를 안전 분류기로 검사.',rel:'콘텐츠 안전;가드레일;정책',src:[['OpenAI API - Structured model outputs','https://developers.openai.com/api/docs/guides/structured-outputs'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['모델 역추론','Model Inversion','모델 출력이나 접근 권한을 이용해 훈련 데이터의 민감 정보를 추정하는 공격.','ai_risk','ai',{detail:'예측 결과와 신뢰도 등을 분석해 학습 데이터의 특징이나 개인 정보를 복원하려 한다.',ex:'얼굴 인식 모델 출력으로 학습 이미지 특징 추정.',rel:'멤버십 추론;개인정보;모델 보안',src:[['MITRE ATLAS','https://atlas.mitre.org/'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['모델 탈취','Model Theft','모델 자체나 기능을 무단 복제하거나 추출하는 공격.','ai_risk','ai',{detail:'API 질의, 가중치 유출, 저장소 침해를 통해 독점 모델과 지식재산을 빼앗을 수 있다.',ex:'대량 질의로 유사한 대체 모델을 학습.',rel:'지식재산;공급망;OWASP LLM10',src:[['OWASP Top 10 for LLM Applications','https://owasp.org/www-project-top-10-for-large-language-model-applications/'],['MITRE ATLAS','https://atlas.mitre.org/']]}],
    ['민감 정보 노출','Sensitive Information Disclosure','모델 입력, 출력, 로그, 학습 데이터에서 민감 정보가 드러나는 위험.','ai_risk','ai',{detail:'개인정보, 기밀, 인증 정보가 생성 결과나 도구 호출을 통해 노출될 수 있다.',ex:'챗봇이 이전 사용자의 이메일 주소를 답변에 포함.',rel:'개인정보;모더레이션;OWASP LLM06',src:[['OWASP Top 10 for LLM Applications','https://owasp.org/www-project-top-10-for-large-language-model-applications/'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['불안전한 출력 처리','Insecure Output Handling','LLM 출력 검증 없이 코드, 쿼리, 명령으로 실행해 생기는 취약점.','ai_risk','ai',{detail:'모델 응답을 신뢰된 입력처럼 다루면 XSS, SQL injection, 원격 코드 실행 위험이 생길 수 있다.',ex:'생성된 SQL을 검증 없이 DB에 실행.',rel:'함수 호출;구조화 출력;OWASP LLM02',src:[['OWASP Top 10 for LLM Applications','https://owasp.org/www-project-top-10-for-large-language-model-applications/'],['OpenAI API - Structured model outputs','https://developers.openai.com/api/docs/guides/structured-outputs']]}],
    ['적대적 예제','Adversarial Example','작은 조작으로 모델이 잘못 판단하게 만든 입력.','ai_risk','ai',{detail:'사람에게는 거의 같아 보이지만 모델의 분류나 행동을 바꾸도록 설계된 공격 입력이다.',ex:'정지 표지판 이미지에 작은 패턴을 붙여 오인식 유도.',rel:'적대적 ML;MITRE ATLAS;견고성',src:[['MITRE ATLAS','https://atlas.mitre.org/'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['차등 개인정보보호','Differential Privacy','개별 데이터 포함 여부가 결과에 미치는 영향을 제한하는 개인정보 보호 기법.','ai_risk','ai',{ac:'DP',detail:'통계나 학습 과정에 노이즈를 추가해 개인 정보 추론 위험을 수학적으로 낮춘다.',ex:'사용자 로그 통계를 노이즈와 함께 공개.',rel:'개인정보보호 ML;멤버십 추론;연합학습',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['콘텐츠 안전','Content Safety','유해, 불법, 차별적, 위험한 콘텐츠 생성을 줄이는 정책과 기술.','ai_risk','ai',{detail:'모델 정책, 필터, 평가, 사용자 흐름 설계를 통해 안전한 사용 범위를 관리한다.',ex:'자해 조언 대신 도움 요청 안내를 제공.',rel:'모더레이션;가드레일;레드팀',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],
    ['탈옥','Jailbreak','모델의 안전 제한이나 정책을 우회하려는 입력 기법.','ai_risk','ai',{detail:'위험한 지시를 우회 표현, 역할극, 다단계 요청으로 감싸 제한된 출력을 유도한다.',ex:'금지된 조작법을 우회적으로 묻기.',rel:'프롬프트 인젝션;가드레일;레드팀',src:[['OWASP Top 10 for LLM Applications','https://owasp.org/www-project-top-10-for-large-language-model-applications/'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['프롬프트 인젝션','Prompt Injection','악의적 입력이 모델 지시 체계를 교란해 의도치 않은 행동을 유발하는 공격.','ai_risk','ai',{detail:'직접 입력이나 외부 문서 속 지시가 시스템 규칙을 우회하도록 모델을 속이는 LLM 보안 취약점이다.',ex:'문서 안의 \'이전 지시를 무시하라\'를 모델이 따름.',rel:'간접 프롬프트 인젝션;가드레일;OWASP LLM01',src:[['OWASP Top 10 for LLM Applications','https://owasp.org/www-project-top-10-for-large-language-model-applications/'],['MITRE ATLAS','https://atlas.mitre.org/']]}],
    ['환각','Hallucination','모델이 사실이 아니거나 근거 없는 내용을 그럴듯하게 생성하는 현상.','ai_risk','ai',{detail:'언어적으로 자연스러워 보여도 출처, 계산, 사실관계가 틀릴 수 있어 검증이 필요하다.',ex:'존재하지 않는 논문 제목과 저자를 만들어냄.',rel:'그라운딩;RAG;평가',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['휴먼 인 더 루프','Human-in-the-loop','중요 판단이나 작업에 사람의 검토와 승인을 포함하는 방식.','ai_risk','ai',{ac:'HITL',detail:'자동화의 위험을 줄이기 위해 민감한 단계에서 사람이 확인하거나 수정한다.',ex:'환불 승인 전 상담원이 모델 제안을 검토.',rel:'가드레일;액티브 러닝;책임성',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],

    // ── AI 거버넌스 ──
    ['AI 경영시스템','AI Management System','조직의 AI 개발과 운영을 관리하기 위한 국제 표준 기반 경영시스템.','ai_gov','ai',{ac:'ISO/IEC 42001',detail:'정책, 책임, 위험관리, 운영 통제, 지속 개선을 통해 AI 시스템 관리 체계를 구축한다.',ex:'기업 전사 AI 사용 정책과 감사 절차 수립.',rel:'AI RMF;책임성;거버넌스',src:[['ISO/IEC 42001:2023 AI management systems','https://www.iso.org/standard/42001'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['AI 리터러시','AI Literacy','AI의 능력, 한계, 위험을 이해하고 적절히 사용할 수 있는 역량.','ai_gov','ai',{detail:'조직 구성원과 사용자가 AI 결과를 비판적으로 해석하고 책임 있게 활용하도록 돕는다.',ex:'직원에게 환각과 개인정보 입력 금지 교육.',rel:'투명성;책임성;AI 거버넌스',src:[['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],
    ['AI 위험관리 프레임워크','AI Risk Management Framework','AI 위험을 식별, 측정, 관리, 거버넌스하기 위한 NIST 프레임워크.','ai_gov','ai',{ac:'AI RMF',detail:'조직이 AI 시스템의 신뢰성, 안전성, 공정성, 투명성 위험을 체계적으로 관리하도록 돕는다.',ex:'AI 서비스 출시 전 Map, Measure, Manage 절차로 위험 평가.',rel:'NIST;AI 거버넌스;견고성',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['ISO/IEC 42001:2023 AI management systems','https://www.iso.org/standard/42001']]}],
    ['EU AI 법','European Union Artificial Intelligence Act','AI 시스템을 위험 기반으로 규제하는 유럽연합 법 체계.','ai_gov','ai',{ac:'EU AI Act',detail:'AI 시스템, 제공자, 배포자, 고위험 AI, 범용 AI 모델 등 핵심 정의와 의무를 제시한다.',ex:'고위험 채용 AI에 문서화와 인간 감독 요구.',rel:'고위험 AI;투명성;AI 거버넌스',src:[['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],
    ['고위험 AI','High-risk AI System','사람의 권리와 안전에 중대한 영향을 줄 수 있어 강화된 의무가 적용되는 AI.','ai_gov','ai',{detail:'채용, 교육, 필수 서비스, 법 집행 등 민감 영역에서 위험 기반 요구사항을 충족해야 한다.',ex:'채용 지원자 선별 AI의 편향과 설명 의무 점검.',rel:'EU AI Act;위험관리;인간 감독',src:[['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['기술 문서화','Technical Documentation','AI 시스템의 설계, 데이터, 성능, 위험관리 정보를 기록하는 문서.','ai_gov','ai',{detail:'규제 준수, 감사, 재현성, 변경 관리를 위해 모델과 시스템 수명주기 정보를 남긴다.',ex:'학습 데이터 출처, 모델 버전, 테스트 결과를 문서화.',rel:'모델 카드;AI Act;모델 레지스트리',src:[['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/'],['ISO/IEC 42001:2023 AI management systems','https://www.iso.org/standard/42001']]}],
    ['범용 AI 모델','General-purpose AI Model','여러 목적과 시스템에 통합될 수 있는 범용 AI 모델.','ai_gov','ai',{ac:'GPAI',detail:'특정 단일 작업에 한정되지 않고 다양한 다운스트림 용도로 재사용될 수 있는 모델이다.',ex:'범용 언어 모델을 고객지원, 분석, 코딩에 통합.',rel:'파운데이션 모델;EU AI Act;LLM',src:[['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/'],['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework']]}],
    ['위험관리','Risk Management','AI 시스템의 위험을 식별, 평가, 완화, 모니터링하는 지속적 과정.','ai_gov','ai',{detail:'기술적 오류뿐 아니라 사회적 영향, 보안, 개인정보, 운영 리스크를 포함한다.',ex:'출시 전 위험 등록부와 완화 조치 작성.',rel:'AI RMF;ISO 42001;모니터링',src:[['NIST AI Risk Management Framework','https://www.nist.gov/itl/ai-risk-management-framework'],['ISO/IEC 42001:2023 AI management systems','https://www.iso.org/standard/42001']]}],
    ['인간 감독','Human Oversight','AI 결정이나 행동을 사람이 이해하고 개입할 수 있게 하는 통제.','ai_gov','ai',{detail:'고위험 상황에서 자동화 오류를 발견하고 중단, 수정, 승인할 권한을 사람에게 부여한다.',ex:'의료 AI 진단 제안을 의사가 최종 검토.',rel:'휴먼 인 더 루프;고위험 AI;책임성',src:[['EU AI Act - Article 3 Definitions','https://artificialintelligenceact.eu/article/3/'],['OECD AI Principles','https://oecd.ai/en/ai-principles']]}],

    // ── AI 지표 ──
    ['F1 점수','F1 Score','정밀도와 재현율의 조화평균.','ai_metric','ai',{ac:'F1',detail:'정밀도와 재현율 사이 균형을 하나의 숫자로 요약해 불균형 데이터 평가에 자주 쓴다.',ex:'스팸 탐지 모델 비교에 F1 사용.',rel:'정밀도;재현율;분류',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],
    ['ROC-AUC','Area Under the ROC Curve','분류 모델이 양성과 음성을 구분하는 능력을 나타내는 지표.','ai_metric','ai',{ac:'ROC-AUC',detail:'여러 임계값에서 참양성률과 거짓양성률의 관계를 면적으로 요약한다.',ex:'신용 위험 모델의 구분력을 AUC로 비교.',rel:'ROC 곡선;분류;임계값',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],
    ['재현율','Recall','실제 양성 중 모델이 양성으로 찾아낸 비율.','ai_metric','ai',{detail:'놓치면 안 되는 사례가 많은 의료, 사기 탐지에서 중요하다.',ex:'실제 암 환자 중 모델이 양성으로 탐지한 비율.',rel:'정밀도;F1;거짓 음성',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],
    ['정밀도','Precision','양성으로 예측한 것 중 실제 양성인 비율.','ai_metric','ai',{detail:'거짓 양성을 줄이는 것이 중요한 분류 문제에서 핵심 지표다.',ex:'스팸이라고 표시한 메일 중 실제 스팸 비율.',rel:'재현율;F1;혼동 행렬',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],
    ['정확도','Accuracy','전체 예측 중 맞힌 비율.','ai_metric','ai',{detail:'분류 문제에서 직관적이지만 클래스 불균형이 심하면 성능을 과대평가할 수 있다.',ex:'100건 중 85건을 맞혀 정확도 85%.',rel:'정밀도;재현율;혼동 행렬',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],
    ['퍼플렉서티','Perplexity','언어 모델이 다음 토큰을 얼마나 잘 예측하는지 나타내는 지표.','ai_metric','ai',{ac:'PPL',detail:'낮을수록 평가 텍스트에 더 높은 확률을 부여하지만 실제 사용자 품질과 항상 일치하지는 않는다.',ex:'언어 모델 A의 PPL이 B보다 낮음.',rel:'LLM;벤치마크;손실 함수',src:[['Hugging Face Transformers Glossary','https://huggingface.co/docs/transformers/en/glossary'],['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary']]}],
    ['혼동 행렬','Confusion Matrix','분류 결과를 실제/예측 조합별 건수로 정리한 표.','ai_metric','ai',{detail:'참양성, 거짓양성, 참음성, 거짓음성을 보여줘 어떤 오류가 많은지 분석한다.',ex:'암 진단 모델의 누락과 오탐 건수 확인.',rel:'정확도;정밀도;재현율',src:[['Google Machine Learning Glossary','https://developers.google.com/machine-learning/glossary'],['OpenAI API - Working with evals','https://developers.openai.com/api/docs/guides/evals']]}],

    // ── 보존(고유 GEO/기타) ──
    ['할루시네이션','Hallucination','AI가 사실이 아닌 내용을 그럴듯하게 지어내는 현상. 의료 정보에서 특히 주의가 필요.','ai_risk','ai'],
    ['챗봇','Chatbot','사람과 대화하듯 질문에 답하고 상담·예약을 돕는 AI 대화형 프로그램.','ai_basic','ai'],
    ['AI 에이전트','AI Agent','목표를 스스로 계획하고 도구를 사용해 여러 단계를 자동 수행하는 AI.','ai_tech','ai'],
    ['GEO','GEO','Generative Engine Optimization, 생성형 AI가 병원·브랜드를 추천·인용하도록 최적화하는 전략.','ai_geo','ai'],
    ['AEO','AEO','Answer Engine Optimization, AI 답변 엔진이 우리 콘텐츠를 답변으로 채택하도록 최적화하는 작업.','ai_geo','ai'],
    ['AI 오버뷰(개요)','AI Overviews','구글 검색 상단에 AI가 요약해 보여주는 생성형 답변 영역. 노출 시 브랜드 신뢰도가 크게 상승.','ai_geo','ai'],
    ['엔티티','Entity','사람·장소·브랜드·개념 등 검색엔진과 AI가 하나의 대상으로 인식하는 개체.','ai_geo','ai'],
    ['지식 그래프','Knowledge Graph','엔티티와 그 관계를 연결해 구글이 정보를 이해하는 데 쓰는 지식 데이터베이스.','ai_geo','ai'],
    ['제로클릭 검색','Zero-click search','검색결과나 AI 답변만으로 정보가 해결돼 사이트를 클릭하지 않고 끝나는 검색.','ai_geo','ai'],
    ['시맨틱 마크업','Semantic markup','AI·검색엔진이 콘텐츠의 의미를 파악하도록 구조화 데이터로 표시하는 작업.','ai_geo','ai'],
    ['RAG(검색증강생성)','RAG','Retrieval-Augmented Generation, 외부 문서를 검색해 근거로 삼아 답변 정확도를 높이는 기법.','ai_tech','ai'],
    ['파인튜닝','Fine-tuning','사전학습된 AI 모델을 특정 도메인·업무 데이터로 추가 학습시켜 전문화하는 작업.','ai_tech','ai'],
    ['컨텍스트 윈도우','Context window','AI가 한 번에 기억·처리할 수 있는 토큰(문맥)의 최대 범위.','ai_tech','ai'],

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
    ['UTM','UTM Parameter','URL 뒤에 붙여 유입 캠페인·매체·소재를 구분해 추적하는 표준 파라미터.','mkt_channel','marketing'],
    ['옴니채널','Omnichannel','온·오프라인 채널을 끊김 없이 통합해 일관된 고객 경험을 제공하는 전략.','mkt_strategy','marketing'],
    ['퍼스트파티 데이터','First-party Data','기업이 고객에게서 직접 수집한 자사 데이터. 쿠키 규제 시대의 핵심 자산.','mkt_strategy','marketing'],
    ['리퍼럴','Referral','기존 고객의 추천·소개를 통해 새 고객을 얻는 유입.','mkt_channel','marketing'],
    ['숏폼','Short-form','15~60초 세로형 영상 콘텐츠(릴스·쇼츠·틱톡). 도달 확장에 강력.','mkt_channel','marketing'],

    // ═══════════════ 개발 용어사전 ═══════════════
    // ── 프론트엔드 ──
    ['프론트엔드','Frontend','사용자가 직접 보고 상호작용하는 화면(UI)을 만드는 웹 개발 영역.','dev_frontend','dev'],
    ['HTML','HTML','웹 페이지의 구조와 콘텐츠를 정의하는 마크업 언어.','dev_frontend','dev'],
    ['CSS','CSS','웹 페이지의 색·글꼴·레이아웃 등 디자인을 지정하는 스타일 언어.','dev_frontend','dev'],
    ['자바스크립트','JavaScript','웹 페이지에 동적 기능과 상호작용을 더하는 프로그래밍 언어.','dev_frontend','dev'],
    ['프레임워크','Framework','반복되는 개발 작업을 표준화해 앱을 빠르게 만들도록 돕는 코드 뼈대.','dev_frontend','dev'],
    ['라이브러리','Library','특정 기능을 미리 만들어 가져다 쓰는 재사용 코드 모음.','dev_frontend','dev'],
    ['리액트','React','컴포넌트 단위로 UI를 구성하는 대표적인 프론트엔드 라이브러리.','dev_frontend','dev'],
    ['컴포넌트','Component','버튼·카드처럼 재사용 가능한 독립적인 UI 조각.','dev_frontend','dev'],
    ['SPA','SPA','Single Page Application, 페이지 전체를 새로고침하지 않고 화면을 바꾸는 웹앱 방식.','dev_frontend','dev'],
    ['반응형','Responsive','화면 크기에 따라 레이아웃이 자동으로 맞춰지는 디자인 방식.','dev_frontend','dev'],
    ['DOM','DOM','Document Object Model, 브라우저가 HTML을 객체 구조로 다루는 모델.','dev_frontend','dev'],
    ['웹 접근성','Accessibility','장애 여부와 관계없이 누구나 웹을 이용할 수 있게 만드는 설계 원칙.','dev_frontend','dev'],

    // ── 백엔드·API ──
    ['백엔드','Backend','서버·데이터베이스 등 화면 뒤에서 데이터를 처리하는 개발 영역.','dev_backend','dev'],
    ['서버','Server','요청을 받아 처리하고 응답을 돌려주는 컴퓨터·프로그램.','dev_backend','dev'],
    ['데이터베이스','Database','데이터를 체계적으로 저장·검색·관리하는 시스템(MySQL·PostgreSQL 등).','dev_backend','dev'],
    ['API','API','Application Programming Interface, 프로그램끼리 데이터를 주고받는 규약·창구.','dev_backend','dev'],
    ['REST API','REST API','HTTP 규약으로 자원을 주소(URL)와 메서드로 다루는 API 설계 방식.','dev_backend','dev'],
    ['엔드포인트','Endpoint','API에 접근하는 개별 주소(URL). 요청을 받는 창구.','dev_backend','dev'],
    ['JSON','JSON','사람이 읽기 쉬운 텍스트로 데이터를 표현·교환하는 표준 형식.','dev_backend','dev'],
    ['인증','Authentication','사용자가 누구인지 확인하는 절차(로그인 등).','dev_backend','dev'],
    ['권한 관리','Authorization','인증된 사용자가 무엇을 할 수 있는지 허용 범위를 정하는 것.','dev_backend','dev'],
    ['쿼리','Query','데이터베이스에 원하는 데이터를 요청하는 명령.','dev_backend','dev'],
    ['캐시','Cache','자주 쓰는 데이터를 임시 저장해 응답 속도를 높이는 기술.','dev_backend','dev'],
    ['웹훅','Webhook','특정 이벤트가 생기면 지정한 주소로 자동 알림을 보내는 방식.','dev_backend','dev'],
    ['SDK','SDK','Software Development Kit, 특정 플랫폼용 앱 개발을 돕는 도구·코드 모음.','dev_backend','dev'],

    // ── 인프라·배포 ──
    ['배포','Deployment','완성된 코드를 실제 서비스 환경에 올려 사용자가 쓰게 하는 작업.','dev_infra','dev'],
    ['CI/CD','CI/CD','코드 통합·테스트·배포를 자동화하는 개발 파이프라인.','dev_infra','dev'],
    ['깃','Git','코드 변경 이력을 관리하는 분산 버전 관리 시스템.','dev_infra','dev'],
    ['깃허브','GitHub','Git 저장소를 클라우드에서 협업·관리하는 대표 플랫폼.','dev_infra','dev'],
    ['저장소','Repository','프로젝트 코드와 변경 이력이 저장되는 공간(리포지토리).','dev_infra','dev'],
    ['브랜치','Branch','원본을 건드리지 않고 독립적으로 작업하는 코드 분기.','dev_infra','dev'],
    ['클라우드','Cloud','서버·저장소를 직접 소유하지 않고 인터넷으로 빌려 쓰는 방식.','dev_infra','dev'],
    ['CDN','CDN','Content Delivery Network, 콘텐츠를 사용자와 가까운 서버에서 빠르게 전달하는 망.','dev_infra','dev'],
    ['도메인','Domain','사이트 주소로 쓰이는 사람이 읽기 쉬운 이름(example.com).','dev_infra','dev'],
    ['환경변수','Environment Variable','API 키 등 민감·설정 값을 코드 밖에서 주입하는 변수.','dev_infra','dev'],
    ['서버리스','Serverless','서버 관리 없이 함수 단위로 코드를 실행하는 클라우드 방식.','dev_infra','dev'],

    // ── 개발 일반 ──
    ['오픈소스','Open Source','소스코드를 공개해 누구나 보고 수정·기여할 수 있는 소프트웨어.','dev_common','dev'],
    ['버그','Bug','프로그램이 의도와 다르게 동작하게 만드는 결함·오류.','dev_common','dev'],
    ['디버깅','Debugging','버그의 원인을 찾아 고치는 과정.','dev_common','dev'],
    ['리팩터링','Refactoring','동작은 그대로 두고 코드 구조를 더 깔끔하게 개선하는 작업.','dev_common','dev'],
    ['오픈 API','Open API','외부 개발자가 쓸 수 있도록 규격을 공개한 API.','dev_common','dev'],
    ['레이턴시','Latency','요청 후 응답이 올 때까지 걸리는 지연 시간.','dev_common','dev'],
    ['버전 관리','Version Control','코드의 변경 이력을 기록·추적해 되돌리거나 협업할 수 있게 하는 관리.','dev_common','dev'],
    ['테스트','Test','코드가 의도대로 동작하는지 자동·수동으로 확인하는 절차.','dev_common','dev']
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
    if (state.q) {
      var x = t[5] || {};
      var hay = (t[0] + ' ' + t[1] + ' ' + t[2] + ' ' + (x.ac || '') + ' ' + (x.detail || '') + ' ' + (x.rel || '')).toLowerCase();
      if (hay.indexOf(state.q.toLowerCase()) < 0) return false;
    }
    return true;
  }

  function buildCards() {
    var list = TERMS.filter(match).sort(function (a, b) { return a[0].localeCompare(b[0], 'ko'); });
    if (!list.length) return '<p class="gl-empty">검색 결과가 없습니다. 다른 키워드로 찾아보세요.</p>';
    var cards = list.map(function (t) {
      var c = CATS[t[3]] || CATS.basic;
      var x = t[5] || {};
      var enLine = esc(t[1]) + (x.ac ? ' <span class="gl-ac">' + esc(x.ac) + '</span>' : '');
      var more = '';
      if (x.detail || x.ex || (x.src && x.src.length)) {
        var inner = '';
        if (x.detail) inner += '<p class="gl-detail">' + esc(x.detail) + '</p>';
        if (x.ex) inner += '<p class="gl-ex"><b>예시</b> ' + esc(x.ex) + '</p>';
        if (x.rel) inner += '<p class="gl-rel"><b>관련</b> ' + esc(x.rel).split(';').map(function (r) { return '<span class="gl-tag">' + r.trim() + '</span>'; }).join('') + '</p>';
        if (x.src && x.src.length) {
          inner += '<p class="gl-src"><b>출처</b> ' + x.src.map(function (s) {
            return '<a href="' + esc(s[1]) + '" target="_blank" rel="noopener nofollow">' + esc(s[0]) + '</a>';
          }).join('<span class="gl-src-sep">·</span>') + '</p>';
        }
        more = '<details class="gl-more"><summary>자세히 보기</summary><div class="gl-more-in">' + inner + '</div></details>';
      }
      return '<div class="gl-card">'
        + '<div class="gl-top"><span class="gl-term">' + esc(t[0]) + '</span><span class="gl-cat" style="--c:' + c.color + '">' + c.label + '</span></div>'
        + '<div class="gl-en">' + enLine + '</div>'
        + '<p class="gl-def">' + esc(t[2]) + '</p>' + more + '</div>';
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
      '.gl-ac{font-size:10.5px;font-weight:800;color:var(--mute,#64748d);background:color-mix(in srgb,var(--p,#533afd) 8%,#fff);padding:1px 6px;border-radius:6px;margin-left:5px;letter-spacing:.3px}',
      '.gl-more{margin-top:10px;border-top:1px dashed var(--border,#e3e8ee);padding-top:8px}',
      '.gl-more summary{font-size:12px;font-weight:800;color:var(--p,#533afd);cursor:pointer;list-style:none;user-select:none}',
      '.gl-more summary::-webkit-details-marker{display:none}',
      '.gl-more summary::before{content:"＋ ";font-weight:800}',
      '.gl-more[open] summary::before{content:"－ "}',
      '.gl-more-in{padding-top:8px}',
      '.gl-more-in p{font-size:12.5px;line-height:1.6;color:var(--ink2,#475569);margin:0 0 7px}',
      '.gl-more-in b{color:var(--bd,#1c1e54);font-weight:800;margin-right:4px}',
      '.gl-tag{display:inline-block;font-size:11px;font-weight:700;color:var(--p,#533afd);background:color-mix(in srgb,var(--p,#533afd) 9%,#fff);padding:2px 8px;border-radius:10px;margin:2px 4px 2px 0}',
      '.gl-src a{color:var(--p,#533afd);font-weight:700;text-decoration:none;border-bottom:1px solid color-mix(in srgb,var(--p,#533afd) 40%,#fff)}',
      '.gl-src a:hover{border-bottom-color:var(--p,#533afd)}',
      '.gl-src-sep{color:var(--mute,#94a3b8);margin:0 7px}',
      '.gl-empty{padding:40px;text-align:center;color:var(--mute,#64748d)}'
    ].join('');
    document.head.appendChild(s);
  }

  root.Glossary = { mount: mount, TERMS: TERMS, DICTS: DICTS, count: TERMS.length };
})(typeof window !== 'undefined' ? window : this);
