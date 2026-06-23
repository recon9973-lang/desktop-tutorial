<?php
/**
 * Single Specialty Template — 진료과별 마케팅 페이지
 */
get_header();

while ( have_posts() ) : the_post();
  $post_id = get_the_ID();
  $faqs    = get_post_meta( $post_id, '_mm_faqs', true );
  $types   = get_the_terms( $post_id, 'specialty_type' );
?>

<!-- Sub GNB — specialty sections -->
<nav class="sub-gnb" aria-label="진료과 카테고리">
  <div class="container">
    <a href="<?php echo esc_url( home_url('/specialty/') ); ?>">전체</a>
    <a href="<?php echo esc_url( home_url('/specialty/plastic-surgery/') ); ?>">성형외과</a>
    <a href="<?php echo esc_url( home_url('/specialty/dermatology/') ); ?>">피부과</a>
    <a href="<?php echo esc_url( home_url('/specialty/dental/') ); ?>">치과</a>
    <a href="<?php echo esc_url( home_url('/specialty/orthopedic/') ); ?>">정형외과</a>
    <a href="<?php echo esc_url( home_url('/specialty/oriental/') ); ?>">한의원</a>
    <a href="<?php echo esc_url( home_url('/specialty/obesity/') ); ?>">비만클리닉</a>
  </div>
</nav>

<?php mm_breadcrumb(); ?>

<!-- Hero -->
<section style="background:linear-gradient(135deg,var(--navy) 0%,#1e3a5f 100%);padding:80px 0 60px;color:#fff">
  <div class="container" style="max-width:800px">
    <?php if($types): ?>
      <span class="section-badge" style="background:rgba(255,255,255,.15);color:#fff;border-color:rgba(255,255,255,.3)"><?php echo esc_html($types[0]->name); ?></span>
    <?php endif; ?>
    <h1 style="font-size:2.5rem;font-weight:800;margin:16px 0 20px;line-height:1.2"><?php the_title(); ?></h1>
    <p style="font-size:1.125rem;opacity:.85;line-height:1.7;margin-bottom:32px"><?php echo wp_trim_words(get_the_excerpt(),30); ?></p>
    <a href="<?php echo esc_url(home_url('/contact/')); ?>" class="btn btn-primary">무료 마케팅 진단 신청 →</a>
  </div>
</section>

<div class="container content-layout" style="padding-top:60px;padding-bottom:80px">

  <!-- SIDEBAR -->
  <aside class="content-sidebar">
    <div class="toc-box">
      <div class="toc-title">이 페이지 목차</div>
      <ul class="toc-list" id="toc-list"></ul>
    </div>
    <div class="toc-box" style="margin-top:24px;background:linear-gradient(135deg,var(--primary),var(--primary-dark));color:#fff;border:none">
      <div style="font-weight:700;margin-bottom:12px">무료 마케팅 진단</div>
      <p style="font-size:.875rem;opacity:.9;margin-bottom:16px">우리 병원에 맞는 마케팅 전략을 무료로 확인하세요.</p>
      <a href="<?php echo esc_url(home_url('/contact/')); ?>" style="display:block;background:#fff;color:var(--primary);text-align:center;padding:10px;border-radius:8px;font-weight:700;text-decoration:none;font-size:.875rem">무료 진단 신청 →</a>
    </div>
  </aside>

  <!-- MAIN -->
  <main class="content-main" id="content-main">

    <!-- 기존 대비 비교 블록 (next-t 패턴) -->
    <div class="section-badge" style="margin-bottom:16px">CORE PROBLEM</div>
    <h2 style="font-size:1.5rem;font-weight:700;color:var(--navy);margin-bottom:24px">기존 마케팅의 문제점</h2>
    <div class="comparison-block" style="margin-bottom:56px">
      <div class="comparison-col bad">
        <div class="comparison-col-title">❌ 기존 방식</div>
        <ul>
          <li>광고비에만 의존하는 단기 전략</li>
          <li>클릭 수 높아도 실제 예약 전환 낮음</li>
          <li>AI 검색에서 병원 정보 누락</li>
          <li>경쟁사 대비 차별화 포인트 부재</li>
          <li>콘텐츠 없이 키워드만 반복</li>
        </ul>
      </div>
      <div class="comparison-col good">
        <div class="comparison-col-title">✅ 메디마케팅 방식</div>
        <ul>
          <li>SEO·AEO·GEO 통합 전략으로 지속 성장</li>
          <li>검색 → 예약까지 전환 퍼널 최적화</li>
          <li>ChatGPT·Perplexity에 병원 정보 노출</li>
          <li>진료과 특화 콘텐츠로 전문성 확보</li>
          <li>환자 신뢰를 높이는 E-E-A-T 콘텐츠</li>
        </ul>
      </div>
    </div>

    <!-- 본문 -->
    <div class="wiki-content entry-content">
      <?php the_content(); ?>
    </div>

    <!-- FAQ -->
    <?php if ( $faqs && is_array($faqs) ) : ?>
    <section style="margin-top:60px">
      <div class="section-badge" style="margin-bottom:16px">FAQ</div>
      <h2 style="font-size:1.5rem;font-weight:700;color:var(--navy);margin-bottom:32px">자주 묻는 질문</h2>
      <?php echo mm_render_faqs($faqs); ?>
    </section>
    <?php endif; ?>

    <!-- CTA 배너 -->
    <div style="margin-top:60px;background:linear-gradient(135deg,var(--navy),#1e3a5f);border-radius:20px;padding:48px;text-align:center;color:#fff">
      <h3 style="font-size:1.5rem;font-weight:800;margin-bottom:12px">지금 바로 무료 마케팅 진단을 받아보세요</h3>
      <p style="opacity:.85;margin-bottom:28px">우리 병원 현황 분석부터 맞춤 전략까지 — 무료로 제공합니다.</p>
      <a href="<?php echo esc_url(home_url('/contact/')); ?>" class="btn btn-primary" style="background:#fff;color:var(--navy)">무료 진단 신청 →</a>
    </div>

    <!-- 관련 위키 -->
    <?php
    $wiki_posts = get_posts(['post_type'=>'wiki','posts_per_page'=>3]);
    if($wiki_posts):
    ?>
    <section style="margin-top:60px">
      <h3 style="font-size:1.125rem;font-weight:700;color:var(--navy);margin-bottom:20px">관련 마케팅 가이드</h3>
      <div class="related-grid">
        <?php foreach($wiki_posts as $wp): ?>
        <a href="<?php echo esc_url(get_permalink($wp->ID)); ?>" class="related-card">
          <div class="related-card-img" style="background:var(--gray-100);height:120px;display:flex;align-items:center;justify-content:center;font-size:2rem">📄</div>
          <div class="related-card-body">
            <span class="related-card-cat">위키</span>
            <div class="related-card-title"><?php echo esc_html($wp->post_title); ?></div>
          </div>
        </a>
        <?php endforeach; ?>
      </div>
    </section>
    <?php endif; ?>

  </main>
</div>

<?php endwhile;
get_footer();
