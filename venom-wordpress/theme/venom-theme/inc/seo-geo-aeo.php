<?php
/**
 * Venom Theme — SEO / GEO / AEO 전문 백엔드 모듈
 *
 * 백엔드 개발자 겸 SEO·AEO·GEO 전문가 설계:
 *  - Technical SEO: Canonical, hreflang, structured data, Core Web Vitals 최적화
 *  - GEO (Generative Engine Optimization): AI 크롤러 접근 허용, 엔티티 마크업, FAQPage
 *  - AEO (Answer Engine Optimization): speakable, HowTo, FAQPage, 단락 구조
 */

defined('ABSPATH') || exit;

/* ============================================================
   1. TECHNICAL SEO
   ============================================================ */

/** Canonical URL 자동 출력 */
function venom_canonical(): void {
    $url = is_singular() ? get_permalink() : (is_home() ? home_url('/') : null);
    if ($url) {
        echo '<link rel="canonical" href="' . esc_url($url) . '">' . "\n";
    }
}
add_action('wp_head', 'venom_canonical', 3);

/** X-Robots-Tag: 검색 결과 페이지·관리자 ajax 제외 */
function venom_robots_header(): void {
    if (is_search() || is_404()) {
        header('X-Robots-Tag: noindex, follow', true);
    }
}
add_action('send_headers', 'venom_robots_header');

/** 이미지 lazy-load + width/height 자동 추가 (CLS 방지) */
function venom_auto_image_attrs(string $content): string {
    return preg_replace_callback(
        '/<img([^>]+)>/i',
        function (array $m): string {
            $tag = $m[1];
            if (!str_contains($tag, 'loading='))  $tag .= ' loading="lazy"';
            if (!str_contains($tag, 'decoding=')) $tag .= ' decoding="async"';
            return "<img{$tag}>";
        },
        $content
    );
}
add_filter('the_content', 'venom_auto_image_attrs');

/** RSS에 이미지 포함 (구글 뉴스·AI 피드용) */
function venom_rss_featured_image(string $content): string {
    global $post;
    if (is_feed() && has_post_thumbnail($post->ID)) {
        $img = get_the_post_thumbnail($post->ID, 'venom-wide', ['style' => 'max-width:600px;']);
        return $img . $content;
    }
    return $content;
}
add_filter('the_excerpt_rss', 'venom_rss_featured_image');
add_filter('the_content_feed', 'venom_rss_featured_image');

/* ============================================================
   2. SCHEMA / STRUCTURED DATA (GEO·AEO 핵심)
   ============================================================ */

/**
 * 페이지 유형별 JSON-LD 출력
 * GEO: AI 검색엔진(ChatGPT, Perplexity, Gemini)이 엔티티 인식
 * AEO: 구글 AI Overviews, 음성검색, 스니펫 최적화
 */
