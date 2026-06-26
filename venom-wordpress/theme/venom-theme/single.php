<?php
/**
 * 블로그 단일 포스트 — 3단 레이아웃
 */
get_header(); ?>

<!-- Post Hero -->
<section class="gradient-mesh" style="padding:48px 0 36px;">
  <div class="container">
    <?php venom_breadcrumb(); ?>
    <?php while (have_posts()): the_post(); ?>
      <div style="margin-top:16px;">
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">
          <?php
          $cats = get_the_category();
          foreach ($cats as $cat): ?>
            <a href="<?php echo get_category_link($cat->term_id); ?>" class="pill-tag"><?php echo esc_html($cat->name); ?></a>
          <?php endforeach; ?>
        </div>
        <h1 class="display-xl"><?php the_title(); ?></h1>
        <div style="display:flex;gap:16px;margin-top:16px;font-size:13px;color:var(--color-ink-mute);">
          <span><?php echo get_the_date('Y년 m월 d일'); ?></span>
          <span>|</span>
          <span>읽는 시간 <?php echo ceil(str_word_count(strip_tags(get_the_content())) / 200); ?>분</span>
        </div>
      </div>
    <?php endwhile; wp_reset_query(); ?>
  </div>
</section>

<!-- 3-Column Layout -->
<div class="inner-layout">

  <!-- LEFT: Sitemap -->
  <?php get_template_part('template-parts/sitemap-sidebar'); ?>

  <!-- CENTER: Post Content -->
  <main class="page-content" id="main-content" role="main">
    <?php while (have_posts()): the_post(); ?>

      <!-- Thumbnail -->
      <?php if (has_post_thumbnail()): ?>
        <div style="margin-bottom:32px;border-radius:var(--radius-lg);overflow:hidden;">
          <?php the_post_thumbnail('venom-wide', ['style' => 'width:100%;height:auto;']); ?>
        </div>
      <?php endif; ?>

      <!-- Speakable lead (AEO) -->
      <?php $excerpt = get_the_excerpt();
      if ($excerpt): ?>
        <p class="speakable" style="font-size:17px;color:var(--color-ink-secondary);line-height:1.7;padding:20px 24px;background:var(--color-canvas-soft);border-left:3px solid var(--color-primary);border-radius:0 var(--radius-md) var(--radius-md) 0;margin-bottom:32px;">
          <?php echo esc_html($excerpt); ?>
        </p>
      <?php endif; ?>

      <!-- Content -->
      <?php the_content(); ?>

      <!-- FAQ (AEO) -->
      <?php
      $faqs = get_post_meta(get_the_ID(), '_venom_faqs', true);
      if (is_array($faqs) && count($faqs)): ?>
        <section id="faq" style="margin-top:48px;">
          <h2>자주 묻는 질문</h2>
          <div style="margin-top:20px;display:flex;flex-direction:column;gap:12px;">
            <?php foreach ($faqs as $faq): ?>
              <details style="border:1px solid var(--color-hairline);border-radius:var(--radius-lg);padding:16px 20px;">
                <summary style="font-size:15px;font-weight:400;color:var(--color-ink);cursor:pointer;">
                  <?php echo esc_html($faq['question']); ?>
                </summary>
                <div style="margin-top:12px;color:var(--color-ink-secondary);line-height:1.7;font-size:14px;">
                  <?php echo wp_kses_post($faq['answer']); ?>
                </div>
              </details>
            <?php endforeach; ?>
          </div>
        </section>
      <?php endif; ?>

      <!-- Post Footer Meta -->
      <div style="margin-top:48px;padding-top:24px;border-top:1px solid var(--color-hairline);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
        <div style="font-size:13px;color:var(--color-ink-mute);">
          최종 수정: <?php echo get_the_modified_date('Y년 m월 d일'); ?>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <?php $tags = get_the_tags(); if ($tags): foreach ($tags as $tag): ?>
            <a href="<?php echo get_tag_link($tag->term_id); ?>" class="pill-tag">#<?php echo esc_html($tag->name); ?></a>
          <?php endforeach; endif; ?>
        </div>
      </div>

      <!-- CTA -->
      <div style="margin-top:40px;background:var(--color-brand-dark);border-radius:var(--radius-lg);padding:32px;text-align:center;">
        <h3 style="color:#fff;margin-bottom:12px;">병원 마케팅 전략이 필요하신가요?</h3>
        <p style="color:rgba(255,255,255,0.7);margin-bottom:20px;font-size:14px;">베놈의 전문 마케터가 1:1 무료 상담을 제공합니다.</p>
        <a href="<?php echo home_url('/contact'); ?>" class="btn btn-primary">무료 상담 신청하기</a>
      </div>

    <?php endwhile; ?>
  </main>

  <!-- RIGHT: TOC -->
  <aside class="sidebar-right" aria-label="목차">
    <nav class="toc-nav">
      <div class="toc-title">목차</div>
      <ul class="toc-list" id="tocList" role="list"></ul>
      <?php
      $entities = get_post_meta(get_the_ID(), '_venom_geo_entities', true);
      if ($entities): ?>
        <div style="margin-top:24px;padding-top:16px;border-top:1px solid var(--color-hairline);">
          <div class="toc-title">관련 키워드</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">
            <?php foreach (explode(',', $entities) as $e): ?>
              <span class="pill-tag" style="font-size:10px;"><?php echo esc_html(trim($e)); ?></span>
            <?php endforeach; ?>
          </div>
        </div>
      <?php endif; ?>
    </nav>
  </aside>

</div>

<?php get_footer(); ?>
