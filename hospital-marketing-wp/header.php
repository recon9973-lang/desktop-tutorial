<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo('charset'); ?>">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<!-- ===== HEADER ===== -->
<header class="site-header" id="site-header" role="banner">
  <div class="container header-inner">

    <!-- 로고 -->
    <a href="<?php echo esc_url( home_url('/') ); ?>" class="site-logo" aria-label="<?php bloginfo('name'); ?> 홈">
      메디<span>마케팅</span>
    </a>

    <!-- GNB (데스크탑) -->
    <nav class="gnb" role="navigation" aria-label="메인 메뉴">
      <ul>
        <!-- 서비스 -->
        <li>
          <a href="<?php echo esc_url( home_url('/services/') ); ?>">
            서비스
            <svg class="chevron" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
          </a>
          <div class="dropdown">
            <div class="dropdown-grid">
              <span class="dropdown-col-header">SEO · AEO · GEO</span>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/services/geo/') ); ?>"><span class="dot"></span>GEO 서비스</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/services/geo/process/') ); ?>"><span class="dot"></span>GEO 프로세스</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/services/aeo/') ); ?>"><span class="dot"></span>AEO 서비스</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/services/seo/') ); ?>"><span class="dot"></span>SEO 서비스</a>
              <span class="dropdown-col-header">병원마케팅</span>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/services/hospital-marketing/') ); ?>"><span class="dot"></span>병원마케팅 광고</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/services/website/') ); ?>"><span class="dot"></span>홈페이지 제작</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/services/sns/') ); ?>"><span class="dot"></span>SNS 관리</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/services/blog/') ); ?>"><span class="dot"></span>블로그 운영</a>
            </div>
          </div>
        </li>

        <!-- 병과별 -->
        <li>
          <a href="<?php echo esc_url( home_url('/specialty/') ); ?>">
            병과별
            <svg class="chevron" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
          </a>
          <div class="dropdown">
            <div class="dropdown-grid">
              <span class="dropdown-col-header">진료과별 마케팅</span>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/specialty/plastic-surgery/') ); ?>"><span class="dot"></span>성형외과</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/specialty/dermatology/') ); ?>"><span class="dot"></span>피부과</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/specialty/dental/') ); ?>"><span class="dot"></span>치과</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/specialty/orthopedic/') ); ?>"><span class="dot"></span>정형외과</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/specialty/oriental/') ); ?>"><span class="dot"></span>한의원</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/specialty/obesity/') ); ?>"><span class="dot"></span>비만클리닉</a>
            </div>
          </div>
        </li>

        <!-- 위키 -->
        <li>
          <a href="<?php echo esc_url( home_url('/wiki/') ); ?>">
            위키
            <svg class="chevron" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
          </a>
          <div class="dropdown">
            <div class="dropdown-grid">
              <span class="dropdown-col-header">인기 위키</span>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/wiki/geo/') ); ?>"><span class="dot"></span>GEO란?</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/wiki/hospital-seo/') ); ?>"><span class="dot"></span>병원 SEO 완벽가이드</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/wiki/aeo/') ); ?>"><span class="dot"></span>AEO란?</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/wiki/naver-marketing/') ); ?>"><span class="dot"></span>네이버 병원마케팅</a>
              <span class="dropdown-col-header">최신 위키</span>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/wiki/llms-txt/') ); ?>"><span class="dot"></span>llms.txt 가이드</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/wiki/chatgpt-citation/') ); ?>"><span class="dot"></span>ChatGPT 인용 최적화</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/wiki/') ); ?>" style="font-weight:700;color:#2563EB"><span class="dot"></span>전체 위키 보기 →</a>
            </div>
          </div>
        </li>

        <!-- 사례 -->
        <li>
          <a href="<?php echo esc_url( home_url('/cases/') ); ?>">성과사례</a>
        </li>

        <!-- 도구 -->
        <li>
          <a href="<?php echo esc_url( home_url('/tools/') ); ?>">
            무료 도구
            <svg class="chevron" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
          </a>
          <div class="dropdown">
            <div class="dropdown-grid">
              <span class="dropdown-col-header">무료 진단 도구</span>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/tools/seo-check/') ); ?>"><span class="dot"></span>SEO 점수 체크</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/tools/geo-check/') ); ?>"><span class="dot"></span>GEO 엔티티 체크</a>
              <a class="dropdown-link" href="<?php echo esc_url( home_url('/tools/keyword-research/') ); ?>"><span class="dot"></span>키워드 분석</a>
            </div>
          </div>
        </li>
      </ul>
    </nav>

    <!-- CTA + 모바일 버튼 -->
    <div class="header-cta">
      <a href="<?php echo esc_url( home_url('/contact/') ); ?>" class="btn btn-primary">
        무료 상담 신청
      </a>
      <button class="mobile-toggle" id="mobile-toggle" aria-label="메뉴 열기" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>

<!-- 모바일 메뉴 -->
<nav class="mobile-nav" id="mobile-nav" aria-hidden="true">
  <ul>
    <?php
    $mobile_items = [
      '서비스' => [
        'GEO 서비스' => '/services/geo/', 'GEO 프로세스' => '/services/geo/process/',
        'AEO 서비스' => '/services/aeo/', 'SEO 서비스'  => '/services/seo/',
        '병원마케팅 광고' => '/services/hospital-marketing/', '홈페이지 제작' => '/services/website/',
      ],
      '병과별' => [
        '성형외과' => '/specialty/plastic-surgery/', '피부과' => '/specialty/dermatology/',
        '치과' => '/specialty/dental/', '정형외과' => '/specialty/orthopedic/',
        '한의원' => '/specialty/oriental/', '비만클리닉' => '/specialty/obesity/',
      ],
      '위키' => [
        'GEO란?' => '/wiki/geo/', '병원 SEO 완벽가이드' => '/wiki/hospital-seo/',
        'AEO란?' => '/wiki/aeo/', 'llms.txt 가이드' => '/wiki/llms-txt/',
        '전체 위키' => '/wiki/',
      ],
      '성과사례' => [],
      '무료 도구' => [
        'SEO 점수 체크' => '/tools/seo-check/',
        'GEO 엔티티 체크' => '/tools/geo-check/',
      ],
    ];
    foreach ( $mobile_items as $label => $sub ) :
      $has_sub = ! empty($sub);
    ?>
    <li class="mobile-nav-item">
      <?php if ( $has_sub ) : ?>
        <a href="#" class="mobile-sub-toggle">
          <?php echo esc_html($label); ?>
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </a>
        <ul class="mobile-sub">
          <?php foreach ( $sub as $slabel => $shref ) : ?>
          <li><a href="<?php echo esc_url(home_url($shref)); ?>"><?php echo esc_html($slabel); ?></a></li>
          <?php endforeach; ?>
        </ul>
      <?php else : ?>
        <a href="<?php echo esc_url(home_url('/'.strtolower($label).'/')); ?>"><?php echo esc_html($label); ?></a>
      <?php endif; ?>
    </li>
    <?php endforeach; ?>
    <li style="padding:16px 24px">
      <a href="<?php echo esc_url(home_url('/contact/')); ?>" class="btn btn-primary" style="width:100%;justify-content:center">무료 상담 신청</a>
    </li>
  </ul>
</nav>

<div id="page-content">
