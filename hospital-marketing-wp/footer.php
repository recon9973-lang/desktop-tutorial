</div><!-- #page-content -->

<!-- ===== FOOTER ===== -->
<footer class="site-footer" role="contentinfo">
  <div class="container">
    <div class="footer-grid">
      <!-- 브랜드 -->
      <div class="footer-brand">
        <div class="logo">메디<span>마케팅</span></div>
        <p>AI 시대 병원마케팅의 새로운 기준.<br>
           SEO·AEO·GEO 통합 전략으로<br>
           광고 없이 환자를 모읍니다.</p>
        <div class="footer-sns">
          <a href="#" aria-label="블로그">📝</a>
          <a href="#" aria-label="유튜브">▶</a>
          <a href="#" aria-label="인스타그램">📷</a>
          <a href="#" aria-label="카카오톡">💬</a>
        </div>
      </div>

      <!-- 서비스 -->
      <div class="footer-col">
        <h4>서비스</h4>
        <ul>
          <li><a href="<?php echo esc_url(home_url('/services/geo/')); ?>">GEO 서비스</a></li>
          <li><a href="<?php echo esc_url(home_url('/services/aeo/')); ?>">AEO 서비스</a></li>
          <li><a href="<?php echo esc_url(home_url('/services/seo/')); ?>">SEO 서비스</a></li>
          <li><a href="<?php echo esc_url(home_url('/services/hospital-marketing/')); ?>">병원마케팅 광고</a></li>
          <li><a href="<?php echo esc_url(home_url('/services/website/')); ?>">홈페이지 제작</a></li>
          <li><a href="<?php echo esc_url(home_url('/services/sns/')); ?>">SNS 관리</a></li>
        </ul>
      </div>

      <!-- 위키 -->
      <div class="footer-col">
        <h4>위키</h4>
        <ul>
          <li><a href="<?php echo esc_url(home_url('/wiki/geo/')); ?>">GEO란?</a></li>
          <li><a href="<?php echo esc_url(home_url('/wiki/aeo/')); ?>">AEO란?</a></li>
          <li><a href="<?php echo esc_url(home_url('/wiki/hospital-seo/')); ?>">병원 SEO 가이드</a></li>
          <li><a href="<?php echo esc_url(home_url('/wiki/naver-marketing/')); ?>">네이버 마케팅</a></li>
          <li><a href="<?php echo esc_url(home_url('/wiki/llms-txt/')); ?>">llms.txt 가이드</a></li>
          <li><a href="<?php echo esc_url(home_url('/wiki/')); ?>">전체 위키 →</a></li>
        </ul>
      </div>

      <!-- 회사 -->
      <div class="footer-col">
        <h4>회사</h4>
        <ul>
          <li><a href="<?php echo esc_url(home_url('/about/')); ?>">회사 소개</a></li>
          <li><a href="<?php echo esc_url(home_url('/cases/')); ?>">성과 사례</a></li>
          <li><a href="<?php echo esc_url(home_url('/blog/')); ?>">블로그</a></li>
          <li><a href="<?php echo esc_url(home_url('/tools/')); ?>">무료 도구</a></li>
          <li><a href="<?php echo esc_url(home_url('/contact/')); ?>">상담 신청</a></li>
        </ul>
      </div>
    </div>

    <div class="footer-bottom">
      <div>
        <p>© <?php echo date('Y'); ?> <?php bloginfo('name'); ?>. All rights reserved.</p>
        <p class="footer-biz">
          사업자등록번호: 000-00-00000 &nbsp;|&nbsp; 대표: 홍길동 &nbsp;|&nbsp; 서울특별시 강남구<br>
          통신판매업신고번호: 제2024-서울강남-0000호
        </p>
      </div>
      <div class="footer-links">
        <a href="<?php echo esc_url(home_url('/privacy/')); ?>">개인정보처리방침</a>
        <a href="<?php echo esc_url(home_url('/terms/')); ?>">이용약관</a>
        <a href="<?php echo esc_url(home_url('/sitemap/')); ?>">사이트맵</a>
      </div>
    </div>
  </div>
</footer>

<?php wp_footer(); ?>
</body>
</html>
