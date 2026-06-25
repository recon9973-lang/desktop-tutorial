<?php
/**
 * Venom Theme — functions.php
 * 병원마케팅 베놈 워드프레스 테마 핵심 기능
 */

defined('ABSPATH') || exit;

// SEO / GEO / AEO 전문 백엔드 모듈
require_once get_template_directory() . '/inc/seo-geo-aeo.php';

/* ============================================================
   THEME SETUP
   ============================================================ */
function venom_theme_setup(): void {
    load_theme_textdomain('venom-theme', get_template_directory() . '/languages');
    add_theme_support('title-tag');
    add_theme_support('post-thumbnails');
    add_theme_support('html5', ['search-form','comment-form','comment-list','gallery','caption','style','script']);
    add_theme_support('responsive-embeds');
    add_theme_support('custom-logo', ['height' => 64, 'width' => 200, 'flex-width' => true]);
    add_theme_support('editor-styles');
    add_theme_support('wp-block-styles');
    add_theme_support('align-wide');
    add_image_size('venom-thumb',   800, 450, true);
    add_image_size('venom-wide',   1200, 675, true);
    add_image_size('venom-square',  600, 600, true);

    register_nav_menus([
        'primary'  => '메인 내비게이션',
        'footer-1' => '푸터 — 서비스',
        'footer-2' => '푸터 — 회사정보',
        'footer-3' => '푸터 — 블로그',
        'footer-4' => '푸터 — 법적',
    ]);
}
add_action('after_setup_theme', 'venom_theme_setup');

/* ============================================================
   ENQUEUE ASSETS
   ============================================================ */
function venom_enqueue_assets(): void {
    $v = wp_get_theme()->get('Version');
    $uri = get_template_directory_uri();

    // Google Fonts — Inter
    wp_enqueue_style(
        'venom-fonts',
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap',
        [], null
    );

    // Main stylesheet
    wp_enqueue_style('venom-style', get_stylesheet_uri(), ['venom-fonts'], $v);

    // Lucide Icons
    wp_enqueue_script(
        'lucide',
        'https://unpkg.com/lucide@latest/dist/umd/lucide.min.js',
        [], '0.379.0', true
    );

    // Main JS
    wp_enqueue_script('venom-main', $uri . '/assets/js/main.js', ['lucide'], $v, true);

    // TOC JS (inner pages only)
    if (is_singular(['page','post'])) {
        wp_enqueue_script('venom-toc', $uri . '/assets/js/toc.js', [], $v, true);
    }

    // Localize for AJAX
    wp_localize_script('venom-main', 'venomData', [
        'ajaxUrl' => admin_url('admin-ajax.php'),
        'nonce'   => wp_create_nonce('venom_nonce'),
        'siteUrl' => get_site_url(),
    ]);
}
add_action('wp_enqueue_scripts', 'venom_enqueue_assets');

/* ============================================================
   REGISTER CUSTOM POST TYPES
   ============================================================ */
function venom_register_post_types(): void {
    // 병원마케팅 서비스
    register_post_type('venom_service', [
        'labels' => [
            'name'               => '서비스',
            'singular_name'      => '서비스',
            'add_new_item'       => '서비스 추가',
            'edit_item'          => '서비스 편집',
            'menu_name'          => '서비스 관리',
        ],
        'public'       => true,
        'has_archive'  => true,
        'hierarchical' => false,
        'show_in_rest' => true,
        'menu_icon'    => 'dashicons-star-filled',
        'menu_position'=> 5,
        'supports'     => ['title','editor','thumbnail','excerpt','custom-fields'],
        'rewrite'      => ['slug' => 'service'],
    ]);

    // 포트폴리오 / 성과
    register_post_type('venom_case', [
        'labels' => [
            'name'          => '성과 사례',
            'singular_name' => '성과 사례',
            'menu_name'     => '성과 사례',
        ],
        'public'       => true,
        'has_archive'  => true,
        'show_in_rest' => true,
        'menu_icon'    => 'dashicons-chart-bar',
        'menu_position'=> 6,
        'supports'     => ['title','editor','thumbnail','excerpt','custom-fields'],
        'rewrite'      => ['slug' => 'case'],
    ]);

    // 팀 멤버
    register_post_type('venom_team', [
        'labels' => [
            'name'          => '팀원',
            'singular_name' => '팀원',
            'menu_name'     => '팀 관리',
        ],
        'public'       => false,
        'show_ui'      => true,
        'show_in_rest' => true,
        'menu_icon'    => 'dashicons-groups',
        'menu_position'=> 7,
        'supports'     => ['title','thumbnail','excerpt','custom-fields'],
    ]);
}
add_action('init', 'venom_register_post_types');

/* ============================================================
   REGISTER CUSTOM TAXONOMIES
   ============================================================ */
