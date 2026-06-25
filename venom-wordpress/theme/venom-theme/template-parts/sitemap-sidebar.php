<?php
/**
 * 좌측 사이트맵 사이드바 — 상세 페이지 공통
 * 참고: next-t.co.kr 스타일 왼쪽 전체 사이트맵
 */
$current = get_permalink();
$sitemap = [
  ['label' => '병원마케팅', 'url' => '/hospital-marketing', 'children' => [
    ['label' => '의료광고심의',   'url' => '/hospital-marketing/medical-ad-review'],
    ['label' => '치과마케팅',     'url' => '/hospital-marketing/dental-marketing'],
    ['label' => '피부과마케팅',   'url' => '/hospital-marketing/skin-marketing'],
    ['label' => '정형외과마케팅', 'url' => '/hospital-marketing/ortho-marketing'],
    ['label' => '한의원마케팅',   'url' => '/hospital-marketing/hani-marketing'],
    ['label' => '성형외과마케팅', 'url' => '/hospital-marketing/plastic-marketing'],
    ['label' => '내과마케팅',     'url' => '/hospital-marketing/internal-marketing'],
    ['label' => '안과마케팅',     'url' => '/hospital-marketing/eye-marketing'],
    ['label' => '의료기기마케팅', 'url' => '/hospital-marketing/device-marketing'],
  ]],
  ['label' => 'AI마케팅', 'url' => '/ai-marketing', 'children' => [
    ['label' => 'GEO — 생성AI 최적화', 'url' => '/ai-marketing/geo', 'children' => [
      ['label' => 'GEO란?',      'url' => '/ai-marketing/geo#what-is-geo'],
      ['label' => 'GEO 프로세스','url' => '/ai-marketing/geo#process'],
      ['label' => 'GEO 효과',    'url' => '/ai-marketing/geo#effects'],
    ]],
    ['label' => 'AEO — 답변엔진 최적화', 'url' => '/ai-marketing/aeo', 'children' => [
      ['label' => 'AEO란?',      'url' => '/ai-marketing/aeo#what-is-aeo'],
      ['label' => 'AEO 프로세스','url' => '/ai-marketing/aeo#process'],
      ['label' => 'AEO 효과',    'url' => '/ai-marketing/aeo#effects'],
    ]],
    ['label' => 'SEO — 검색엔진 최적화', 'url' => '/ai-marketing/seo', 'children' => [
      ['label' => 'SEO란?',          'url' => '/ai-marketing/seo#what-is-seo'],
      ['label' => '콘텐츠 SEO',      'url' => '/ai-marketing/seo#content-seo'],
      ['label' => '테크니컬 SEO',    'url' => '/ai-marketing/seo#technical-seo'],
      ['label' => '링크빌딩 SEO',    'url' => '/ai-marketing/seo#link-building'],
      ['label' => 'SEO 프로세스',    'url' => '/ai-marketing/seo#process'],
      ['label' => 'SEO 효과',        'url' => '/ai-marketing/seo#effects'],
      ['label' => 'SEO 용어 사전',   'url' => '/ai-marketing/seo#glossary'],
    ]],
  ]],
  ['label' => '병원홈페이지 제작', 'url' => '/hospital-website', 'children' => [
    ['label' => '기본형 (5페이지)',       'url' => '/hospital-website/basic'],
    ['label' => '중급형 (10페이지)',      'url' => '/hospital-website/standard'],
    ['label' => '고급형 (10페이지 이상)','url' => '/hospital-website/premium'],
  ]],
  ['label' => '온라인마케팅', 'url' => '/online-marketing', 'children' => [
    ['label' => '검색광고', 'url' => '/online-marketing/search-ads', 'children' => [
      ['label' => '파워링크',      'url' => '/online-marketing/power-link'],
      ['label' => '파워컨텐츠',   'url' => '/online-marketing/power-content'],
      ['label' => '브랜드검색광고','url' => '/online-marketing/brand-search'],
      ['label' => '플레이스검색광고','url' => '/online-marketing/place-ad'],
    ]],
    ['label' => 'SNS & 앱 광고', 'url' => '/online-marketing/sns', 'children' => [
      ['label' => '인스타그램', 'url' => '/online-marketing/instagram'],
      ['label' => '페이스북',   'url' => '/online-marketing/facebook'],
      ['label' => '당근마켓',   'url' => '/online-marketing/daangn'],
    ]],
    ['label' => '언론',          'url' => '/online-marketing/press'],
    ['label' => '브랜드마케팅', 'url' => '/online-marketing/brand', 'children' => [
      ['label' => '브랜드기획',   'url' => '/online-marketing/brand-planning'],
      ['label' => '콘텐츠마케팅','url' => '/online-marketing/content-marketing'],
      ['label' => '브랜드블로그','url' => '/online-marketing/brand-blog'],
      ['label' => '영상콘텐츠',  'url' => '/online-marketing/video-content'],
    ]],
  ]],
  ['label' => '블로그', 'url' => '/blog', 'children' => [
    ['label' => '칼럼', 'url' => '/blog/column', 'children' => [
      ['label' => '병원마케팅 인사이트', 'url' => '/blog/category/insight'],
      ['label' => '마케팅 팁',          'url' => '/blog/category/tips'],
      ['label' => 'SEO',               'url' => '/blog/category/seo'],
      ['label' => 'GEO',               'url' => '/blog/category/geo'],
      ['label' => 'AEO',               'url' => '/blog/category/aeo'],
    ]],
    ['label' => '지역마케팅', 'url' => '/blog/region', 'children' => [
      ['label' => '인천병원마케팅', 'url' => '/blog/category/incheon'],
      ['label' => '대전병원마케팅', 'url' => '/blog/category/daejeon'],
      ['label' => '대구병원마케팅', 'url' => '/blog/category/daegu'],
      ['label' => '부산병원마케팅', 'url' => '/blog/category/busan'],
    ]],
  ]],
];

function render_sitemap_items(array $items, int $depth = 1): void {
    $class = 'sitemap-l' . $depth;
    echo "<ul class=\"{$class}\">";
    foreach ($items as $item) {
        $is_active = str_contains(get_permalink() . $_SERVER['REQUEST_URI'], parse_url($item['url'], PHP_URL_PATH) ?? '');
        $href = home_url($item['url']);
        echo '<li>';
        echo '<a href="' . esc_url($href) . '"' . ($is_active ? ' class="active"' : '') . '>' . esc_html($item['label']) . '</a>';
        if (!empty($item['children']) && $depth < 3) {
            render_sitemap_items($item['children'], $depth + 1);
        }
        echo '</li>';
    }
    echo '</ul>';
}
?>

<aside class="sidebar-left" aria-label="전체 사이트맵">
  <nav class="sitemap-nav">
    <div class="sitemap-nav-title">전체 메뉴</div>
    <?php render_sitemap_items($sitemap); ?>

    <div style="margin-top:24px;padding-top:16px;border-top:1px solid var(--color-hairline);">
      <a href="<?php echo home_url('/contact'); ?>" class="btn btn-primary btn-sm" style="width:100%;justify-content:center;">
        무료 상담 신청
      </a>
    </div>
  </nav>
</aside>