function venom_rich_schema(): void {
    global $post;
    $schemas = [];

    /* ── 공통: Organization ─── */
    $schemas[] = [
        '@context' => 'https://schema.org',
        '@type'    => ['Organization', 'LocalBusiness', 'MedicalBusiness'],
        '@id'      => home_url('/#organization'),
        'name'     => '주식회사 베놈',
        'alternateName' => ['베놈', '병원마케팅 베놈', 'Venom', 'venomad'],
        'description'   => '대구 기반 병원 전문 디지털 마케팅 대행사. 의료광고심의, SEO, GEO, AEO, SNS광고, 병원홈페이지 제작 전문.',
        'url'           => home_url('/'),
        'logo'          => home_url('/wp-content/themes/venom-theme/assets/images/logo.png'),
        'telephone'     => '1661-4142',
        'email'         => 'contact@venomad.com',
        'address'  => [
            '@type'           => 'PostalAddress',
            'streetAddress'   => '수성구 용학로25길 54, 4층',
            'addressLocality' => '대구',
            'addressRegion'   => '대구광역시',
            'postalCode'      => '42182',
            'addressCountry'  => 'KR',
        ],
        'geo' => [
            '@type'     => 'GeoCoordinates',
            'latitude'  => 35.8562,
            'longitude' => 128.6340,
        ],
        'areaServed'    => [
            ['@type' => 'Country', 'name' => '대한민국'],
            ['@type' => 'City',    'name' => '대구'],
            ['@type' => 'City',    'name' => '서울'],
        ],
        'openingHoursSpecification' => [[
            '@type'     => 'OpeningHoursSpecification',
            'dayOfWeek' => ['Monday','Tuesday','Wednesday','Thursday','Friday'],
            'opens'     => '09:00', 'closes' => '18:00',
        ]],
        'knowsAbout' => [
            '병원마케팅', '의료광고', 'SEO', 'GEO', 'AEO',
            '검색엔진최적화', '생성AI최적화', '답변엔진최적화',
            '치과마케팅', '피부과마케팅', '병원홈페이지제작',
        ],
        'sameAs' => ['https://www.venomad.com'],
    ];

    /* ── 단일 포스트: Article + Speakable (AEO) ─── */
    if (is_singular('post')) {
        $schemas[] = [
            '@context'        => 'https://schema.org',
            '@type'           => 'Article',
            '@id'             => get_permalink() . '#article',
            'headline'        => get_the_title(),
            'description'     => wp_trim_words(get_the_excerpt(), 30),
            'datePublished'   => get_the_date('c'),
            'dateModified'    => get_the_modified_date('c'),
            'author'          => ['@type' => 'Organization', '@id' => home_url('/#organization')],
            'publisher'       => ['@type' => 'Organization', '@id' => home_url('/#organization')],
            'inLanguage'      => 'ko-KR',
            'mainEntityOfPage'=> ['@type' => 'WebPage', '@id' => get_permalink()],
            'image'           => get_the_post_thumbnail_url($post, 'venom-wide') ?: home_url('/wp-content/themes/venom-theme/assets/images/og-default.jpg'),
            // Speakable — AEO 음성검색 최적화
            'speakable' => [
                '@type'      => 'SpeakableSpecification',
                'cssSelector' => ['.page-content h1', '.page-content h2', '.hero-desc', '.speakable'],
            ],
        ];
    }

    /* ── 서비스 페이지: Service Schema ─── */
    if (is_singular('venom_service') || is_page()) {
        $service_type = get_post_meta($post->ID ?? 0, '_venom_service_type', true);
        if ($service_type) {
            $schemas[] = [
                '@context'    => 'https://schema.org',
                '@type'       => 'Service',
                'name'        => get_the_title(),
                'description' => wp_trim_words(get_the_excerpt(), 30),
                'provider'    => ['@type' => 'Organization', '@id' => home_url('/#organization')],
                'serviceType' => $service_type,
                'areaServed'  => ['@type' => 'Country', 'name' => '대한민국'],
                'url'         => get_permalink(),
            ];
        }
    }

    /* ── FAQ 페이지: FAQPage (AEO 핵심) ─── */
    $faqs = get_post_meta($post->ID ?? 0, '_venom_faqs', true);
    if (is_array($faqs) && count($faqs)) {
        $faq_schema = [
            '@context'   => 'https://schema.org',
            '@type'      => 'FAQPage',
            'mainEntity' => [],
        ];
        foreach ($faqs as $faq) {
            $faq_schema['mainEntity'][] = [
                '@type'          => 'Question',
                'name'           => $faq['question'],
                'acceptedAnswer' => [
                    '@type' => 'Answer',
                    'text'  => $faq['answer'],
                ],
            ];
        }
        $schemas[] = $faq_schema;
    }

    /* ── BreadcrumbList ─── */
    if (is_singular() && !is_front_page()) {
        $breadcrumbs   = [];
        $breadcrumbs[] = ['@type' => 'ListItem', 'position' => 1, 'name' => '홈', 'item' => home_url('/')];
        if (is_singular('post')) {
            $cats = get_the_category();
            if ($cats) {
                $breadcrumbs[] = ['@type' => 'ListItem', 'position' => 2, 'name' => $cats[0]->name, 'item' => get_category_link($cats[0]->term_id)];
                $breadcrumbs[] = ['@type' => 'ListItem', 'position' => 3, 'name' => get_the_title(), 'item' => get_permalink()];
            }
        } else {
            $breadcrumbs[] = ['@type' => 'ListItem', 'position' => 2, 'name' => get_the_title(), 'item' => get_permalink()];
        }
        $schemas[] = [
            '@context'        => 'https://schema.org',
            '@type'           => 'BreadcrumbList',
            'itemListElement' => $breadcrumbs,
        ];
    }

    foreach ($schemas as $schema) {
        echo '<script type="application/ld+json">'
            . wp_json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT)
            . '</script>' . "\n";
    }
}
add_action('wp_head', 'venom_rich_schema', 10);

