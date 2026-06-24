<?php
/**
 * 메인 홈페이지 — 병원마케팅 베놈
 */
get_header(); ?>

<!-- ============================================================
     HERO — Gradient Mesh
     ============================================================ -->
<section class="gradient-mesh hero">
  <div class="container">
    <div class="hero-eyebrow">
      <span class="pill-tag">대한민국 No.1 병원 전문 마케팅</span>
    </div>
    <h1 class="display-xxl hero-title">
      병원 매출을<br>
      <strong>데이터로 증명</strong>하는<br>
      마케팅 파트너
    </h1>
    <p class="hero-desc">
      의료광고심의부터 SEO · GEO · AEO · SNS 광고까지.<br>
      베놈은 병원 전문 마케터가 직접 전략을 설계하고 실행합니다.
    </p>
    <div class="hero-cta">
      <a href="<?php echo home_url('/contact'); ?>" class="btn btn-primary btn-lg">무료 상담 신청하기</a>
      <a href="<?php echo home_url('/hospital-marketing'); ?>" class="btn btn-secondary btn-lg">서비스 알아보기</a>
    </div>

    <!-- Stats -->
    <div class="hero-stats">
      <div class="stat-item">
        <div class="stat-number">500<span style="font-size:0.6em;">+</span></div>
        <div class="stat-label">병원 마케팅 진행</div>
      </div>
      <div class="stat-item">
        <div class="stat-number">98<span style="font-size:0.6em;">%</span></div>
        <div class="stat-label">고객 재계약률</div>
      </div>
      <div class="stat-item">
        <div class="stat-number">7<span style="font-size:0.6em;">년+</span></div>
        <div class="stat-label">병원마케팅 전문</div>
      </div>
      <div class="stat-item">
        <div class="stat-number">24<span style="font-size:0.6em;">h</span></div>
        <div class="stat-label">전담 담당자 응대</div>
      </div>
    </div>
  </div>
</section>

<!-- Trust Logos -->
<div class="section" style="padding:32px 0;border-bottom:1px solid var(--color-hairline);">
  <div class="container trust-strip">
    <span class="trust-strip-label">다양한 진료과 병원과 함께합니다</span>
    <?php
    $types = ['치과','피부과','정형외과','한의원','성형외과','내과','안과','의료기기'];
    foreach ($types as $t): ?>
      <span class="trust-logo"><?php echo esc_html($t); ?></span>
    <?php endforeach; ?>
  </div>
</div>

<!-- ============================================================
     병원마케팅 서비스 (진료과별)
     ============================================================ -->
<section class="section">
  <div class="container">
    <div class="section-header">
      <span class="pill-tag">병원마케팅</span>
      <h2 class="display-lg" style="margin-top:1rem;">진료과별 맞춤 마케팅 전략</h2>
      <p>각 진료과의 특성과 환자 행동을 깊이 이해하는<br>베놈의 전문 팀이 최적의 마케팅 전략을 제안합니다.</p>
    </div>
    <div class="services-grid">
      <?php
      $services = [
        ['icon'=>'stethoscope', 'slug'=>'dental-marketing',   'title'=>'치과마케팅',     'desc'=>'임플란트·교정 특화 키워드 SEO, 네이버 플레이스 상위 노출, SNS 콘텐츠 마케팅'],
        ['icon'=>'sparkles',    'slug'=>'skin-marketing',      'title'=>'피부과마케팅',   'desc'=>'레이저·보톡스·필러 비급여 시술 중심 퍼포먼스 마케팅 및 브랜딩 전략'],
        ['icon'=>'bone',        'slug'=>'ortho-marketing',     'title'=>'정형외과마케팅', 'desc'=>'척추·관절·도수치료 키워드 SEO + 지역 검색광고로 신환 유입 최대화'],
        ['icon'=>'leaf',        'slug'=>'hani-marketing',      'title'=>'한의원마케팅',   'desc'=>'추나요법·한약·다이어트 한방 전문 콘텐츠 마케팅 + AI 검색 최적화'],
        ['icon'=>'scissors',    'slug'=>'plastic-marketing',   'title'=>'성형외과마케팅', 'desc'=>'눈·코·리프팅 시술 의료광고심의 통과 후 멀티채널 마케팅 전략 수립'],
        ['icon'=>'heart-pulse', 'slug'=>'internal-marketing',  'title'=>'내과마케팅',     'desc'=>'건강검진·다이어트·내시경 패키지 온라인 마케팅 + 지역 브랜드 강화'],
        ['icon'=>'eye',         'slug'=>'eye-marketing',       'title'=>'안과마케팅',     'desc'=>'라식·라섹·백내장 특화 키워드 SEO + 유튜브 영상 콘텐츠 마케팅'],
        ['icon'=>'cpu',         'slug'=>'device-marketing',    'title'=>'의료기기마케팅', 'desc'=>'B2B·B2C 의료기기 전문 마케팅, 병원 대상 영업 지원 콘텐츠 제작'],
        ['icon'=>'shield-check','slug'=>'medical-ad-review',   'title'=>'의료광고심의',   'desc'=>'의료광고 심의 신청 대행, 사전심의 통과율 최적화 카피라이팅 서비스'],
      ];
      foreach ($services as $s): ?>
        <a href="<?php echo home_url('/hospital-marketing/' . $s['slug']); ?>" class="service-card">
          <div class="service-card-icon">
            <i data-lucide="<?php echo esc_attr($s['icon']); ?>"></i>
          </div>
          <h3 class="heading-md"><?php echo esc_html($s['title']); ?></h3>
          <p><?php echo esc_html($s['desc']); ?></p>
          <span class="service-card-link">
            자세히 보기
            <i data-lucide="arrow-right" style="width:14px;height:14px;"></i>
          </span>
        </a>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ============================================================
     AI 마케팅 (GEO / AEO / SEO)
     ============================================================ -->
