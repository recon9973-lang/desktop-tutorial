<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
  <meta charset="<?php bloginfo('charset'); ?>">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<!-- Mobile Menu Overlay -->
<div class="mobile-menu-overlay" id="mobileOverlay" aria-hidden="true"></div>
<nav class="mobile-menu" id="mobileMenu" aria-label="모바일 메뉴">
  <button class="mobile-menu-close" id="mobileMenuClose" aria-label="메뉴 닫기">✕</button>
  <div class="mobile-nav">
    <a href="<?php echo home_url('/hospital-marketing'); ?>">병원마케팅</a>
    <a href="<?php echo home_url('/ai-marketing'); ?>">AI마케팅</a>
    <a href="<?php echo home_url('/hospital-website'); ?>">병원홈페이지 제작</a>
    <a href="<?php echo home_url('/online-marketing'); ?>">온라인마케팅</a>
    <a href="<?php echo home_url('/blog'); ?>">블로그</a>
    <a href="<?php echo home_url('/contact'); ?>" style="color:var(--color-primary);font-weight:500;">문의하기</a>
  </div>
</nav>

<!-- Site Header -->
<header class="site-header" id="siteHeader">
  <div class="container">

    <!-- Logo -->
    <a href="<?php echo home_url('/'); ?>" class="site-logo" aria-label="베놈 홈">
      <?php
      if (has_custom_logo()) {
          the_custom_logo();
      } else { ?>
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect width="28" height="28" rx="6" fill="#533afd"/>
          <path d="M6 8l8 12 8-12" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>병원마케팅 <strong>베놈</strong></span>
      <?php } ?>
    </a>

    <!-- Main Navigation -->
    <nav class="main-nav" id="mainNav" aria-label="주 내비게이션">
      <ul>
        <li>
          <a href="<?php echo home_url('/hospital-marketing'); ?>" <?php echo (is_page('hospital-marketing') || get_post_type() === 'venom_service') ? 'class="active"' : ''; ?>>
            병원마케팅
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
          </a>
          <div class="dropdown" role="menu">
            <div class="sub-group">
              <div class="sub-group-label">진료과별 마케팅</div>
              <?php
              $hospital_types = [
                'medical-ad-review'  => '의료광고심의',
                'dental-marketing'   => '치과마케팅',
                'skin-marketing'     => '피부과마케팅',
                'ortho-marketing'    => '정형외과마케팅',
                'hani-marketing'     => '한의원마케팅',
                'plastic-marketing'  => '성형외과마케팅',
                'internal-marketing' => '내과마케팅',
                'eye-marketing'      => '안과마케팅',
                'device-marketing'   => '의료기기마케팅',
              ];
              foreach ($hospital_types as $slug => $label): ?>
                <a href="<?php echo home_url('/hospital-marketing/' . $slug); ?>" role="menuitem"><?php echo esc_html($label); ?></a>
              <?php endforeach; ?>
            </div>
          </div>
        </li>

        <li>
          <a href="<?php echo home_url('/ai-marketing'); ?>">
            AI마케팅
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
          </a>
          <div class="dropdown" role="menu">
            <div class="sub-group">
              <div class="sub-group-label">AI 마케팅 서비스</div>
              <a href="<?php echo home_url('/ai-marketing/geo'); ?>" role="menuitem">GEO — 생성AI 최적화</a>
              <a href="<?php echo home_url('/ai-marketing/aeo'); ?>" role="menuitem">AEO — 답변엔진 최적화</a>
              <a href="<?php echo home_url('/ai-marketing/seo'); ?>" role="menuitem">SEO — 검색엔진 최적화</a>
            </div>
          </div>
        </li>

        <li>
          <a href="<?php echo home_url('/hospital-website'); ?>">
            병원홈페이지 제작
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
          </a>
          <div class="dropdown" role="menu">
            <a href="<?php echo home_url('/hospital-website/basic'); ?>" role="menuitem">기본형 (서브 5페이지)</a>
            <a href="<?php echo home_url('/hospital-website/standard'); ?>" role="menuitem">중급형 (서브 10페이지)</a>
            <a href="<?php echo home_url('/hospital-website/premium'); ?>" role="menuitem">고급형 (10페이지 이상)</a>
          </div>
        </li>

        <li>
          <a href="<?php echo home_url('/online-marketing'); ?>">
            온라인마케팅
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
          </a>
          <div class="dropdown" role="menu">
            <div class="sub-group">
              <div class="sub-group-label">검색광고</div>
              <a href="<?php echo home_url('/online-marketing/power-link'); ?>" role="menuitem">파워링크</a>
              <a href="<?php echo home_url('/online-marketing/brand-search'); ?>" role="menuitem">브랜드검색광고</a>
              <a href="<?php echo home_url('/online-marketing/place-ad'); ?>" role="menuitem">플레이스검색광고</a>
            </div>
            <div class="sub-group">
              <div class="sub-group-label">SNS & 앱</div>
              <a href="<?php echo home_url('/online-marketing/instagram'); ?>" role="menuitem">인스타그램</a>
              <a href="<?php echo home_url('/online-marketing/facebook'); ?>" role="menuitem">페이스북</a>
              <a href="<?php echo home_url('/online-marketing/daangn'); ?>" role="menuitem">당근마켓</a>
            </div>
            <div class="sub-group">
              <div class="sub-group-label">브랜드</div>
              <a href="<?php echo home_url('/online-marketing/press'); ?>" role="menuitem">언론 보도</a>
              <a href="<?php echo home_url('/online-marketing/brand'); ?>" role="menuitem">브랜드마케팅</a>
            </div>
          </div>
        </li>

        <li>
          <a href="<?php echo home_url('/blog'); ?>" <?php echo is_home() || is_singular('post') ? 'class="active"' : ''; ?>>블로그</a>
        </li>
      </ul>
    </nav>

    <!-- Header Actions -->
    <div class="header-actions">
      <a href="tel:16614142" class="btn btn-secondary btn-sm">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.01 1.18 2 2 0 012 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.18 6.18l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/>
        </svg>
        1661-4142
      </a>
      <a href="<?php echo home_url('/contact'); ?>" class="btn btn-primary btn-sm">무료 상담 신청</a>
    </div>

    <!-- Hamburger -->
    <button class="hamburger" id="hamburgerBtn" aria-label="메뉴 열기" aria-expanded="false" aria-controls="mobileMenu">
      <span></span><span></span><span></span>
    </button>

  </div>
</header>
