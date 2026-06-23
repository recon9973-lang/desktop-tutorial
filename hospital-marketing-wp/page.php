<?php
/**
 * Default Page Template
 */
get_header();

while ( have_posts() ) : the_post(); ?>

<?php mm_breadcrumb(); ?>

<div class="container" style="max-width:800px;padding-top:60px;padding-bottom:80px">
  <h1 style="font-size:2rem;font-weight:800;color:var(--navy);margin-bottom:32px"><?php the_title(); ?></h1>
  <div class="entry-content wiki-content">
    <?php the_content(); ?>
  </div>
</div>

<?php endwhile;
get_footer();
