<?php
/**
 * Plugin Name:  VENOM SEO
 * Plugin URI:   https://github.com/recon9973-lang/desktop-tutorial
 * Description:  robots.txt / sitemap.xml / llms.txt 동적 발행. Schema.org MedicalClinic 자동 삽입.
 * Version:      0.2.0
 * Author:       VENOM Site Factory
 * Text Domain:  venom-seo
 * Network:      true
 */

if ( ! defined( 'ABSPATH' ) ) exit;

// ── robots.txt ────────────────────────────────────────────────────────────────

add_filter( 'robots_txt', function( $output, $public ) {
    $domain = parse_url( get_site_url(), PHP_URL_HOST );
    return "User-agent: *\nAllow: /\nSitemap: https://{$domain}/sitemap.xml\n\n"
         . "# AI crawlers\nUser-agent: GPTBot\nAllow: /\nUser-agent: ClaudeBot\nAllow: /\n"
         . "User-agent: PerplexityBot\nAllow: /\nUser-agent: Google-Extended\nAllow: /\n";
}, 10, 2 );

// ── llms.txt 엔드포인트 ───────────────────────────────────────────────────────

add_action( 'init', function() {
    add_rewrite_rule( '^llms\.txt$', 'index.php?venom_llms=1', 'top' );
} );

add_filter( 'query_vars', function( $vars ) {
    $vars[] = 'venom_llms';
    return $vars;
} );

add_action( 'template_redirect', function() {
    if ( ! get_query_var( 'venom_llms' ) ) return;
    $name    = get_bloginfo('name');
    $desc    = get_bloginfo('description');
    $url     = get_site_url();
    $domain  = parse_url( $url, PHP_URL_HOST );
    $primary = get_option( 'venom_primary', '#533afd' );
    header( 'Content-Type: text/plain; charset=utf-8' );
    echo "# $name\n> $desc\n\n"
       . "사이트: $url\n"
       . "브랜드 색상: $primary\n\n"
       . "## 주요 페이지\n"
       . "- [홈페이지]($url)\n"
       . "- [진료안내]($url/departments)\n"
       . "- [의료진]($url/doctors)\n"
       . "- [블로그]($url/blog)\n"
       . "\n## AI 크롤링 정책\n"
       . "GPTBot, ClaudeBot, PerplexityBot, Google-Extended 크롤링을 허용합니다.\n"
       . "출처 명기 시 콘텐츠 인용을 허가합니다.\n";
    exit;
} );

// ── Schema.org MedicalClinic 헤드 삽입 ────────────────────────────────────────

add_action( 'wp_head', function() {
    if ( ! is_front_page() ) return;
    $name     = get_bloginfo('name');
    $url      = get_site_url();
    $phone    = get_option('venom_phone', '');
    $address  = get_option('venom_address', '');
    $region   = get_option('venom_region', '');
    $schema   = [
        '@context' => 'https://schema.org',
        '@type'    => 'MedicalClinic',
        'name'     => $name,
        'url'      => $url,
        'telephone' => $phone,
        'address'  => [
            '@type'           => 'PostalAddress',
            'addressLocality' => $region,
            'streetAddress'   => $address,
        ],
    ];
    echo '<script type="application/ld+json">' . wp_json_encode( $schema, JSON_UNESCAPED_UNICODE ) . "</script>\n";
} );
