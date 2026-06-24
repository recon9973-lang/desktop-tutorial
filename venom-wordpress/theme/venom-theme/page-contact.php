<?php
/**
 * Template Name: 문의하기
 * 무료 상담 신청 페이지
 */
get_header(); ?>

<!-- Hero -->
<section class="gradient-mesh" style="padding:64px 0 48px;">
  <div class="container" style="text-align:center;">
    <span class="pill-tag">무료 상담 신청</span>
    <h1 class="display-xl" style="margin-top:1rem;">병원 마케팅, 베놈에게 맡겨보세요</h1>
    <p style="font-size:17px;color:var(--color-ink-secondary);margin-top:1rem;max-width:480px;margin-left:auto;margin-right:auto;">
      전문 마케터가 직접 병원 현황을 분석하고<br>맞춤 전략을 1:1로 제안드립니다.
    </p>
  </div>
</section>

<section class="section">
  <div class="container">
    <div style="display:grid;grid-template-columns:1fr 360px;gap:64px;align-items:start;">

      <!-- 폼 -->
      <div>
        <form id="venomContactForm" novalidate>
          <div class="form-row">
            <div class="form-group">
              <label for="f-name" class="form-label">이름 <span style="color:var(--color-ruby)">*</span></label>
              <input type="text" id="f-name" name="name" class="form-input" placeholder="김원장" required>
            </div>
            <div class="form-group">
              <label for="f-hospital" class="form-label">병원명</label>
              <input type="text" id="f-hospital" name="hospital" class="form-input" placeholder="○○○의원">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="f-phone" class="form-label">연락처 <span style="color:var(--color-ruby)">*</span></label>
              <input type="tel" id="f-phone" name="phone" class="form-input" placeholder="010-0000-0000" required>
            </div>
            <div class="form-group">
              <label for="f-email" class="form-label">이메일</label>
              <input type="email" id="f-email" name="email" class="form-input" placeholder="email@hospital.com">
            </div>
          </div>
          <div class="form-group">
            <label for="f-service" class="form-label">관심 서비스</label>
            <select id="f-service" name="service" class="form-select">
              <option value="">선택해 주세요</option>
              <optgroup label="병원마케팅">
                <option>치과마케팅</option>
                <option>피부과마케팅</option>
                <option>정형외과마케팅</option>
                <option>한의원마케팅</option>
                <option>성형외과마케팅</option>
                <option>내과마케팅</option>
                <option>안과마케팅</option>
                <option>의료기기마케팅</option>
                <option>의료광고심의</option>
              </optgroup>
              <optgroup label="AI마케팅">
                <option>GEO (생성AI 최적화)</option>
                <option>AEO (답변엔진 최적화)</option>
                <option>SEO (검색엔진 최적화)</option>
              </optgroup>
              <optgroup label="온라인마케팅">
                <option>검색광고 (파워링크 등)</option>
                <option>SNS 광고 (인스타·페북·당근)</option>
                <option>언론 보도</option>
                <option>브랜드마케팅</option>
              </optgroup>
              <option value="병원홈페이지 제작">병원홈페이지 제작</option>
              <option value="전체 통합 마케팅">전체 통합 마케팅</option>
            </select>
          </div>
          <div class="form-group">
            <label for="f-message" class="form-label">문의 내용</label>
            <textarea id="f-message" name="message" class="form-textarea" placeholder="현재 마케팅 현황이나 고민하시는 점을 자유롭게 작성해 주세요."></textarea>
          </div>
          <div class="form-group form-checkbox">
            <input type="checkbox" id="f-agree" name="agree" required>
            <label for="f-agree" style="font-size:13px;color:var(--color-ink-mute);">
              <a href="<?php echo home_url('/privacy'); ?>" style="text-decoration:underline;">개인정보처리방침</a>에 동의합니다. (필수)
            </label>
          </div>
          <div id="formMessage" style="font-size:14px;min-height:20px;margin-bottom:12px;" role="alert" aria-live="polite"></div>
          <button type="submit" class="btn btn-primary btn-lg" style="width:100%;justify-content:center;">
            상담 신청하기
          </button>
        </form>
      </div>

      <!-- 사이드 정보 -->
      <div>
        <div style="background:var(--color-canvas-soft);border-radius:var(--radius-lg);padding:32px;margin-bottom:24px;">
          <h3 class="heading-md" style="margin-bottom:24px;">빠른 연락</h3>
          <div style="display:flex;flex-direction:column;gap:20px;">
            <div style="display:flex;gap:12px;align-items:flex-start;">
              <div style="width:36px;height:36px;background:var(--color-primary-subdued);border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                <i data-lucide="phone" style="width:16px;height:16px;color:var(--color-primary);"></i>
              </div>
              <div>
                <div style="font-size:12px;color:var(--color-ink-mute);margin-bottom:4px;">대표 전화</div>
                <a href="tel:16614142" style="font-size:20px;font-weight:300;color:var(--color-ink);letter-spacing:-0.4px;">1661-4142</a>
              </div>
            </div>
            <div style="display:flex;gap:12px;align-items:flex-start;">
              <div style="width:36px;height:36px;background:var(--color-primary-subdued);border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                <i data-lucide="clock" style="width:16px;height:16px;color:var(--color-primary);"></i>
              </div>
              <div>
                <div style="font-size:12px;color:var(--color-ink-mute);margin-bottom:4px;">운영 시간</div>
                <div style="font-size:14px;color:var(--color-ink);">평일 09:00 – 18:00</div>
                <div style="font-size:12px;color:var(--color-ink-mute);">토·일·공휴일 휴무</div>
              </div>
            </div>
            <div style="display:flex;gap:12px;align-items:flex-start;">
              <div style="width:36px;height:36px;background:var(--color-primary-subdued);border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                <i data-lucide="map-pin" style="width:16px;height:16px;color:var(--color-primary);"></i>
              </div>
              <div>
                <div style="font-size:12px;color:var(--color-ink-mute);margin-bottom:4px;">주소</div>
                <div style="font-size:13px;color:var(--color-ink);line-height:1.6;">대구광역시 수성구<br>용학로25길 54, 4층</div>
              </div>
            </div>
          </div>
        </div>

        <div style="background:var(--color-brand-dark);border-radius:var(--radius-lg);padding:24px;color:#fff;">
          <h4 class="heading-sm" style="margin-bottom:12px;color:#fff;">상담 후 받게 되는 것</h4>
          <ul style="display:flex;flex-direction:column;gap:10px;">
            <?php
            $benefits = [
              '병원 온라인 현황 무료 진단',
              '경쟁 병원 마케팅 분석 리포트',
              '맞춤 마케팅 전략 제안서',
              '예상 광고비·ROI 계산서',
            ];
            foreach ($benefits as $b): ?>
              <li style="display:flex;gap:8px;align-items:flex-start;font-size:14px;color:rgba(255,255,255,0.85);">
                <i data-lucide="check-circle" style="width:15px;height:15px;color:var(--color-primary-soft);flex-shrink:0;margin-top:1px;"></i>
                <?php echo esc_html($b); ?>
              </li>
            <?php endforeach; ?>
          </ul>
        </div>
      </div>

    </div>
  </div>
</section>

<?php get_footer(); ?>
