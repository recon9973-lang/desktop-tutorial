<?php
/**
 * Plugin Name: VENOM Analytics
 * Plugin URI:  https://github.com/recon9973-lang/desktop-tutorial
 * Description: 경량 페이지뷰 트래커 — 외부 JS 없이 WordPress 자체 DB에 방문 데이터 수집.
 *              관리자 대시보드 위젯 + REST API /wp-json/venom/v1/analytics 제공.
 * Version:     1.0.0
 * Author:      VENOM Site Factory
 * License:     GPL-2.0-or-later
 * Network:     true
 */
defined('ABSPATH') || exit;

define('VN_ANALYTICS_VERSION', '1.0.0');
define('VN_ANALYTICS_TABLE',   'venom_pageviews');

/* ──────────────────────────────────────────────────
   1. 활성화 / 비활성화 — 테이블 생성·삭제
────────────────────────────────────────────────── */
register_activation_hook(__FILE__, 'vn_analytics_activate');
function vn_analytics_activate($network_wide = false) {
    if (is_multisite() && $network_wide) {
        foreach (get_sites(['fields' => 'ids']) as $blog_id) {
            switch_to_blog($blog_id);
            vn_analytics_create_table();
            restore_current_blog();
        }
    } else {
        vn_analytics_create_table();
    }
}

function vn_analytics_create_table() {
    global $wpdb;
    $table   = $wpdb->prefix . VN_ANALYTICS_TABLE;
    $charset = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE IF NOT EXISTS {$table} (
        id          BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
        blog_id     BIGINT(20) UNSIGNED NOT NULL DEFAULT 1,
        post_id     BIGINT(20) UNSIGNED NOT NULL DEFAULT 0,
        path        VARCHAR(512) NOT NULL DEFAULT '',
        referer     VARCHAR(512) NOT NULL DEFAULT '',
        ua_class    VARCHAR(32)  NOT NULL DEFAULT 'human',
        country     VARCHAR(2)   NOT NULL DEFAULT '',
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_blog_path (blog_id, path(191)),
        KEY idx_created   (created_at)
    ) {$charset};";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta($sql);
}

register_deactivation_hook(__FILE__, 'vn_analytics_deactivate');
function vn_analytics_deactivate() {
    // 테이블은 유지 (데이터 보존). 완전 제거는 uninstall.php 에서.
}

/* ──────────────────────────────────────────────────
   2. 페이지뷰 기록 (프론트엔드)
────────────────────────────────────────────────── */
add_action('wp', 'vn_analytics_record_view');
function vn_analytics_record_view() {
    if (is_admin() || wp_is_json_request()) return;

    $ua = $_SERVER['HTTP_USER_AGENT'] ?? '';
    $ua_class = vn_analytics_classify_ua($ua);

    // 봇/크롤러 기록 여부 (옵션으로 제어, 기본 제외)
    if ($ua_class !== 'human' && !get_option('vn_analytics_log_bots', false)) return;

    // 동일 세션 내 같은 경로 중복 제거 (쿠키 기반)
    $path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    $cookie_key = 'vn_pv_' . md5($path);
    if (!empty($_COOKIE[$cookie_key])) return;

    // 세션 쿠키 (30분)
    setcookie($cookie_key, '1', time() + 1800, COOKIEPATH, COOKIE_DOMAIN, is_ssl(), true);

    global $wpdb;
    $wpdb->insert(
        $wpdb->prefix . VN_ANALYTICS_TABLE,
        [
            'blog_id'    => get_current_blog_id(),
            'post_id'    => (int)(get_queried_object_id() ?: 0),
            'path'       => substr($path, 0, 512),
            'referer'    => substr(sanitize_text_field($_SERVER['HTTP_REFERER'] ?? ''), 0, 512),
            'ua_class'   => $ua_class,
            'country'    => vn_analytics_country_code($_SERVER['HTTP_CF_IPCOUNTRY'] ?? ''),
            'created_at' => current_time('mysql', true),
        ],
        ['%d', '%d', '%s', '%s', '%s', '%s', '%s']
    );
}

