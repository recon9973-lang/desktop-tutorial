<?php
/**
 * Archive Template — wiki, case_study, blog
 */
get_header();
$pt = get_post_type();
$obj = get_post_type_object($pt);
$label = $obj ? $obj->labels->name : '아카이브';
?>

<?php mm_breadcrumb(); ?>

<section style="background:var(--gray-50);padding:60px 0 40px">
  <div class="container" style="max-width:800px">
    <h1 style="font-size:2rem;font-weight:800;color:var(--navy);margin-bottom:12px">
      <?php
      if ( is_tax() ) echo single_term_title('', false);
      else echo $label;
      ?>
    </h1>
    <?php if( is_tax() ): ?>
      <p style="color:var(--gray-500)"><?php echo term_description(); ?></p>
    <?php endif; ?>
  </div>
</section>

<div class="container" style="padding:60px 24px 80px">
  <?php if ( $pt === 'wiki' ) : ?>
    <!-- Wiki category filter tabs -->
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:40px">
      <a href="<?php echo esc_url( get_post_type_archive_link('wiki') ); ?>"
         style="padding:8px 16px;border-radius:24px;font-size:.875rem;font-weight:600;text-decoration:none;<?php echo (!is_tax() ? 'background:var(--primary);color:#fff' : 'background:var(--gray-100);color:var(--gray-600)'); ?>">전체</a>
      <?php foreach ( get_terms(['taxonomy'=>'wiki_cat','hide_empty'=>true]) as $cat ) :
        $active = ( is_tax('wiki_cat', $cat->slug) );
      ?>
      <a href="<?php echo esc_url( get_term_link($cat) ); ?>"
         style="padding:8px 16px;border-radius:24px;font-size:.875rem;font-weight:600;text-decoration:none;<?php echo ($active ? 'background:var(--primary);color:#fff' : 'background:var(--gray-100);color:var(--gray-600)'); ?>"><?php echo esc_html($cat->name); ?></a>
      <?php endforeach; ?>
    </div>
  <?php endif; ?>

  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px">
    <?php if ( have_posts() ) : while ( have_posts() ) : the_post();
      $pcats = ($pt==='wiki') ? get_the_terms(get_the_ID(),'wiki_cat') : get_the_category();
      $cat_name = ($pcats && !is_wp_error($pcats)) ? $pcats[0]->name : $label;
    ?>
    <a href="<?php the_permalink(); ?>" style="text-decoration:none;background:#fff;border:1px solid var(--gray-100);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;transition:box-shadow .2s" onmouseover="this.style.boxShadow='0 8px 32px rgba(0,0,0,.1)'" onmouseout="this.style.boxShadow='none'">
      <?php if ( has_post_thumbnail() ) : ?>
        <div style="height:180px;overflow:hidden"><?php the_post_thumbnail('medium',['style'=>'width:100%;height:100%;object-fit:cover']); ?></div>
      <?php else: ?>
        <div style="height:120px;background:linear-gradient(135deg,var(--primary-light),#e0e7ff);display:flex;align-items:center;justify-content:center;font-size:2.5rem">📄</div>
      <?php endif; ?>
      <div style="padding:20px 24px 24px">
        <span style="font-size:.75rem;font-weight:700;color:var(--primary);letter-spacing:.05em;text-transform:uppercase"><?php echo esc_html($cat_name); ?></span>
        <h2 style="font-size:1.125rem;font-weight:700;color:var(--navy);margin:8px 0 12px;line-height:1.4"><?php the_title(); ?></h2>
        <p style="font-size:.875rem;color:var(--gray-500);line-height:1.6;margin:0"><?php echo wp_trim_words(get_the_excerpt(),20); ?></p>
      </div>
    </a>
    <?php endwhile;
    else : ?>
      <p style="color:var(--gray-500)">등록된 콘텐츠가 없습니다.</p>
    <?php endif; ?>
  </div>

  <!-- Pagination -->
  <div style="margin-top:48px;text-align:center">
    <?php
    echo paginate_links([
      'prev_text' => '← 이전',
      'next_text' => '다음 →',
      'before_page_number' => '<span>',
      'after_page_number'  => '</span>',
    ]);
    ?>
  </div>
</div>

<?php get_footer();
