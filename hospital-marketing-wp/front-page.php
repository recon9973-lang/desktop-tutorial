<?php get_header(); ?>

<!-- ===== HERO ===== -->
<section class="hero" id="hero">
  <div class="container">
    <div class="hero-content fade-up">
      <div class="hero-badge">🏥 AI 시대 병원마케팅 전문</div>
      <h1>AI 검색에 직접 인용되는<br><span class="text-gradient">병원마케팅 전문 대행사</span></h1>
      <p class="hero-sub">
        광고비 95%가 낭비되는 구조를 끊고,<br>
        SEO·AEO·GEO 통합 전략으로 ChatGPT·Perplexity·네이버AI에<br>
        당신의 병원이 직접 인용되도록 만듭니다.
      </p>
      <div class="hero-ctas">
        <a href="<?php echo esc_url(home_url('/contact/')); ?>" class="btn btn-primary">무료 마케팅 진단 받기 →</a>
        <a href="<?php echo esc_url(home_url('/services/')); ?>" class="btn btn-outline">서비스 알아보기</a>
      </div>
      <div class="hero-stats">
        <div class="hero-stat-item">
          <div class="hero-stat-num">200+</div>
          <div class="hero-stat-label">협력 병원</div>
        </div>
        <div class="hero-stat-item">
          <div class="hero-stat-num">350%</div>
          <div class="hero-stat-label">평균 트래픽 증가</div>
        </div>
        <div class="hero-stat-item">
          <div class="hero-stat-num">5년+</div>
          <div class="hero-stat-label">전문 운영</div>
        </div>
        <div class="hero-stat-item">
          <div class="hero-stat-num">15%</div>
          <div class="hero-stat-label">AI 트래픽 비중</div>
        </div>
      </div>
    </div>
  </div>
  <svg class="hero-wave" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 60" preserveAspectRatio="none">
    <path fill="#ffffff" d="M0,40 C360,80 1080,0 1440,40 L1440,60 L0,60 Z"/>
  </svg>
</section>

<!-- ===== STATS ===== -->
<section class="section-sm" style="background:#fff">
  <div class="container">
    <div class="stats-grid fade-up">
      <div class="stat-item">
        <div class="stat-num">15%</div>
        <div class="stat-label">병원 업종 AI 트래픽 비중 (2026)</div>
      </div>
      <div class="stat-item">
        <div class="stat-num">30%↓</div>
        <div class="stat-label">구글 AI Overview 도입 후 클릭률 감소</div>
      </div>
      <div class="stat-item">
        <div class="stat-num">2억+</div>
        <div class="stat-label">ChatGPT 월간 활성 사용자</div>
      </div>
      <div class="stat-item">
        <div class="stat-num">95%</div>
        <div class="stat-label">기존 광고비 구조적 낭비율</div>
      </div>
    </div>
  </div>
</section>

<!-- ===== PROBLEM (next-t 비교 패턴) ===== -->
<section class="section section-gray">
  <div class="container">
    <div class="section-header fade-up">
      <span class="section-badge badge-orange">CORE PROBLEM</span>
      <h2>광고비 95%가 낭비되는<br>구조적 이유</h2>
      <p>AI가 직접 답변하는 시대, 클릭 없이 결정이 이루어집니다</p>
    </div>
    <div class="comparison-block fade-up">
      <div class="comparison-col bad">
        <h3>❌ 기존 병원마케팅 방식</h3>
        <ul class="comparison-list">
          <li><span class="icon">✗</span>네이버 파워링크 CPC 의존</li>
          <li><span class="icon">✗</span>클릭 단가 지속 상승 (월 300만원+)</li>
          <li><span class="icon">✗</span>AI 검색에서 클릭 자체가 사라짐</li>
          <li><span class="icon">✗</span>광고 중단 = 트래픽 즉시 0</li>
          <li><span class="icon">✗</span>콘텐츠 자산이 남지 않음</li>
          <li><span class="icon">✗</span>AI 답변 소스로 인용 불가</li>
        </ul>
        <div class="comparison-time">⏱ 지속 비용: 월 300~500만원</div>
      </div>
      <div class="comparison-col good">
        <h3>✅ SEO·AEO·GEO 통합 전략</h3>
        <ul class="comparison-list">
          <li><span class="icon">✓</span>AI 검색에서 무료로 직접 인용</li>
          <li><span class="icon">✓</span>콘텐츠가 영구 자산으로 누적</li>
          <li><span class="icon">✓</span>ChatGPT·Perplexity 답변 소스화</li>
          <li><span class="icon">✓</span>광고 없이 지속적 트래픽 유입</li>
          <li><span class="icon">✓</span>병원 전문성·신뢰도 자동 강화</li>
          <li><span class="icon">✓</span>한 번 구축하면 반영구적 작동</li>
        </ul>
        <div class="comparison-time">⚡ 초기 투자 후 지속 효과</div>
      </div>
    </div>
  </div>