function vn_analytics_classify_ua(string $ua): string {
    $ua_lower = strtolower($ua);
    $bot_hints = ['bot', 'crawl', 'spider', 'slurp', 'fetch', 'headless', 'wget', 'curl', 'python'];
    foreach ($bot_hints as $hint) {
        if (str_contains($ua_lower, $hint)) return 'bot';
    }
    return 'human';
}

function vn_analytics_country_code(string $raw): string {
    return preg_match('/^[A-Z]{2}$/', strtoupper($raw)) ? strtoupper($raw) : '';
}

/* ──────────────────────────────────────────────────
   3. 관리자 대시보드 위젯
────────────────────────────────────────────────── */
add_action('wp_dashboard_setup', 'vn_analytics_dashboard_widget');
function vn_analytics_dashboard_widget() {
    if (!current_user_can('manage_options')) return;
    wp_add_dashboard_widget(
        'vn_analytics_widget',
        '📊 VENOM Analytics — 최근 7일 페이지뷰',
        'vn_analytics_render_widget'
    );
}

function vn_analytics_render_widget() {
    global $wpdb;
    $table = $wpdb->prefix . VN_ANALYTICS_TABLE;
    $since = date('Y-m-d H:i:s', strtotime('-7 days'), true);

    $total = (int)$wpdb->get_var(
        $wpdb->prepare("SELECT COUNT(*) FROM {$table} WHERE blog_id=%d AND created_at>=%s AND ua_class='human'",
            get_current_blog_id(), $since)
    );

    $rows = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT path, COUNT(*) AS views
               FROM {$table}
              WHERE blog_id=%d AND created_at>=%s AND ua_class='human'
              GROUP BY path
              ORDER BY views DESC
              LIMIT 10",
            get_current_blog_id(), $since
        )
    );

    echo '<p style="margin:0 0 10px;font-size:24px;font-weight:300;color:#3b5bdb">'
        . number_format($total)
        . ' <span style="font-size:13px;color:#64748b">인간 방문 (최근 7일)</span></p>';

    if (empty($rows)) { echo '<p style="color:#94a3b8">아직 데이터 없음.</p>'; return; }

    echo '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        . '<tr><th style="text-align:left;padding:4px 0;color:#64748b;font-weight:500">경로</th>'
        . '<th style="text-align:right;color:#64748b;font-weight:500">뷰</th></tr>';
    foreach ($rows as $r) {
        $path_esc = esc_html($r->path);
        echo "<tr><td style='padding:3px 0;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>"
            . "<a href='" . esc_url(home_url($r->path)) . "' target='_blank'>{$path_esc}</a></td>"
            . "<td style='text-align:right;color:#3b5bdb;font-weight:500'>" . number_format((int)$r->views) . "</td></tr>";
    }
    echo '</table>';
    echo '<p style="margin:10px 0 0;font-size:12px;color:#94a3b8">'
        . '<a href="' . esc_url(admin_url('admin.php?page=vn-analytics')) . '">전체 리포트 보기 →</a></p>';
}

/* ──────────────────────────────────────────────────
   4. 관리자 메뉴 — 전체 리포트 페이지
────────────────────────────────────────────────── */
add_action('admin_menu', 'vn_analytics_admin_menu');
function vn_analytics_admin_menu() {
    add_menu_page(
        'VENOM Analytics',
        '📊 Analytics',
        'manage_options',
        'vn-analytics',
        'vn_analytics_admin_page',
        'dashicons-chart-line',
        25
    );
}