<section class="section section-soft">
  <div class="container">
    <div class="section-header">
      <span class="pill-tag">AI 마케팅</span>
      <h2 class="display-lg" style="margin-top:1rem;">AI 시대의 병원 마케팅 전략</h2>
      <p>ChatGPT·Perplexity·구글 AI Overviews 시대,<br>AI가 병원을 추천하게 만드는 GEO·AEO·SEO 전략.</p>
    </div>
    <div class="ai-cards-grid">
      <!-- GEO -->
      <div class="ai-card featured">
        <div class="ai-card-badge">GEO</div>
        <h3 class="heading-lg">생성AI 최적화</h3>
        <p>ChatGPT, Perplexity, Gemini 등 생성AI가 병원을 답변 소스로 인용하도록 최적화합니다.</p>
        <ul class="ai-card-list">
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>AI 크롤러 접근 최적화</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>엔티티 구조화 콘텐츠 설계</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>인용 가능한 전문 콘텐츠 제작</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>Schema.org 구조화 데이터</li>
        </ul>
        <a href="<?php echo home_url('/ai-marketing/geo'); ?>" class="btn btn-primary" style="margin-top:24px;">GEO 알아보기</a>
      </div>
      <!-- AEO -->
      <div class="ai-card">
        <div class="ai-card-badge">AEO</div>
        <h3 class="heading-lg">답변엔진 최적화</h3>
        <p>구글 AI Overviews, 네이버 AI 검색, 음성검색에서 병원이 직접 답변으로 노출되도록 설계합니다.</p>
        <ul class="ai-card-list">
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>Featured Snippet 최적화</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>FAQ / HowTo 구조화 콘텐츠</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>Speakable 마크업 적용</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>AI Overviews 노출 전략</li>
        </ul>
        <a href="<?php echo home_url('/ai-marketing/aeo'); ?>" class="btn btn-secondary" style="margin-top:24px;">AEO 알아보기</a>
      </div>
      <!-- SEO -->
      <div class="ai-card">
        <div class="ai-card-badge">SEO</div>
        <h3 class="heading-lg">검색엔진 최적화</h3>
        <p>네이버·구글 상위 노출을 위한 테크니컬 SEO, 콘텐츠 SEO, 링크빌딩을 통합 전략으로 운영합니다.</p>
        <ul class="ai-card-list">
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>테크니컬 SEO 감사 & 수정</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>병원 특화 키워드 콘텐츠</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>고품질 백링크 구축</li>
          <li><span class="check-icon"><i data-lucide="check" style="width:14px;height:14px;"></i></span>Core Web Vitals 최적화</li>
        </ul>
        <a href="<?php echo home_url('/ai-marketing/seo'); ?>" class="btn btn-secondary" style="margin-top:24px;">SEO 알아보기</a>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     마케팅 프로세스
     ============================================================ -->