</section>

<!-- ===== SEO→AEO→GEO 3단계 진화 ===== -->
<section class="section section-dark">
  <div class="container">
    <div class="section-header fade-up">
      <span class="section-badge badge-blue">FRAMEWORK</span>
      <h2>SEO · AEO · GEO<br>3단계 진화</h2>
      <p style="color:rgba(255,255,255,.7)">발견 → 채택 → 인용. 세 전략을 동시에 구현할 때 최대 효과</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:24px" class="fade-up">
      <?php
      $steps = [
        ['2010~', 'SEO', '발견', '#2563EB', 'badge-blue', '검색엔진 결과 페이지(SERP)에서 상위 노출되도록 키워드·링크·콘텐츠를 최적화합니다.', ['키워드 최적화','테크니컬 SEO','백링크 구축']],
        ['2020~', 'AEO', '채택', '#10B981', 'badge-green', '답변 엔진(People Also Ask·Featured Snippet)이 신뢰 출처로 채택하도록 구조·권위를 최적화합니다.', ['FAQ 구조화','역피라미드 구조','음성검색 최적화']],
        ['2024~', 'GEO', '인용', '#06B6D4', 'badge-orange', '생성형 AI 답변 안에 병원 브랜드가 인용 출처로 등장하도록 콘텐츠 구조·스키마·신뢰 신호를 최적화합니다.', ['llms.txt 설정','Schema 자동화','AI 크롤러 허용']],
      ];
      foreach ($steps as $idx => $s):
      ?>
      <div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:32px" class="stagger-<?php echo $idx+1; ?>">
        <span style="font-size:.75rem;font-weight:700;color:<?php echo $s[3]; ?>;letter-spacing:.1em"><?php echo $s[0]; ?> <?php echo $s[2]; ?></span>
        <h3 style="font-size:2rem;color:#fff;margin:8px 0 16px"><?php echo $s[1]; ?></h3>
        <p style="color:rgba(255,255,255,.7);font-size:.875rem;margin-bottom:20px"><?php echo $s[5]; ?></p>
        <ul style="list-style:none">
          <?php foreach ($s[6] as $item): ?>
          <li style="font-size:.8rem;color:rgba(255,255,255,.6);padding:4px 0;display:flex;gap:8px;align-items:center">
            <span style="color:<?php echo $s[3]; ?>">✓</span><?php echo $item; ?>
          </li>
          <?php endforeach; ?>
        </ul>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ===== 5-STEP PROCESS (next-t 패턴) ===== -->
<section class="section">
  <div class="container">
    <div class="section-header fade-up">
      <span class="section-badge badge-blue">PROCESS OVERVIEW</span>
      <h2>병원마케팅 5-Step 프로세스</h2>
      <p>진단부터 AI 인용까지, 체계적인 프로세스로 실행합니다</p>
    </div>
    <div class="steps-grid fade-up">
      <?php
      $process = [
        ['01','현황 진단','병원 마케팅 현황 분석 리포트 제공'],
        ['02','키워드 전략','검색 의도·경쟁사 키워드 맵 수립'],
        ['03','콘텐츠 설계','SEO·AEO·GEO 최적화 콘텐츠 제작'],
        ['04','기술 최적화','테크니컬 SEO·Schema·llms.txt'],
        ['05','성과 측정','KPI 추적·GEO Score·월간 리포트'],
      ];
      foreach ($process as $p):
      ?>
      <div class="step-card">
        <div class="step-num"><?php echo $p[0]; ?></div>
        <div class="step-title"><?php echo $p[1]; ?></div>
        <div class="step-desc"><?php echo $p[2]; ?></div>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ===== SERVICES ===== -->
