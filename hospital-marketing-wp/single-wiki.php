<?php
/**
 * Single Wiki Template — ezloan.io + next-t.co.kr patterns
 */
get_header();

while ( have_posts() ) : the_post();
  $post_id   = get_the_ID();
  $summary   = get_post_meta( $post_id, '_mm_wiki_summary', true );
  $read_time = get_post_meta( $post_id, '_mm_wiki_read_time', true );
  $faqs      = get_post_meta( $post_id, '_mm_faqs', true );
  $rel_ids   = get_post_meta( $post_id, '_mm_related_wiki', true );
  $cats      = get_the_terms( $post_id, 'wiki_cat' );
?>

<!-- Sub GNB -->
<nav class="sub-gnb" aria-label="위키 카테고리">
  <div class="container">
    <a href="<?php echo esc_url( home_url('/wiki/') ); ?>"  <?php echo ( is_post_type_archive('wiki') ? 'class="active"' : '' ); ?>>전체</a>
    <?php
    $all_cats = get_terms(['taxonomy'=>'wiki_cat','hide_empty'=>true]);
    foreach ( $all_cats as $cat ) :
      $active = ( $cats && in_array( $cat->term_id, wp_list_pluck($cats,'term_id') ) ) ? 'class="active"' : '';
    ?>
    <a href="<?php echo esc_url( get_term_link($cat) ); ?>" <?php echo $active; ?>><?php echo esc_html($cat->name); ?></a>
    <?php endforeach; ?>
  </div>
</nav>

<?php mm_breadcrumb(); ?>