<section class="section">
  <div class="container">
    <div class="section-header">
      <span class="pill-tag">프로세스</span>
      <h2 class="display-lg" style="margin-top:1rem;">베놈의 4단계 마케팅 프로세스</h2>
      <p>데이터 기반 분석부터 실행·성과 보고까지, 투명하게 진행합니다.</p>
    </div>
    <div class="process-steps">
      <?php
      $steps = [
        ['title'=>'현황 분석', 'desc'=>'병원 경쟁사·키워드·온라인 현황을 데이터로 분석합니다.'],
        ['title'=>'전략 수립', 'desc'=>'진료과 특성에 맞는 맞춤 마케팅 전략과 KPI를 설계합니다.'],
        ['title'=>'실행 & 최적화', 'desc'=>'광고 집행·콘텐츠 발행·SEO 작업을 병행하며 지속 개선합니다.'],
        ['title'=>'성과 보고', 'desc'=>'월간 리포트로 신환수·유입·ROI를 투명하게 공유합니다.'],
      ];
      foreach ($steps as $i => $s): ?>
        <div class="process-step">
          <div class="step-num"><?php echo $i + 1; ?></div>
          <h4><?php echo esc_html($s['title']); ?></h4>
          <p><?php echo esc_html($s['desc']); ?></p>
        </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ============================================================
     병원홈페이지 제작 요금제
     ============================================================ -->
<section class="section section-soft">
  <div class="container">
    <div class="section-header">
      <span class="pill-tag">병원홈페이지 제작</span>
      <h2 class="display-lg" style="margin-top:1rem;">SEO 최적화 병원 홈페이지</h2>
      <p>처음부터 검색엔진을 고려해 설계된 병원 홈페이지. 반응형·예약·캘린더·네이버 연동 기본 제공.</p>
    </div>
    <div class="pricing-grid">
      <?php
      $plans = [
        [
          'tier'  => '기본형',
          'price' => '협의',
          'desc'  => '서브 페이지 5개 이내. 빠른 런칭이 필요한 병원.',
          'featured' => false,
          'features'  => ['반응형 웹디자인', '서브 페이지 5개', 'SEO 기본 설정', '예약폼 연동', '네이버 지도 연동', '1개월 무상 A/S'],
        ],
        [
          'tier'  => '중급형',
          'price' => '협의',
          'desc'  => '서브 페이지 10개. SEO 강화 + 다양한 기능 포함.',
          'featured' => true,
          'features'  => ['반응형 + 적응형', '서브 페이지 10개', '테크니컬 SEO 완전 설정', '예약·캘린더 연동', '네이버 예약 연동', '진료일정 관리', '모달형 팝업', '3개월 무상 A/S'],
        ],
        [
          'tier'  => '고급형',
          'price' => '협의',
          'desc'  => '서브 페이지 10개 이상. 완전 맞춤 제작.',
          'featured' => false,
          'features'  => ['풀 커스텀 디자인', '무제한 서브 페이지', 'SEO·GEO·AEO 완전 설정', '고급 예약 시스템', 'CRM 연동', '다국어 지원', '영상 콘텐츠 섹션', '6개월 무상 A/S'],
        ],
      ];
      foreach ($plans as $p): ?>
        <div class="pricing-card <?php echo $p['featured'] ? 'featured' : ''; ?>">
          <div class="pricing-tier"><?php echo esc_html($p['tier']); ?></div>
          <div class="pricing-price"><?php echo esc_html($p['price']); ?></div>
          <p class="pricing-desc"><?php echo esc_html($p['desc']); ?></p>
          <ul class="pricing-features">
            <?php foreach ($p['features'] as $f): ?>
              <li>
                <i data-lucide="check-circle" style="width:15px;height:15px;color:<?php echo $p['featured'] ? 'var(--color-primary-soft)' : 'var(--color-primary)'; ?>;flex-shrink:0;"></i>
                <?php echo esc_html($f); ?>
              </li>
            <?php endforeach; ?>
          </ul>
          <a href="<?php echo home_url('/contact'); ?>" class="btn <?php echo $p['featured'] ? 'btn-primary' : 'btn-secondary'; ?>" style="width:100%;justify-content:center;">
            견적 문의하기
          </a>
        </div>
      <?php endforeach; ?>
    </div>
    <p class="text-center text-mute" style="margin-top:24px;font-size:13px;">
      ※ 검색엔진최적화 기본 제공 | 반응형·예약·캘린더·네이버 연동 기본 | 특화 기능은 선택 가능 (일부 별도 비용)
    </p>
  </div>
</section>

<!-- ============================================================
     고객 후기
     ============================================================ -->
