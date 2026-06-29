<?php
/**
 * Plugin Name:  VENOM AutoBlog
 * Plugin URI:   https://github.com/recon9973-lang/desktop-tutorial
 * Description:  블로그 자동발행. WP-Cron 으로 키워드별 포스트를 주기적으로 생성한다. (engine/blog-gen.js 배선)
 * Version:      0.2.0
 * Author:       VENOM Site Factory
 * Text Domain:  venom-autoblog
 * Network:      true
 */

if ( ! defined( 'ABSPATH' ) ) exit;

// ── 설치·제거 ─────────────────────────────────────────────────────────────────

register_activation_hook( __FILE__, function() {
    if ( ! wp_next_scheduled( 'venom_autoblog_run' ) ) {
        wp_schedule_event( time(), 'daily', 'venom_autoblog_run' );
    }
} );

register_deactivation_hook( __FILE__, function() {
    wp_clear_scheduled_hook( 'venom_autoblog_run' );
} );

// ── WP-Cron 핸들러 ───────────────────────────────────────────────────────────

add_action( 'venom_autoblog_run', function() {
    $site_id  = get_current_blog_id();
    $category = get_option( 'venom_specialty', '' );
    $region   = get_option( 'venom_region',    '' );
    $keywords_raw = get_option( 'venom_keywords', '' );
    if ( ! $category || ! $keywords_raw ) return;

    $keywords = array_filter( array_map( 'trim', explode( ',', $keywords_raw ) ) );

    // Node.js blog-gen.js 가 있을 경우 CLI 호출 (Docker WP 환경)
    $script = defined( 'VENOM_BLOG_GEN' ) ? VENOM_BLOG_GEN : '';
    if ( $script && is_executable( $script ) && isset( $_SERVER['OPENAI_API_KEY'] ) ) {
        $spec_path = get_option( 'venom_spec_path', '' );
        if ( $spec_path && file_exists( $spec_path ) ) {
            $cmd = escapeshellcmd( "node $script " . escapeshellarg( $spec_path ) ) . ' 2>&1';
            $out = shell_exec( $cmd );
            error_log( '[venom-autoblog] blog-gen output: ' . $out );
            return;
        }
    }

    // CLI 없을 때 폴백: WP REST 로 자체 생성 요청
    foreach ( array_slice( $keywords, 0, 3 ) as $keyword ) {
        $response = wp_remote_post( get_site_url() . '/wp-json/venom/v1/generate-post', [
            'body'    => json_encode( compact( 'category', 'region', 'keyword' ) ),
            'headers' => [ 'Content-Type' => 'application/json' ],
            'timeout' => 90,
        ] );
        if ( is_wp_error( $response ) ) {
            error_log( '[venom-autoblog] generate-post error: ' . $response->get_error_message() );
            continue;
        }
        $body = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( ! empty( $body['title'] ) && ! empty( $body['html'] ) ) {
            wp_insert_post( [
                'post_title'   => wp_strip_all_tags( $body['title'] ),
                'post_content' => $body['html'],
                'post_status'  => $body['status'] ?? 'draft',
                'post_type'    => 'post',
                'meta_input'   => [
                    '_venom_autoblog'  => '1',
                    '_venom_post_slug' => $body['slug'] ?? '',
                ],
            ] );
        }
    }
} );

// ── REST 엔드포인트: 포스트 생성 요청 (외부 orchestrator → WP) ──────────────

add_action( 'rest_api_init', function() {
    register_rest_route( 'venom/v1', '/generate-post', [
        'methods'             => 'POST',
        'callback'            => function( WP_REST_Request $req ) {
            // 실제 AI 생성은 Node.js blog-gen.js 가 담당;
            // 이 엔드포인트는 생성된 결과를 WP 에 삽입하는 역할.
            $title   = sanitize_text_field( $req->get_param( 'title' )   ?? '' );
            $html    = wp_kses_post( $req->get_param( 'html' )           ?? '' );
            $slug_v  = sanitize_title(  $req->get_param( 'slug' )        ?? '' );
            $status  = in_array( $req->get_param( 'status' ), [ 'publish', 'draft', 'pending' ], true )
                       ? $req->get_param( 'status' ) : 'draft';

            if ( ! $title || ! $html ) {
                return new WP_Error( 'missing_fields', 'title 과 html 은 필수입니다.', [ 'status' => 400 ] );
            }

            $post_id = wp_insert_post( [
                'post_title'   => $title,
                'post_content' => $html,
                'post_name'    => $slug_v,
                'post_status'  => $status,
                'post_type'    => 'post',
                'meta_input'   => [ '_venom_autoblog' => '1' ],
            ] );

            if ( is_wp_error( $post_id ) ) {
                return $post_id;
            }
            return rest_ensure_response( [
                'post_id' => $post_id,
                'url'     => get_permalink( $post_id ),
            ] );
        },
        'permission_callback' => function() {
            return current_user_can( 'publish_posts' ) || ( defined( 'VENOM_API_KEY' ) && $_SERVER['HTTP_X_VENOM_KEY'] === VENOM_API_KEY );
        },
    ] );
} );

// ── 관리자 설정 페이지 ────────────────────────────────────────────────────────

add_action( 'admin_menu', function() {
    add_options_page( 'VENOM AutoBlog', 'VENOM AutoBlog', 'manage_options', 'venom-autoblog', function() {
        if ( isset( $_POST['_venom_nonce'] ) && wp_verify_nonce( $_POST['_venom_nonce'], 'venom_autoblog_save' ) ) {
            update_option( 'venom_specialty', sanitize_text_field( $_POST['venom_specialty'] ?? '' ) );
            update_option( 'venom_region',    sanitize_text_field( $_POST['venom_region']    ?? '' ) );
            update_option( 'venom_keywords',  sanitize_textarea_field( $_POST['venom_keywords'] ?? '' ) );
            echo '<div class="notice notice-success"><p>저장되었습니다.</p></div>';
        }
        $specialty = get_option( 'venom_specialty', '' );
        $region    = get_option( 'venom_region',    '' );
        $keywords  = get_option( 'venom_keywords',  '' );
        ?>
        <div class="wrap">
          <h1>VENOM AutoBlog 설정</h1>
          <form method="post">
            <?php wp_nonce_field( 'venom_autoblog_save', '_venom_nonce' ); ?>
            <table class="form-table">
              <tr><th>진료과 (카테고리)</th><td>
                <input type="text" name="venom_specialty" value="<?= esc_attr($specialty) ?>" class="regular-text" placeholder="dental / skin / ortho ...">
              </td></tr>
              <tr><th>지역</th><td>
                <input type="text" name="venom_region" value="<?= esc_attr($region) ?>" class="regular-text" placeholder="서울 강남">
              </td></tr>
              <tr><th>키워드 (쉼표 구분)</th><td>
                <textarea name="venom_keywords" rows="4" class="large-text"><?= esc_textarea($keywords) ?></textarea>
              </td></tr>
            </table>
            <?php submit_button('저장'); ?>
          </form>
          <hr>
          <p>다음 자동 발행: <strong><?= esc_html( date( 'Y-m-d H:i:s', wp_next_scheduled('venom_autoblog_run') ?: 0 ) ) ?></strong></p>
          <form method="post">
            <?php wp_nonce_field( 'venom_autoblog_save', '_venom_nonce' ); ?>
            <?php submit_button('지금 실행', 'secondary', 'run_now'); ?>
          </form>
          <?php if ( isset($_POST['run_now']) ) { do_action('venom_autoblog_run'); echo '<p>실행 완료.</p>'; } ?>
        </div>
        <?php
    } );
} );