<section class="section section-gray">
  <div class="container">
    <div class="section-header fade-up">
      <span class="section-badge badge-blue">SERVICES</span>
      <h2>병원마케팅 전문 서비스</h2>
      <p>병원 업종에 특화된 SEO·AEO·GEO 통합 서비스를 제공합니다</p>
    </div>
    <div class="services-grid fade-up">
      <?php
      $services = [
        ['🔍','SEO 서비스','구글·네이버 검색 상위 노출. 테크니컬 SEO, 콘텐츠 최적화, 로컬 SEO 통합 제공.','/services/seo/'],
        ['🤖','GEO 서비스','ChatGPT·Perplexity·Gemini 답변에 병원이 인용되도록 최적화합니다.','/services/geo/'],
        ['🎤','AEO 서비스','음성검색·네이버 AI 답변에 채택되는 FAQ 구조화 콘텐츠 전략.','/services/aeo/'],
        ['🏥','병원마케팅 광고','의료법 준수 네이버·구글 광고 대행. 낭비 없는 타겟 광고 운영.','/services/hospital-marketing/'],
        ['💻','홈페이지 제작','GEO·AEO·SEO가 내장된 병원 홈페이지 제작. 워드프레스 기반.','/services/website/'],
        ['📱','SNS·블로그 운영','인스타그램·블로그 전문 운영. AI 콘텐츠 + 전문가 검수.','/services/sns/'],
      ];
      foreach ($services as $idx => $s):
      ?>
      <div class="service-card stagger-<?php echo $idx+1; ?>">
        <div class="service-icon"><?php echo $s[0]; ?></div>
        <h3><?php echo $s[1]; ?></h3>
        <p><?php echo $s[2]; ?></p>
        <a href="<?php echo esc_url(home_url($s[3])); ?>" class="link-more">자세히 보기 →</a>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ===== SPECIALTY ===== -->
<section class="section">
  <div class="container">
    <div class="section-header fade-up">
      <span class="section-badge badge-green">BY SPECIALTY</span>
      <h2>병과별 전문 마케팅</h2>
      <p>진료과 특성에 맞는 맞춤형 SEO·GEO 전략</p>
    </div>
    <div class="specialty-grid fade-up">
      <?php
      $specs = [
        ['💉','성형외과','/specialty/plastic-surgery/'],
        ['✨','피부과','/specialty/dermatology/'],
        ['🦷','치과','/specialty/dental/'],
        ['🦴','정형외과','/specialty/orthopedic/'],
        ['🌿','한의원','/specialty/oriental/'],
        ['⚖️','비만클리닉','/specialty/obesity/'],
      ];
      foreach ($specs as $s):
      ?>
      <a href="<?php echo esc_url(home_url($s[2])); ?>" class="specialty-card">
        <div class="icon"><?php echo $s[0]; ?></div>
        <div class="name"><?php echo $s[1]; ?></div>
      </a>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ===== CASE STUDIES ===== -->