<section class="section">
  <div class="container">
    <div class="section-header">
      <span class="pill-tag">고객 후기</span>
      <h2 class="display-lg" style="margin-top:1rem;">실제 병원 원장님들의 이야기</h2>
    </div>
    <div class="testimonial-grid">
      <?php
      $reviews = [
        ['name'=>'김○○ 원장', 'role'=>'서울 강남구 치과', 'text'=>'6개월 만에 네이버 블로그 방문자가 5배 증가했고 신환 수가 눈에 띄게 늘었습니다. 마케터가 치과 업계를 정말 잘 알고 있어서 믿고 맡길 수 있었어요.'],
        ['name'=>'이○○ 원장', 'role'=>'부산 해운대 피부과', 'text'=>'기존 광고 대행사와 다르게 의료광고심의 통과 전략까지 함께 고민해줍니다. 심의 불합격 0%를 유지하면서 콘텐츠 퀄리티도 높아졌어요.'],
        ['name'=>'박○○ 원장', 'role'=>'대구 수성구 정형외과', 'desc'=>'SEO로 구글 상위 노출이 된 후 병원 방문 전에 이미 저희 병원을 알고 오는 환자들이 생겼습니다. GEO 전략으로 AI 검색에서도 노출되고 있어요.'],
      ];
      $defaults = ['text' => ''];
      foreach ($reviews as $r): $r = array_merge($defaults, $r); ?>
        <div class="testimonial-card">
          <p class="testimonial-quote">"<?php echo esc_html($r['text'] ?: ($r['desc'] ?? '')); ?>"</p>
          <div class="testimonial-author">
            <div class="author-avatar"><?php echo mb_substr($r['name'], 0, 1); ?></div>
            <div>
              <div class="author-name"><?php echo esc_html($r['name']); ?></div>
              <div class="author-role"><?php echo esc_html($r['role']); ?></div>
            </div>
          </div>
        </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ============================================================
     최신 블로그
     ============================================================ -->
<section class="section section-soft">
  <div class="container">
    <div class="section-header">
      <span class="pill-tag">블로그</span>
      <h2 class="display-lg" style="margin-top:1rem;">병원마케팅 최신 인사이트</h2>
    </div>
    <div class="blog-grid">
      <?php
      $posts = get_posts(['posts_per_page' => 3, 'post_status' => 'publish']);
      if ($posts):
        foreach ($posts as $post): setup_postdata($post); ?>
          <article class="blog-card">
            <?php if (has_post_thumbnail()): ?>
              <a href="<?php the_permalink(); ?>" class="blog-card-thumb">
                <?php the_post_thumbnail('venom-thumb', ['loading' => 'lazy']); ?>
              </a>
            <?php else: ?>
              <div class="blog-card-thumb" style="height:180px;background:var(--color-canvas-soft);display:flex;align-items:center;justify-content:center;">
                <i data-lucide="file-text" style="color:var(--color-ink-mute);"></i>
              </div>
            <?php endif; ?>
            <div class="blog-card-body">
              <div class="blog-card-meta">
                <?php $cats = get_the_category(); if($cats): ?>
                  <span class="pill-tag"><?php echo esc_html($cats[0]->name); ?></span>
                <?php endif; ?>
                <span><?php echo get_the_date('Y.m.d'); ?></span>
              </div>
              <h3><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h3>
              <p><?php echo wp_trim_words(get_the_excerpt(), 18, '...'); ?></p>
            </div>
          </article>
        <?php endforeach; wp_reset_postdata();
      else: ?>
        <?php
        $sample_posts = [
          ['tag'=>'SEO', 'title'=>'2025 병원 SEO 완벽 가이드 — 네이버·구글 동시 상위 노출 전략', 'date'=>'2025.06.10'],
          ['tag'=>'GEO', 'title'=>'ChatGPT가 병원을 추천하게 만드는 GEO 전략 5가지', 'date'=>'2025.06.05'],
          ['tag'=>'AEO', 'title'=>'구글 AI Overviews에서 치과가 직접 답변으로 노출되는 방법', 'date'=>'2025.05.28'],
        ];
        foreach ($sample_posts as $sp): ?>
          <article class="blog-card">
            <div class="blog-card-thumb" style="height:180px;background:linear-gradient(135deg,var(--color-primary-subdued),var(--color-canvas-soft));display:flex;align-items:center;justify-content:center;">
              <i data-lucide="file-text" style="color:var(--color-primary);width:32px;height:32px;"></i>
            </div>
            <div class="blog-card-body">
              <div class="blog-card-meta">
                <span class="pill-tag"><?php echo esc_html($sp['tag']); ?></span>
                <span><?php echo esc_html($sp['date']); ?></span>
              </div>
              <h3><a href="<?php echo home_url('/blog'); ?>"><?php echo esc_html($sp['title']); ?></a></h3>
            </div>
          </article>
        <?php endforeach; ?>
      <?php endif; ?>
    </div>
    <div class="text-center" style="margin-top:40px;">
      <a href="<?php echo home_url('/blog'); ?>" class="btn btn-secondary">블로그 전체 보기</a>
    </div>
  </div>
</section>

<?php get_footer(); ?>
