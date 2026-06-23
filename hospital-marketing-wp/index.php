<?php
/**
 * Main Index Template - WordPress fallback
 */
get_header(); ?>

<div class="container" style="padding:80px 24px;min-height:60vh">
  <h1><?php wp_title(''); ?></h1>
  <?php if ( have_posts() ) : while ( have_posts() ) : the_post(); ?>
    <article>
      <h2><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h2>
      <div><?php the_excerpt(); ?></div>
    </article>
  <?php endwhile; else : ?>
    <p>콘텐츠가 없습니다.</p>
  <?php endif; ?>
</div>

<?php get_footer();