<section class="section section-gray">
  <div class="container">
    <div class="section-header fade-up">
      <span class="section-badge badge-green">TRACK RECORD</span>
      <h2>실제 성과 사례</h2>
      <p>숫자로 증명하는 병원마케팅 성과</p>
    </div>
    <div class="cases-grid fade-up">
      <?php
      $case_query = new WP_Query([
        'post_type'      => 'case_study',
        'posts_per_page' => 3,
        'post_status'    => 'publish',
      ]);
      if ( $case_query->have_posts() ) :
        while ( $case_query->have_posts() ) : $case_query->the_post();
          $m1n = get_post_meta(get_the_ID(), '_mm_metric1_num', true);
          $m1l = get_post_meta(get_the_ID(), '_mm_metric1_label', true);
          $m2n = get_post_meta(get_the_ID(), '_mm_metric2_num', true);
          $m2l = get_post_meta(get_the_ID(), '_mm_metric2_label', true);
          $sp  = get_post_meta(get_the_ID(), '_mm_case_specialty', true);
      ?>
      <div class="case-card">
        <div class="case-body">
          <?php if ($sp): ?><span class="case-tag"><?php echo esc_html($sp); ?></span><?php endif; ?>
          <h3><?php the_title(); ?></h3>
          <p style="font-size:.875rem;color:#6B7280"><?php echo wp_trim_words(get_the_excerpt(), 20); ?></p>
          <div class="case-metrics">
            <?php if ($m1n): ?>
            <div><div class="case-metric-num"><?php echo esc_html($m1n); ?></div><div class="case-metric-label"><?php echo esc_html($m1l); ?></div></div>
            <?php endif; ?>
            <?php if ($m2n): ?>
            <div><div class="case-metric-num"><?php echo esc_html($m2n); ?></div><div class="case-metric-label"><?php echo esc_html($m2l); ?></div></div>
            <?php endif; ?>
          </div>
        </div>
      </div>
      <?php endwhile; wp_reset_postdata();
      else:
        // 더미 사례 (실제 포스트 없을 때)
        $dummy = [
          ['성형외과','강남 성형외과 클리닉','네이버 블로그+SEO 통합 운영으로 월 상담 300% 증가','트래픽 350%↑','상담신청 3배'],
          ['피부과','분당 피부과 의원','GEO 최적화 후 ChatGPT 인용 달성, AI 트래픽 유입 시작','AI인용 15건/월','신규환자 2.1배'],
          ['치과','홍대 치과','SEO 6개월 운영 후 "홍대 치과 추천" 1위 달성','검색순위 1위','클릭률 280%↑'],
        ];
        foreach ($dummy as $d): ?>
      <div class="case-card">
        <div class="case-body">
          <span class="case-tag"><?php echo $d[0]; ?></span>
          <h3><?php echo $d[1]; ?></h3>
          <p style="font-size:.875rem;color:#6B7280"><?php echo $d[2]; ?></p>
          <div class="case-metrics">
            <div><div class="case-metric-num"><?php echo $d[3]; ?></div><div class="case-metric-label">성과 지표 1</div></div>
            <div><div class="case-metric-num"><?php echo $d[4]; ?></div><div class="case-metric-label">성과 지표 2</div></div>
          </div>
        </div>
      </div>
        <?php endforeach;
      endif; ?>
    </div>
    <div style="text-align:center;margin-top:32px">
      <a href="<?php echo esc_url(home_url('/cases/')); ?>" class="btn btn-primary">전체 사례 보기 →</a>
    </div>
  </div>
</section>

<!-- ===== WIKI PREVIEW ===== -->
<?php
$wiki_query = new WP_Query(['post_type'=>'wiki','posts_per_page'=>3,'post_status'=>'publish']);
if ($wiki_query->have_posts()):
?>
<section class="section">
  <div class="container">
    <div class="section-header fade-up">
      <span class="section-badge badge-navy">WIKI</span>
      <h2>병원마케팅 위키</h2>
      <p>AI 검색·SEO·병원마케팅 전문 지식 허브</p>
    </div>
    <div class="post-grid fade-up">
      <?php while ($wiki_query->have_posts()): $wiki_query->the_post(); ?>
      <a href="<?php the_permalink(); ?>" class="post-card">
        <?php if (has_post_thumbnail()): ?>
        <div class="post-thumb"><?php the_post_thumbnail('mm-thumb'); ?></div>
        <?php endif; ?>
        <div class="post-body">
          <span class="post-cat">위키</span>
          <div class="post-title"><?php the_title(); ?></div>
          <div class="post-excerpt"><?php echo wp_trim_words(get_the_excerpt(), 20); ?></div>
          <div class="post-meta"><?php echo get_the_date(); ?></div>
        </div>
      </a>
      <?php endwhile; wp_reset_postdata(); ?>
    </div>
    <div style="text-align:center;margin-top:32px">
      <a href="<?php echo esc_url(home_url('/wiki/')); ?>" class="btn btn-primary">전체 위키 보기 →</a>
    </div>
  </div>