function vn_analytics_admin_page() {
    if (!current_user_can('manage_options')) wp_die('권한 없음');

    global $wpdb;
    $table   = $wpdb->prefix . VN_ANALYTICS_TABLE;
    $blog_id = get_current_blog_id();
    $period  = (int)($_GET['period'] ?? 30);
    $period  = in_array($period, [7, 30, 90]) ? $period : 30;
    $since   = date('Y-m-d H:i:s', strtotime("-{$period} days"), true);

    $total = (int)$wpdb->get_var(
        $wpdb->prepare("SELECT COUNT(*) FROM {$table} WHERE blog_id=%d AND created_at>=%s AND ua_class='human'",
            $blog_id, $since)
    );

    $by_day = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT DATE(created_at) AS day, COUNT(*) AS views
               FROM {$table}
              WHERE blog_id=%d AND created_at>=%s AND ua_class='human'
              GROUP BY DATE(created_at)
              ORDER BY day ASC",
            $blog_id, $since
        )
    );

    $top_pages = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT path, COUNT(*) AS views
               FROM {$table}
              WHERE blog_id=%d AND created_at>=%s AND ua_class='human'
              GROUP BY path ORDER BY views DESC LIMIT 20",
            $blog_id, $since
        )
    );

    $top_refs = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT referer, COUNT(*) AS cnt
               FROM {$table}
              WHERE blog_id=%d AND created_at>=%s AND ua_class='human' AND referer!=''
              GROUP BY referer ORDER BY cnt DESC LIMIT 10",
            $blog_id, $since
        )
    );

    $periods = [7 => '최근 7일', 30 => '최근 30일', 90 => '최근 90일'];
    ?>
    <div class="wrap">
      <h1>📊 VENOM Analytics</h1>
      <div style="margin:16px 0;display:flex;gap:8px">
        <?php foreach ($periods as $d => $label): ?>
          <a href="<?= esc_url(admin_url('admin.php?page=vn-analytics&period='.$d)) ?>"
             class="button<?= $period===$d ? ' button-primary' : '' ?>"><?= esc_html($label) ?></a>
        <?php endforeach; ?>
      </div>

      <div style="display:flex;gap:20px;margin-bottom:28px">
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px 28px;flex:1;text-align:center">
          <div style="font-size:36px;font-weight:300;color:#3b5bdb"><?= number_format($total) ?></div>
          <div style="font-size:13px;color:#64748b;margin-top:4px">총 페이지뷰</div>
        </div>
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px 28px;flex:1;text-align:center">
          <div style="font-size:36px;font-weight:300;color:#3b5bdb"><?= number_format($period > 0 ? round($total / $period, 1) : 0) ?></div>
          <div style="font-size:13px;color:#64748b;margin-top:4px">일 평균</div>
        </div>
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px 28px;flex:1;text-align:center">
          <div style="font-size:36px;font-weight:300;color:#3b5bdb"><?= count($top_pages) ?></div>
          <div style="font-size:13px;color:#64748b;margin-top:4px">유니크 경로</div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px">
        <!-- 상위 페이지 -->
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px">
          <h2 style="font-size:15px;margin:0 0 14px;font-weight:600">상위 페이지</h2>
          <table class="widefat striped" style="font-size:13px">
            <thead><tr><th>경로</th><th style="text-align:right">뷰</th></tr></thead>
            <tbody>
            <?php foreach ($top_pages as $r): ?>
              <tr>
                <td><a href="<?= esc_url(home_url($r->path)) ?>" target="_blank"><?= esc_html($r->path) ?></a></td>
                <td style="text-align:right;color:#3b5bdb;font-weight:500"><?= number_format((int)$r->views) ?></td>
              </tr>
            <?php endforeach; ?>
            <?php if (empty($top_pages)): ?>
              <tr><td colspan="2" style="color:#94a3b8">데이터 없음</td></tr>
            <?php endif; ?>
            </tbody>
          </table>
        </div>

        <!-- 유입 경로 -->
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px">
          <h2 style="font-size:15px;margin:0 0 14px;font-weight:600">유입 경로 (Top 10)</h2>
          <table class="widefat striped" style="font-size:13px">
            <thead><tr><th>레퍼러</th><th style="text-align:right">수</th></tr></thead>
            <tbody>
            <?php foreach ($top_refs as $r): ?>
              <tr>
                <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                  <?= esc_html($r->referer) ?></td>
                <td style="text-align:right"><?= number_format((int)$r->cnt) ?></td>
              </tr>
            <?php endforeach; ?>
            <?php if (empty($top_refs)): ?>
              <tr><td colspan="2" style="color:#94a3b8">데이터 없음</td></tr>
            <?php endif; ?>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 일별 차트 (간단 ASCII 스파크라인 대용) -->
      <?php if (!empty($by_day)): ?>
      <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin-top:20px">
        <h2 style="font-size:15px;margin:0 0 14px;font-weight:600">일별 트렌드</h2>
        <?php $max_v = max(array_column($by_day, 'views')) ?: 1; ?>
        <div style="display:flex;align-items:flex-end;gap:4px;height:80px">
        <?php foreach ($by_day as $d): ?>
          <?php $h = max(4, round((int)$d->views / $max_v * 80)); ?>
          <div title="<?= esc_attr($d->day) ?>: <?= (int)$d->views ?>뷰"
               style="flex:1;background:#3b5bdb;border-radius:3px 3px 0 0;height:<?= $h ?>px;min-width:4px;opacity:.8;cursor:pointer"></div>
        <?php endforeach; ?>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-top:4px">
          <span><?= esc_html($by_day[0]->day ?? '') ?></span>
          <span><?= esc_html($by_day[count($by_day)-1]->day ?? '') ?></span>
        </div>
      </div>
      <?php endif; ?>
    </div>
    <?php
}