function venom_register_taxonomies(): void {
    // 서비스 카테고리
    register_taxonomy('service_cat', ['venom_service'], [
        'labels'       => ['name' => '서비스 분류', 'singular_name' => '서비스 분류'],
        'hierarchical' => true,
        'show_in_rest' => true,
        'rewrite'      => ['slug' => 'service-cat'],
    ]);

    // 병원 유형
    register_taxonomy('hospital_type', ['post','venom_service'], [
        'labels'       => ['name' => '병원 유형', 'singular_name' => '병원 유형'],
        'hierarchical' => true,
        'show_in_rest' => true,
        'rewrite'      => ['slug' => 'hospital-type'],
    ]);

    // 지역
    register_taxonomy('region', ['post','venom_case'], [
        'labels'       => ['name' => '지역', 'singular_name' => '지역'],
        'hierarchical' => true,
        'show_in_rest' => true,
        'rewrite'      => ['slug' => 'region'],
    ]);
}
add_action('init', 'venom_register_taxonomies');

/* ============================================================
   WIDGET AREAS
   ============================================================ */
function venom_widgets_init(): void {
    register_sidebar([
        'name'          => '사이드바 (블로그)',
        'id'            => 'blog-sidebar',
        'before_widget' => '<div class="widget %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h4 class="widget-title">',
        'after_title'   => '</h4>',
    ]);
}
add_action('widgets_init', 'venom_widgets_init');

/* ============================================================
   CONTACT FORM AJAX HANDLER
   ============================================================ */
function venom_handle_contact(): void {
    check_ajax_referer('venom_nonce', 'nonce');

    $name    = sanitize_text_field($_POST['name']    ?? '');
    $hospital= sanitize_text_field($_POST['hospital'] ?? '');
    $phone   = sanitize_text_field($_POST['phone']   ?? '');
    $email   = sanitize_email($_POST['email']        ?? '');
    $service = sanitize_text_field($_POST['service'] ?? '');
    $message = sanitize_textarea_field($_POST['message'] ?? '');

    if (!$name || !$phone) {
        wp_send_json_error(['message' => '이름과 연락처는 필수 항목입니다.']);
        return;
    }

    // Save to DB
    $post_id = wp_insert_post([
        'post_type'   => 'venom_inquiry',
        'post_title'  => "[문의] {$name} — {$hospital}",
        'post_status' => 'private',
        'meta_input'  => [
            '_inquiry_name'     => $name,
            '_inquiry_hospital' => $hospital,
            '_inquiry_phone'    => $phone,
            '_inquiry_email'    => $email,
            '_inquiry_service'  => $service,
            '_inquiry_message'  => $message,
            '_inquiry_date'     => current_time('mysql'),
        ],
    ]);

    // Send email notification
    $admin_email = get_option('admin_email');
    $subject = "[베놈] 새 마케팅 상담 문의 — {$name}";
    $body  = "이름: {$name}\n";
    $body .= "병원명: {$hospital}\n";
    $body .= "연락처: {$phone}\n";
    $body .= "이메일: {$email}\n";
    $body .= "관심 서비스: {$service}\n";
    $body .= "문의 내용:\n{$message}\n";
    wp_mail($admin_email, $subject, $body);

    wp_send_json_success(['message' => '문의가 접수되었습니다. 1영업일 내 연락드리겠습니다.']);
}
add_action('wp_ajax_venom_contact',        'venom_handle_contact');
add_action('wp_ajax_nopriv_venom_contact', 'venom_handle_contact');

/* ============================================================
   SEO META TAGS
   ============================================================ */
function venom_output_meta(): void {
    if (is_singular()) {
        global $post;
        $desc = get_post_meta($post->ID, '_venom_meta_desc', true)
              ?: wp_trim_words(get_the_excerpt($post), 25, '...');
        $img  = get_the_post_thumbnail_url($post, 'venom-wide')
              ?: get_template_directory_uri() . '/assets/images/og-default.jpg';

        echo '<meta name="description" content="' . esc_attr($desc) . '">' . "\n";
        echo '<meta property="og:title" content="' . esc_attr(get_the_title()) . '">' . "\n";
        echo '<meta property="og:description" content="' . esc_attr($desc) . '">' . "\n";
        echo '<meta property="og:image" content="' . esc_url($img) . '">' . "\n";
        echo '<meta property="og:url" content="' . esc_url(get_permalink()) . '">' . "\n";
        echo '<meta property="og:type" content="article">' . "\n";
    } else {
        $desc = get_bloginfo('description');
        echo '<meta name="description" content="' . esc_attr($desc) . '">' . "\n";
    }
    echo '<meta name="robots" content="index, follow">' . "\n";
    echo '<meta name="author" content="주식회사 베놈">' . "\n";
}
add_action('wp_head', 'venom_output_meta', 5);

/* ============================================================
   SCHEMA MARKUP (JSON-LD)
   ============================================================ */