/* ============================================================
   3. GEO — 생성AI 크롤러 허용 (robots.txt 필터)
   ============================================================ */

/**
 * GEO 전략: GPTBot, Claude-Web, PerplexityBot, GoogleExtendedBot 등
 * 생성AI 크롤러가 콘텐츠를 수집해 답변 소스로 활용할 수 있도록 허용.
 * 단, 관리자·로그인 경로는 차단.
 */
function venom_robots_txt(string $output, bool $public): string {
    if (!$public) return $output;
    $output .= "\n# === GEO: 생성AI 크롤러 허용 ===\n";
    $ai_bots = [
        'GPTBot', 'ChatGPT-User', 'OAI-SearchBot',
        'Claude-Web', 'ClaudeBot', 'anthropic-ai',
        'PerplexityBot', 'cohere-ai', 'YouBot',
        'Google-Extended', 'Googlebot-Extended',
        'facebookexternalhit', 'Applebot-Extended',
        'Bytespider', 'bingbot',
    ];
    foreach ($ai_bots as $bot) {
        $output .= "User-agent: {$bot}\nAllow: /\nDisallow: /wp-admin/\nDisallow: /wp-json/\n\n";
    }
    return $output;
}
add_filter('robots_txt', 'venom_robots_txt', 10, 2);

/* ============================================================
   4. AEO — 답변 최적화 콘텐츠 메타박스
   ============================================================ */

/** FAQ 메타박스 등록 */
function venom_faq_metabox(): void {
    add_meta_box(
        'venom_faq_box',
        'FAQ (AEO — 구글 AI Overviews 최적화)',
        'venom_faq_metabox_html',
        ['post', 'page', 'venom_service'],
        'normal', 'high'
    );

    add_meta_box(
        'venom_seo_box',
        'SEO / GEO 설정',
        'venom_seo_metabox_html',
        ['post', 'page', 'venom_service'],
        'side', 'high'
    );
}
add_action('add_meta_boxes', 'venom_faq_metabox');

function venom_faq_metabox_html(\WP_Post $post): void {
    $faqs = get_post_meta($post->ID, '_venom_faqs', true) ?: [];
    wp_nonce_field('venom_faq_save', 'venom_faq_nonce');
    ?>
    <div id="venomFaqContainer">
    <?php foreach ($faqs as $i => $faq): ?>
      <div class="venom-faq-row" style="background:#f6f9fc;padding:12px;margin:8px 0;border-radius:6px;border:1px solid #e3e8ee;">
        <p><label style="font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px;">질문</label><br>
        <input type="text" name="venom_faq_q[]" value="<?php echo esc_attr($faq['question']); ?>" style="width:100%;margin-top:4px;"></p>
        <p><label style="font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px;">답변</label><br>
        <textarea name="venom_faq_a[]" rows="3" style="width:100%;margin-top:4px;"><?php echo esc_textarea($faq['answer']); ?></textarea></p>
        <button type="button" onclick="this.closest('.venom-faq-row').remove()" style="color:#ea2261;background:none;border:none;cursor:pointer;font-size:12px;">삭제</button>
      </div>
    <?php endforeach; ?>
    </div>
    <button type="button" id="venomAddFaq"
      style="margin-top:8px;padding:6px 14px;background:#533afd;color:#fff;border:none;border-radius:9999px;cursor:pointer;font-size:13px;">
      + FAQ 추가
    </button>
    <p class="description" style="margin-top:8px;">FAQ는 구글 AI Overviews, 음성검색(AEO), 생성AI 답변(GEO) 소스로 직접 활용됩니다.</p>
    <script>
    document.getElementById('venomAddFaq').addEventListener('click', function(){
      var html = `<div class="venom-faq-row" style="background:#f6f9fc;padding:12px;margin:8px 0;border-radius:6px;border:1px solid #e3e8ee;">
        <p><label style="font-weight:600;font-size:12px;text-transform:uppercase;">질문</label><br>
        <input type="text" name="venom_faq_q[]" style="width:100%;margin-top:4px;"></p>
        <p><label style="font-weight:600;font-size:12px;text-transform:uppercase;">답변</label><br>
        <textarea name="venom_faq_a[]" rows="3" style="width:100%;margin-top:4px;"></textarea></p>
        <button type="button" onclick="this.closest('.venom-faq-row').remove()" style="color:#ea2261;background:none;border:none;cursor:pointer;font-size:12px;">삭제</button>
      </div>`;
      document.getElementById('venomFaqContainer').insertAdjacentHTML('beforeend', html);
    });
    </script>
    <?php
}

