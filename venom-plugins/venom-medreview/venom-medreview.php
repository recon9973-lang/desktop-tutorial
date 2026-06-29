<?php
/**
 * Plugin Name:  VENOM Medical Review
 * Plugin URI:   https://github.com/recon9973-lang/desktop-tutorial
 * Description:  의료광고법 제56조 기반 금지·위험 표현 자동 검수. 포스트 저장 시 실시간 검수, 관리자 상태 컬럼 표시.
 * Version:      0.2.0
 * Author:       VENOM Site Factory
 * Text Domain:  venom-medreview
 * Network:      true
 */

if ( ! defined( 'ABSPATH' ) ) exit;

// ── 금지 표현 목록 (lib/medical-ad-validator.js 와 동기화) ──────────────────
define( 'VENOM_MR_FORBIDDEN', [
    '최고','최상','최대','최초','유일','넘버원','1등','1위','업계 최고','국내 최고',
    '100% 효과','완치','완전히 낫','완벽한 치료','치료 보장','효과 보장','반드시',
    '무조건','절대적','탁월한 효과','놀라운 효과','기적','기적적',
    '부작용 없','부작용 전혀','안전한 시술','완전히 안전','100% 안전',
    '통증 없이','통증 전혀','마취 없이도',
    '타 병원보다','타 의원보다','경쟁 병원','다른 병원은 안',
    '무료 시술','공짜 이벤트','경품','선착순 혜택','할인 쿠폰 지급',
    '연예인 추천','유명인',
    '최저가 보장','가격 보장','가장 저렴',
] );

// ── 검수 함수 ────────────────────────────────────────────────────────────────

function venom_mr_validate( $text ) {
    $lower    = mb_strtolower( $text );
    $found    = [];
    foreach ( VENOM_MR_FORBIDDEN as $w ) {
        if ( mb_strpos( $lower, mb_strtolower( $w ) ) !== false ) {
            $found[] = $w;
        }
    }
    return [
        'pass'      => empty( $found ),
        'forbidden' => $found,
    ];
}

// ── 포스트 저장 시 검수 결과를 post meta 에 저장 ─────────────────────────────

add_action( 'save_post', function( $post_id, $post ) {
    if ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) return;
    if ( ! in_array( $post->post_status, [ 'publish', 'draft', 'pending' ], true ) ) return;
    $content = wp_strip_all_tags( $post->post_content . ' ' . $post->post_title );
    $result  = venom_mr_validate( $content );
    update_post_meta( $post_id, '_venom_mr_pass',      $result['pass'] ? '1' : '0' );
    update_post_meta( $post_id, '_venom_mr_forbidden', implode( ', ', $result['forbidden'] ) );
}, 10, 2 );

// ── 관리자 포스트 목록 — 검수 상태 컬럼 ──────────────────────────────────────

add_filter( 'manage_posts_columns', function( $cols ) {
    $cols['venom_mr'] = '의료광고 검수';
    return $cols;
} );

add_action( 'manage_posts_custom_column', function( $col, $post_id ) {
    if ( $col !== 'venom_mr' ) return;
    $pass = get_post_meta( $post_id, '_venom_mr_pass', true );
    if ( $pass === '' ) {
        echo '<span style="color:#999">—</span>';
    } elseif ( $pass === '1' ) {
        echo '<span style="color:#1a7f37;font-weight:700">✅ 통과</span>';
    } else {
        $words = get_post_meta( $post_id, '_venom_mr_forbidden', true );
        echo '<span style="color:#cf222e;font-weight:700" title="' . esc_attr( $words ) . '">⚠ 위반</span>';
    }
}, 10, 2 );

// ── REST API 엔드포인트 (외부 Node.js 에서 호출 가능) ───────────────────────

add_action( 'rest_api_init', function() {
    register_rest_route( 'venom/v1', '/medreview', [
        'methods'             => 'POST',
        'callback'            => function( WP_REST_Request $req ) {
            $text   = sanitize_textarea_field( $req->get_param( 'text' ) ?? '' );
            $result = venom_mr_validate( $text );
            return rest_ensure_response( $result );
        },
        'permission_callback' => '__return_true',
    ] );
} );