<div class="container content-layout" style="padding-top:40px;padding-bottom:80px">

  <!-- ===== SIDEBAR ===== -->
  <aside class="content-sidebar">

    <!-- TOC -->
    <div class="toc-box" id="toc-box">
      <div class="toc-title">목차</div>
      <ul class="toc-list" id="toc-list"><!-- JS로 생성 --></ul>
    </div>

    <!-- 관련 위키 크로스링크 -->
    <?php if ( $cats ) : ?>
    <div class="toc-box" style="margin-top:24px">
      <div class="toc-title">관련 위키</div>
      <?php
      $related = get_posts([
        'post_type'      => 'wiki',
        'posts_per_page' => 6,
        'post__not_in'   => [$post_id],
        'tax_query'      => [['taxonomy'=>'wiki_cat','terms'=>wp_list_pluck($cats,'term_id')]],
      ]);
      foreach ( $related as $r ) : ?>
        <a href="<?php echo esc_url( get_permalink($r->ID) ); ?>" style="display:block;padding:6px 0;font-size:.875rem;color:var(--primary);text-decoration:none;border-bottom:1px solid var(--gray-100)"><?php echo esc_html($r->post_title); ?> →</a>
      <?php endforeach; ?>
    </div>
    <?php endif; ?>

  </aside>

  <!-- ===== MAIN CONTENT ===== -->
  <main class="content-main" id="content-main">

    <!-- 카테고리 배지 -->
    <?php if ( $cats ) : ?>
    <div style="margin-bottom:12px">
      <?php foreach($cats as $c): ?>
        <span class="section-badge"><?php echo esc_html($c->name); ?></span>
      <?php endforeach; ?>
    </div>
    <?php endif; ?>

    <h1 class="wiki-title" style="font-size:2rem;font-weight:800;color:var(--navy);margin-bottom:16px"><?php the_title(); ?></h1>

    <!-- 메타 (읽기 시간, 업데이트) -->
    <div style="display:flex;gap:16px;align-items:center;font-size:.875rem;color:var(--gray-500);margin-bottom:32px;padding-bottom:20px;border-bottom:2px solid var(--gray-100)">
      <?php if($read_time): ?><span>⏱ <?php echo esc_html($read_time); ?>분 읽기</span><?php endif; ?>
      <span>🗓 최종 업데이트: <?php echo get_the_modified_date('Y년 m월 d일'); ?></span>
      <span>✍ <?php the_author(); ?></span>
    </div>

    <!-- 빠르게 핵심만 살펴보기 (ezloan 패턴) -->
    <?php
    // Build quick-nav from h2 headings in content
    $content = get_the_content();
    preg_match_all('/<h2[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)<\/h2>/i', apply_filters('the_content',$content), $h2_matches);
    if ( ! empty($h2_matches[1]) ) :
    ?>
    <div class="quick-nav" style="margin-bottom:40px">
      <div class="quick-nav-title">빠르게 핵심만 살펴보기</div>
      <div class="quick-nav-grid">
        <?php foreach ( $h2_matches[1] as $i => $anchor ) : ?>
        <a href="#<?php echo esc_attr($anchor); ?>" class="quick-nav-link">
          <span class="quick-nav-num"><?php echo str_pad($i+1, 2, '0', STR_PAD_LEFT); ?></span>
          <?php echo wp_strip_all_tags($h2_matches[2][$i]); ?>
        </a>
        <?php endforeach; ?>
      </div>
    </div>
    <?php endif; ?>

    <!-- 핵심 요약 (Executive Summary) -->
    <?php if ( $summary ) : ?>
    <div class="executive-summary" style="margin-bottom:40px">
      <div style="font-weight:700;font-size:1rem;margin-bottom:8px;color:var(--navy)">✅ 핵심 요약</div>
      <p style="margin:0;line-height:1.7;color:var(--gray-700)"><?php echo nl2br(esc_html($summary)); ?></p>
    </div>
    <?php endif; ?>

    <!-- 본문 -->
    <div class="wiki-content entry-content">
      <?php the_content(); ?>
    </div>

    <!-- FAQ (numbered, ezloan 패턴) -->
    <?php if ( $faqs && is_array($faqs) ) : ?>
    <section style="margin-top:60px">
      <div class="section-badge" style="margin-bottom:16px">FAQ</div>
      <h2 style="font-size:1.5rem;font-weight:700;color:var(--navy);margin-bottom:32px">자주 묻는 질문</h2>
      <?php echo mm_render_faqs($faqs); ?>
    </section>
    <?php endif; ?>

    <!-- 저자 프로필 -->
    <div style="margin-top:60px;padding:28px;background:var(--gray-50);border-radius:16px;display:flex;gap:20px;align-items:flex-start">
      <?php echo get_avatar( get_the_author_meta('ID'), 64, '', '', ['style'=>'border-radius:50%;flex-shrink:0'] ); ?>
      <div>
        <div style="font-weight:700;color:var(--navy);margin-bottom:4px"><?php the_author(); ?></div>
        <div style="font-size:.875rem;color:var(--gray-500);margin-bottom:8px">메디마케팅 콘텐츠팀</div>
        <p style="font-size:.875rem;color:var(--gray-600);margin:0"><?php the_author_meta('description'); ?></p>
      </div>
    </div>

    <!-- 관련 콘텐츠 위젯 (next-t 패턴) -->
    <?php
    $rel_posts = [];
    if ( $rel_ids ) {
      $rel_posts = get_posts(['post_type'=>'wiki','post__in'=>array_filter(array_map('intval',explode(',',$rel_ids))),'posts_per_page'=>3]);
    }
    if ( empty($rel_posts) && $cats ) {
      $rel_posts = get_posts(['post_type'=>'wiki','posts_per_page'=>3,'post__not_in'=>[$post_id],'tax_query'=>[['taxonomy'=>'wiki_cat','terms'=>wp_list_pluck($cats,'term_id')]]]);
    }
    if ( $rel_posts ) : ?>
    <section style="margin-top:60px">
      <h3 style="font-size:1.125rem;font-weight:700;color:var(--navy);margin-bottom:20px">이 페이지를 본 사람이 다음에 본 글</h3>
      <div class="related-grid">
        <?php foreach ( $rel_posts as $rp ) :
          $rcat = get_the_terms($rp->ID,'wiki_cat');
          $rlabel = $rcat ? $rcat[0]->name : '위키';
        ?>
        <a href="<?php echo esc_url(get_permalink($rp->ID)); ?>" class="related-card">
          <?php if(has_post_thumbnail($rp->ID)): ?>
            <div class="related-card-img"><?php echo get_the_post_thumbnail($rp->ID,'medium'); ?></div>
          <?php else: ?>
            <div class="related-card-img" style="background:var(--gray-100);height:120px;display:flex;align-items:center;justify-content:center;font-size:2rem">📄</div>
          <?php endif; ?>
          <div class="related-card-body">
            <span class="related-card-cat"><?php echo esc_html($rlabel); ?></span>
            <div class="related-card-title"><?php echo esc_html($rp->post_title); ?></div>
          </div>
        </a>
        <?php endforeach; ?>
      </div>
    </section>
    <?php endif; ?>

    <!-- 위키 태그 크로스링크 (ezloan 패턴) -->
    <?php echo mm_render_wiki_crosslinks($post_id); ?>

  </main>
</div>

<?php endwhile;
get_footer();