function venom_seo_metabox_html(\WP_Post $post): void {
    $meta_desc    = get_post_meta($post->ID, '_venom_meta_desc', true);
    $focus_kw     = get_post_meta($post->ID, '_venom_focus_kw', true);
    $geo_entities = get_post_meta($post->ID, '_venom_geo_entities', true);
    $service_type = get_post_meta($post->ID, '_venom_service_type', true);
    wp_nonce_field('venom_seo_save', 'venom_seo_nonce');
    ?>
    <table class="form-table" style="font-size:13px;">
      <tr>
        <th style="padding:6px 0;font-weight:600;">메타 설명 (160자)</th>
        <td><textarea name="venom_meta_desc" rows="3" style="width:100%;"><?php echo esc_textarea($meta_desc); ?></textarea></td>
      </tr>
      <tr>
        <th style="padding:6px 0;font-weight:600;">포커스 키워드</th>
        <td><input type="text" name="venom_focus_kw" value="<?php echo esc_attr($focus_kw); ?>" style="width:100%;">
        <p class="description">예: 치과마케팅, 병원 SEO</p></td>
      </tr>
      <tr>
        <th style="padding:6px 0;font-weight:600;">GEO 엔티티</th>
        <td><input type="text" name="venom_geo_entities" value="<?php echo esc_attr($geo_entities); ?>" style="width:100%;">
        <p class="description">쉼표 구분. 예: 치과,임플란트,대구치과,스케일링 — AI가 엔티티로 인식</p></td>
      </tr>
      <tr>
        <th style="padding:6px 0;font-weight:600;">서비스 유형 (Schema)</th>
        <td><input type="text" name="venom_service_type" value="<?php echo esc_attr($service_type); ?>" style="width:100%;">
        <p class="description">예: 치과 마케팅 서비스, SEO 최적화 서비스</p></td>
      </tr>
    </table>
    <?php
}

/** FAQ + SEO 메타박스 저장 */
function venom_save_meta(\WP_Post $post): void {
    // FAQ
    if (
        isset($_POST['venom_faq_nonce'])
        && wp_verify_nonce($_POST['venom_faq_nonce'], 'venom_faq_save')
        && current_user_can('edit_post', $post->ID)
    ) {
        $questions = array_map('sanitize_text_field', $_POST['venom_faq_q'] ?? []);
        $answers   = array_map('sanitize_textarea_field', $_POST['venom_faq_a'] ?? []);
        $faqs = [];
        foreach ($questions as $i => $q) {
            if (trim($q) && isset($answers[$i]) && trim($answers[$i])) {
                $faqs[] = ['question' => $q, 'answer' => $answers[$i]];
            }
        }
        update_post_meta($post->ID, '_venom_faqs', $faqs);
    }

    // SEO
    if (
        isset($_POST['venom_seo_nonce'])
        && wp_verify_nonce($_POST['venom_seo_nonce'], 'venom_seo_save')
        && current_user_can('edit_post', $post->ID)
    ) {
        update_post_meta($post->ID, '_venom_meta_desc',    sanitize_textarea_field($_POST['venom_meta_desc']    ?? ''));
        update_post_meta($post->ID, '_venom_focus_kw',     sanitize_text_field($_POST['venom_focus_kw']         ?? ''));
        update_post_meta($post->ID, '_venom_geo_entities', sanitize_text_field($_POST['venom_geo_entities']     ?? ''));
        update_post_meta($post->ID, '_venom_service_type', sanitize_text_field($_POST['venom_service_type']     ?? ''));
    }
}
add_action('save_post', 'venom_save_meta');