function venom_output_schema(): void {
    $schema = [
        '@context' => 'https://schema.org',
        '@type'    => 'LocalBusiness',
        'name'     => '주식회사 베놈',
        'alternateName' => '병원마케팅 베놈',
        'description'   => '병원 전문 디지털 마케팅 대행사. SEO, GEO, AEO, SNS광고, 병원홈페이지 제작 전문',
        'url'      => get_site_url(),
        'telephone'=> '1661-4142',
        'address'  => [
            '@type'           => 'PostalAddress',
            'streetAddress'   => '수성구 용학로25길 54, 4층',
            'addressLocality' => '대구광역시',
            'addressCountry'  => 'KR',
        ],
        'areaServed'    => '대한민국',
        'priceRange'    => '₩₩₩',
        'openingHours'  => 'Mo-Fr 09:00-18:00',
        'sameAs'        => ['https://www.venomad.com'],
    ];
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT) . '</script>' . "\n";
}
add_action('wp_head', 'venom_output_schema');

/* ============================================================
   BREADCRUMB HELPER
   ============================================================ */
function venom_breadcrumb(): void {
    echo '<nav class="breadcrumb" aria-label="경로">';
    echo '<a href="' . home_url('/') . '">홈</a>';
    echo '<span class="sep" aria-hidden="true">›</span>';
    if (is_singular('post')) {
        $cats = get_the_category();
        if ($cats) {
            echo '<a href="' . esc_url(get_category_link($cats[0]->term_id)) . '">' . esc_html($cats[0]->name) . '</a>';
            echo '<span class="sep" aria-hidden="true">›</span>';
        }
        echo '<span>' . esc_html(get_the_title()) . '</span>';
    } elseif (is_page()) {
        if ($post->post_parent) {
            echo '<a href="' . esc_url(get_permalink($post->post_parent)) . '">' . esc_html(get_the_title($post->post_parent)) . '</a>';
            echo '<span class="sep">›</span>';
        }
        echo '<span>' . esc_html(get_the_title()) . '</span>';
    } elseif (is_category()) {
        echo '<span>' . esc_html(single_cat_title('', false)) . '</span>';
    } else {
        wp_title(' › ');
    }
    echo '</nav>';
}

/* ============================================================
   SITEMAP XML
   ============================================================ */
function venom_sitemap_xml(): void {
    if (!isset($_GET['venom_sitemap'])) return;
    header('Content-Type: application/xml; charset=utf-8');
    $out = '<?xml version="1.0" encoding="UTF-8"?>';
    $out .= '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
    $out .= '<url><loc>' . home_url('/') . '</loc><changefreq>daily</changefreq><priority>1.0</priority></url>';
    $pages = get_posts(['post_type'=>'page','posts_per_page'=>-1,'post_status'=>'publish']);
    foreach ($pages as $p) {
        $out .= '<url><loc>' . get_permalink($p) . '</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>';
    }
    $posts = get_posts(['posts_per_page'=>-1,'post_status'=>'publish']);
    foreach ($posts as $p) {
        $out .= '<url><loc>' . get_permalink($p) . '</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>';
    }
    $out .= '</urlset>';
    echo $out;
    exit;
}
add_action('init', 'venom_sitemap_xml');

/* ============================================================
   REGISTER INQUIRY CPT
   ============================================================ */
function venom_register_inquiry_cpt(): void {
    register_post_type('venom_inquiry', [
        'labels' => ['name' => '상담 문의', 'singular_name' => '상담 문의'],
        'public'      => false,
        'show_ui'     => true,
        'show_in_rest'=> false,
        'menu_icon'   => 'dashicons-email-alt',
        'menu_position'=> 8,
        'supports'    => ['title'],
        'capabilities'=> ['create_posts' => 'do_not_allow'],
        'map_meta_cap'=> true,
    ]);
}
add_action('init', 'venom_register_inquiry_cpt');

/* ============================================================
   ADMIN COLUMNS FOR INQUIRIES
   ============================================================ */
function venom_inquiry_columns(array $cols): array {
    return [
        'cb'               => $cols['cb'],
        'title'            => '이름/병원',
        'inquiry_phone'    => '연락처',
        'inquiry_service'  => '서비스',
        'inquiry_date'     => '문의일',
    ];
}
add_filter('manage_venom_inquiry_posts_columns', 'venom_inquiry_columns');

function venom_inquiry_column_data(string $col, int $post_id): void {
    match ($col) {
        'inquiry_phone'   => print(esc_html(get_post_meta($post_id, '_inquiry_phone', true))),
        'inquiry_service' => print(esc_html(get_post_meta($post_id, '_inquiry_service', true))),
        'inquiry_date'    => print(esc_html(get_post_meta($post_id, '_inquiry_date', true))),
        default           => null,
    };
}
add_action('manage_venom_inquiry_posts_custom_column', 'venom_inquiry_column_data', 10, 2);