</section>
<?php endif; ?>

<!-- ===== CTA + CONTACT FORM ===== -->
<section class="section section-dark" id="contact">
  <div class="container">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:start">
      <!-- 왼쪽 -->
      <div class="fade-up">
        <span class="section-badge badge-blue">무료 상담 신청</span>
        <h2 style="color:#fff;margin-bottom:20px">지금 바로 시작하세요<br><span class="text-gradient">무료 진단은 24시간</span><br>안에 연락드립니다</h2>
        <ul style="list-style:none;margin-top:32px">
          <?php
          $benefits = [
            ['✅','무료 마케팅 현황 진단','현재 병원 온라인 마케팅 상태 분석 리포트 제공'],
            ['✅','경쟁 병원 분석 포함','지역 내 경쟁 병원 키워드·SEO 현황 비교'],
            ['✅','맞춤 전략 제안서 제공','병원 상황에 맞는 마케팅 로드맵 무료 제안'],
          ];
          foreach ($benefits as $b): ?>
          <li style="display:flex;gap:16px;align-items:flex-start;margin-bottom:24px">
            <span style="width:44px;height:44px;background:rgba(37,99,235,.2);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0"><?php echo $b[0]; ?></span>
            <div>
              <div style="color:#fff;font-weight:700;margin-bottom:4px"><?php echo $b[1]; ?></div>
              <div style="color:rgba(255,255,255,.6);font-size:.875rem"><?php echo $b[2]; ?></div>
            </div>
          </li>
          <?php endforeach; ?>
        </ul>
      </div>

      <!-- 오른쪽 폼 -->
      <div class="fade-up stagger-2">
        <div class="contact-form-wrap">
          <h3>무료 상담 신청서</h3>
          <form id="contact-form">
            <div class="form-row">
              <div class="form-group">
                <label>병원명 <span class="req">*</span></label>
                <input type="text" name="hospital_name" placeholder="○○의원" required>
              </div>
              <div class="form-group">
                <label>담당자명 <span class="req">*</span></label>
                <input type="text" name="person_name" placeholder="홍길동" required>
              </div>
            </div>
            <div class="form-group">
              <label>연락처 <span class="req">*</span></label>
              <input type="tel" name="contact" placeholder="010-0000-0000" required>
            </div>
            <div class="form-group">
              <label>관심 서비스 <span class="req">*</span></label>
              <div class="service-checks">
                <?php
                $svcs = ['GEO 서비스','SEO 서비스','AEO 서비스','홈페이지 제작','병원마케팅 광고','SNS·블로그 운영'];
                foreach ($svcs as $sv): ?>
                <label class="service-check-label">
                  <input type="checkbox" name="services[]" value="<?php echo esc_attr($sv); ?>">
                  <?php echo esc_html($sv); ?>
                </label>
                <?php endforeach; ?>
              </div>
            </div>
            <div class="form-group">
              <label>문의 내용</label>
              <textarea name="message" rows="3" placeholder="현재 상황이나 궁금한 점을 간단히 적어주세요"></textarea>
            </div>
            <label class="privacy-check">
              <input type="checkbox" required>
              개인정보 수집·이용에 동의합니다. 수집된 정보는 상담 목적으로만 활용됩니다.
              <a href="<?php echo esc_url(home_url('/privacy/')); ?>">개인정보처리방침</a>
            </label>
            <button type="submit" class="form-submit">무료 상담 신청하기 →</button>
          </form>
          <div id="form-success" style="display:none;text-align:center;padding:40px 0">
            <div style="font-size:3rem;margin-bottom:16px">🎉</div>
            <h3>신청 완료!</h3>
            <p style="color:#6B7280">24시간 안에 담당자가 연락드립니다.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<?php get_footer(); ?>
