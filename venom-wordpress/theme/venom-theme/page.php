<?php
/**
 * 상세 페이지 템플릿 — 3단 레이아웃
 * 왼쪽: 전체 사이트맵 | 본문 | 오른쪽: 목차(TOC)
 */
get_header(); ?>

<!-- Page Hero (Gradient Mesh) -->
<section class="gradient-mesh" style="padding:48px 0 36px;">
  <div class="container">
    <?php venom_breadcrumb(); ?>
    <h1 class="display-xl" style="margin-top:1rem;"><?php the_title(); ?></h1>
    <?php
    $subtitle = get_post_meta(get_the_ID(), '_venom_subtitle', true);
    if ($subtitle): ?>
      <p style="font-size:17px;color:var(--color-ink-mute);margin-top:0.75rem;max-width:560px;"><?php echo esc_html($subtitle); ?></p>
    <?php endif; ?>
  </div>
</section>

<!-- 3-Column Inner Layout -->
<div class="inner-layout">

  <!-- LEFT: 전체 사이트맵 -->
  <?php get_template_part('template-parts/sitemap-sidebar'); ?>

  <!-- CENTER: 본문 -->
  <main class="page-content" id="main-content" role="main">
    <?php while (have_posts()): the_post(); ?>
      <?php the_content(); ?>

      <!-- FAQ 섹션 (AEO) -->
      <?php
      $faqs = get_post_meta(get_the_ID(), '_venom_faqs', true);
      if (is_array($faqs) && count($faqs)): ?>
        <section id="faq" style="margin-top:56px;">
          <h2>자주 묻는 질문</h2>
          <div style="margin-top:24px;display:flex;flex-direction:column;gap:16px;">
            <?php foreach ($faqs as $faq): ?>
              <details style="border:1px solid var(--color-hairline);border-radius:var(--radius-lg);padding:20px;cursor:pointer;">
                <summary style="font-size:16px;font-weight:400;color:var(--color-ink);list-style:none;display:flex;justify-content:space-between;align-items:center;">
                  <?php echo esc_html($faq['question']); ?>
                  <i data-lucide="chevron-down" style="width:16px;height:16px;color:var(--color-ink-mute);flex-shrink:0;"></i>
                </summary>
                <div style="margin-top:12px;color:var(--color-ink-secondary);line-height:1.7;font-size:15px;">
                  <?php echo wp_kses_post($faq['answer']); ?>
                </div>
              </details>
            <?php endforeach; ?>
          </div>
        </section>
      <?php endif; ?>

    <?php endwhile; ?>

    <!-- 문의 CTA 인라인 -->
    <div style="margin-top:56px;background:var(--color-canvas-soft);border-radius:var(--radius-lg);padding:32px;text-align:center;">
      <h3 class="heading-md">이 서비스가 궁금하신가요?</h3>
      <p style="color:var(--color-ink-mute);margin:12px 0 24px;">베놈 전문 마케터가 1:1로 무료 상담을 제공합니다.</p>
      <a href="<?php echo home_url('/contact'); ?>" class="btn btn-primary">무료 상담 신청하기</a>
    </div>
  </main>

  <!-- RIGHT: 목차 (TOC) -->
  <aside class="sidebar-right" aria-label="페이지 목차">
    <nav class="toc-nav">
      <div class="toc-title">목차</div>
      <ul class="toc-list" id="tocList" role="list">
        <!-- JS(toc.js)가 자동 생성 -->
      </ul>
      <!-- GEO 엔티티 태그 표시 -->
      <?php
      $entities = get_post_meta(get_the_ID(), '_venom_geo_entities', true);
      if ($entities): ?>
        <div style="margin-top:24px;padding-top:16px;border-top:1px solid var(--color-hairline);">
          <div class="toc-title">관련 키워드</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">
            <?php foreach (explode(',', $entities) as $entity): ?>
              <span class="pill-tag" style="font-size:10px;"><?php echo esc_html(trim($entity)); ?></span>
            <?php endforeach; ?>
          </div>
        </div>
      <?php endif; ?>
    </nav>
  </aside>

</div><!-- /.inner-layout -->

<?php get_footer(); ?>