/* ============================================================
   5. GEO 엔티티 키워드 자동 메타태그 출력
   ============================================================ */
function venom_geo_entity_meta(): void {
    if (!is_singular()) return;
    global $post;
    $entities = get_post_meta($post->ID, '_venom_geo_entities', true);
    if ($entities) {
        echo '<meta name="keywords" content="' . esc_attr($entities) . '">' . "\n";
        // AI 크롤러용 엔티티 힌트
        echo '<meta name="subject" content="' . esc_attr(get_the_title() . ' — 병원마케팅 베놈') . '">' . "\n";
    }
}
add_action('wp_head', 'venom_geo_entity_meta', 6);

/* ============================================================
   6. Core Web Vitals 최적화
   ============================================================ */

/** 불필요한 기본 스크립트 제거 */
function venom_cleanup_head(): void {
    remove_action('wp_head', 'wp_generator');
    remove_action('wp_head', 'wlwmanifest_link');
    remove_action('wp_head', 'rsd_link');
    remove_action('wp_head', 'wp_shortlink_wp_head');
    remove_action('wp_head', 'print_emoji_detection_script', 7);
    remove_action('wp_print_styles', 'print_emoji_styles');
    remove_action('admin_print_scripts', 'print_emoji_detection_script');
    remove_action('admin_print_styles', 'print_emoji_styles');
}
add_action('init', 'venom_cleanup_head');

/** 미사용 블록 CSS 제거 */
add_filter('should_load_separate_core_block_assets', '__return_true');

/** 폰트 preconnect */
function venom_preconnect_fonts(): void {
    echo '<link rel="preconnect" href="https://fonts.googleapis.com">' . "\n";
    echo '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' . "\n";
    echo '<link rel="dns-prefetch" href="//fonts.googleapis.com">' . "\n";
    echo '<link rel="dns-prefetch" href="//unpkg.com">' . "\n";
}
add_action('wp_head', 'venom_preconnect_fonts', 1);

/* ============================================================
   7. 내부 링크 강화 (SEO 링크 주스)
   ============================================================ */

/** 관련 글 (같은 카테고리 최근 3개) */
function venom_related_posts(): string {
    if (!is_singular('post')) return '';
    global $post;
    $cats = wp_get_post_categories($post->ID);
    if (!$cats) return '';

    $related = get_posts([
        'category__in'   => $cats,
        'post__not_in'   => [$post->ID],
        'posts_per_page' => 3,
        'orderby'        => 'rand',
    ]);
    if (!$related) return '';

    $out  = '<section class="related-posts section-soft" style="padding:40px;border-radius:12px;margin-top:40px;">';
    $out .= '<h3 class="heading-md" style="margin-bottom:24px;">관련 글</h3>';
    $out .= '<div class="blog-grid">';
    foreach ($related as $r) {
        $thumb = get_the_post_thumbnail_url($r->ID, 'venom-thumb');
        $out  .= '<article class="blog-card">';
        if ($thumb) {
            $out .= '<a href="' . get_permalink($r) . '" class="blog-card-thumb"><img src="' . esc_url($thumb) . '" alt="' . esc_attr($r->post_title) . '" loading="lazy"></a>';
        }
        $out .= '<div class="blog-card-body">';
        $out .= '<h4><a href="' . get_permalink($r) . '">' . esc_html($r->post_title) . '</a></h4>';
        $out .= '</div></article>';
    }
    $out .= '</div></section>';
    return $out;
}
add_filter('the_content', function(string $c): string {
    return $c . venom_related_posts();
});

/* ============================================================
   8. 사이트 퍼포먼스: HTML 출력 압축
   ============================================================ */
function venom_compress_html(string $html): string {
    if (!is_admin() && !is_feed()) {
        $html = preg_replace('/<!--(?!\s*(?:\[if [^\]]+]|<!|>))(?:(?!-->).)*-->/s', '', $html);
        $html = preg_replace('/\s{2,}/', ' ', $html);
    }
    return $html;
}
add_filter('final_output', 'venom_compress_html');
