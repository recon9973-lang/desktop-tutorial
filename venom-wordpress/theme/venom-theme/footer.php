<!-- CTA Band (페이지마다 공통) -->
<?php if (!is_page('contact')): ?>
<section class="section section-dark">
  <div class="container cta-band">
    <span class="pill-tag" style="background:rgba(255,255,255,0.15);color:rgba(255,255,255,0.9);">지금 시작하세요</span>
    <h2 style="margin-top:1rem;">병원 매출을 <span style="color:var(--color-primary-soft);">확실하게</span> 올리고 싶으신가요?</h2>
    <p>베놈의 병원 전문 마케터가 1:1로 현황을 분석하고 맞춤 전략을 제안합니다.</p>
    <div class="cta-band-btns">
      <a href="<?php echo home_url('/contact'); ?>" class="btn btn-primary btn-lg">무료 상담 신청하기</a>
      <a href="tel:16614142" class="btn btn-secondary btn-lg" style="color:#fff;border-color:rgba(255,255,255,0.3);">1661-4142 전화 상담</a>
    </div>
  </div>
</section>
<?php endif; ?>

<!-- Footer -->
<footer class="site-footer" role="contentinfo">
  <div class="container">
    <div class="footer-grid">

      <!-- Brand -->
      <div class="footer-brand">
        <a href="<?php echo home_url('/'); ?>" class="site-logo" aria-label="베놈 홈">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <rect width="28" height="28" rx="6" fill="#533afd"/>
            <path d="M6 8l8 12 8-12" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>병원마케팅 <strong>베놈</strong></span>
        </a>
        <p>병원 전문 디지털 마케팅 대행사.<br>SEO · GEO · AEO · SNS · 병원홈페이지 제작</p>
        <p style="margin-top:0.75rem;">
          <a href="tel:16614142" style="color:var(--color-ink-mute);">1661-4142</a>
        </p>
      </div>

      <!-- Services -->
      <div class="footer-col">
        <h4>병원마케팅</h4>
        <ul>
          <li><a href="<?php echo home_url('/hospital-marketing/dental-marketing'); ?>">치과마케팅</a></li>
          <li><a href="<?php echo home_url('/hospital-marketing/skin-marketing'); ?>">피부과마케팅</a></li>
          <li><a href="<?php echo home_url('/hospital-marketing/ortho-marketing'); ?>">정형외과마케팅</a></li>
          <li><a href="<?php echo home_url('/hospital-marketing/hani-marketing'); ?>">한의원마케팅</a></li>
          <li><a href="<?php echo home_url('/hospital-marketing/plastic-marketing'); ?>">성형외과마케팅</a></li>
          <li><a href="<?php echo home_url('/hospital-marketing/medical-ad-review'); ?>">의료광고심의</a></li>
        </ul>
      </div>

      <!-- AI Marketing -->
      <div class="footer-col">
        <h4>AI마케팅</h4>
        <ul>
          <li><a href="<?php echo home_url('/ai-marketing/geo'); ?>">GEO — 생성AI 최적화</a></li>
          <li><a href="<?php echo home_url('/ai-marketing/aeo'); ?>">AEO — 답변엔진 최적화</a></li>
          <li><a href="<?php echo home_url('/ai-marketing/seo'); ?>">SEO — 검색엔진 최적화</a></li>
          <li><a href="<?php echo home_url('/hospital-website'); ?>">병원홈페이지 제작</a></li>
          <li><a href="<?php echo home_url('/online-marketing'); ?>">온라인마케팅</a></li>
        </ul>
      </div>

      <!-- Blog -->
      <div class="footer-col">
        <h4>블로그</h4>
        <ul>
          <li><a href="<?php echo home_url('/blog/category/insight'); ?>">병원마케팅 인사이트</a></li>
          <li><a href="<?php echo home_url('/blog/category/seo'); ?>">SEO 정보</a></li>
          <li><a href="<?php echo home_url('/blog/category/geo'); ?>">GEO 정보</a></li>
          <li><a href="<?php echo home_url('/blog/category/aeo'); ?>">AEO 정보</a></li>
          <li><a href="<?php echo home_url('/blog/category/region'); ?>">지역마케팅</a></li>
        </ul>
      </div>

      <!-- Company -->
      <div class="footer-col">
        <h4>회사 정보</h4>
        <ul>
          <li><a href="<?php echo home_url('/about'); ?>">회사소개</a></li>
          <li><a href="<?php echo home_url('/history'); ?>">연혁</a></li>
          <li><a href="<?php echo home_url('/team'); ?>">조직도</a></li>
          <li><a href="<?php echo home_url('/contact'); ?>">무료 상담 신청</a></li>
        </ul>
      </div>

    </div><!-- /.footer-grid -->

    <!-- Footer Bottom -->
    <div class="footer-bottom">
      <div>
        <p>주식회사 베놈 · 대표 김보형 · 사업자등록번호 291-86-02777</p>
        <p style="margin-top:4px;">대구광역시 수성구 용학로25길 54, 4층 · 대표번호 1661-4142</p>
        <p style="margin-top:8px;">© <?php echo date('Y'); ?> 주식회사 베놈. All rights reserved.</p>
      </div>
      <div class="footer-bottom-links">
        <a href="<?php echo home_url('/privacy'); ?>">개인정보처리방침</a>
        <a href="<?php echo home_url('/terms'); ?>">이용약관</a>
        <a href="<?php echo home_url('/sitemap'); ?>">사이트맵</a>
      </div>
    </div>

  </div>
</footer>

<!-- Back to Top -->
<button class="back-to-top" id="backToTop" aria-label="맨 위로">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
    <polyline points="18 15 12 9 6 15"/>
  </svg>
</button>

<?php wp_footer(); ?>
</body>
</html>