/* ──────────────────────────────────────────────────
   5. REST API — /wp-json/venom/v1/analytics
────────────────────────────────────────────────── */
add_action('rest_api_init', 'vn_analytics_register_routes');
function vn_analytics_register_routes() {
    register_rest_route('venom/v1', '/analytics', [
        'methods'             => 'GET',
        'callback'            => 'vn_analytics_rest_handler',
        'permission_callback' => function() {
            return current_user_can('manage_options');
        },
        'args' => [
            'period' => [
                'default'           => 30,
                'sanitize_callback' => 'absint',
            ],
            'limit' => [
                'default'           => 20,
                'sanitize_callback' => 'absint',
            ],
        ],
    ]);
}

function vn_analytics_rest_handler(WP_REST_Request $req): WP_REST_Response {
    global $wpdb;
    $table   = $wpdb->prefix . VN_ANALYTICS_TABLE;
    $blog_id = get_current_blog_id();
    $period  = min((int)$req->get_param('period'), 365);
    $limit   = min((int)$req->get_param('limit'), 100);
    $since   = date('Y-m-d H:i:s', strtotime("-{$period} days"), true);

    $total = (int)$wpdb->get_var(
        $wpdb->prepare("SELECT COUNT(*) FROM {$table} WHERE blog_id=%d AND created_at>=%s AND ua_class='human'",
            $blog_id, $since)
    );

    $pages = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT path, COUNT(*) AS views FROM {$table}
              WHERE blog_id=%d AND created_at>=%s AND ua_class='human'
              GROUP BY path ORDER BY views DESC LIMIT %d",
            $blog_id, $since, $limit
        ),
        ARRAY_A
    );

    $daily = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT DATE(created_at) AS date, COUNT(*) AS views FROM {$table}
              WHERE blog_id=%d AND created_at>=%s AND ua_class='human'
              GROUP BY DATE(created_at) ORDER BY date ASC",
            $blog_id, $since
        ),
        ARRAY_A
    );

    return new WP_REST_Response([
        'period_days' => $period,
        'total_views' => $total,
        'pages'       => $pages,
        'daily'       => $daily,
        'generated'   => current_time('c'),
    ], 200);
}
