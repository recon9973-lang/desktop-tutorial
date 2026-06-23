<?php
/**
 * Single Post Template (blog posts)
 */
get_header();

while ( have_posts() ) : the_post();
  $cats = get_the_category();
?>

<?php mm_breadcrumb(); ?>

<div class="container content-layout" style="padding-top:60px;padding-bottom:80px">

  <aside class="content-sidebar">
    <div class="toc-box">
      <div class="toc-title">목차</div>
      <ul class="toc-list" id="toc-list"></ul>
    </div>
  </aside>

  <main class="content-main" id="content-main">

    <?php if($cats): ?>
      <span class="section-badge"><?php echo esc_html($cats[0]->name); ?></span>
    <?php endif; ?>
    <h1 style="font-size:2rem;font-weight:800;color:var(--navy);margin:16px 0 20px;line-height:1.3"><?php the_title(); ?></h1>

    <div style="display:flex;gap:16px;font-size:.875rem;color:var(--gray-500);margin-bottom:32px;padding-bottom:20px;border-bottom:2px solid var(--gray-100)">
      <span>🗓 <?php echo get_the_date('Y년 m월 d일'); ?></span>
      <span>✍ <?php the_author(); ?></span>
    </div>

    <div class="entry-content wiki-content">
      <?php the_content(); ?>
    </div>

    <div style="margin-top:48px;padding:24px;background:var(--gray-50);border-radius:12px;display:flex;gap:16px;align-items:flex-start">
      <?php echo get_avatar(get_the_author_meta('ID'),56,'','',['style'=>'border-radius:50%;flex-shrink:0']); ?>
      <div>
        <div style="font-weight:700;color:var(--navy)"><?php the_author(); ?></div>
        <p style="font-size:.875rem;color:var(--gray-600);margin:4px 0 0"><?php the_author_meta('description'); ?></p>
      </div>
    </div>

  </main>
</div>

<?php endwhile;
get_footer();
