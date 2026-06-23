<?php
/**
 * Template Name: 상담 신청
 */
get_header(); ?>

<section style="background:linear-gradient(135deg,var(--navy),#1e3a5f);padding:80px 0 60px;color:#fff;text-align:center">
  <div class="container">
    <span class="section-badge" style="background:rgba(255,255,255,.15);color:#fff;border-color:rgba(255,255,255,.3);margin-bottom:16px">FREE CONSULTATION</span>
    <h1 style="font-size:2.5rem;font-weight:800;margin-bottom:16px">무료 마케팅 진단 신청</h1>
    <p style="font-size:1.125rem;opacity:.85">전문가가 직접 분석하고 맞춤 전략을 제안해 드립니다.</p>
  </div>
</section>

<div class="container" style="max-width:960px;padding:80px 24px">
  <div style="display:grid;grid-template-columns:1fr 1.5fr;gap:48px;align-items:start">

    <!-- Benefits -->
    <div>
      <h2 style="font-size:1.375rem;font-weight:700;color:var(--navy);margin-bottom:24px">무료 진단에 포함되는 것</h2>
      <ul style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:16px">
        <?php
        $items = [
          ['🔍','현재 SEO 점수 분석','구글·네이버 검색 노출 현황 진단'],
          ['🤖','AI 검색 인용 현황','ChatGPT·Perplexity 인용 여부 확인'],
          ['📊','경쟁사 비교 분석','동종 병원 대비 포지셔닝 분석'],
          ['📋','맞춤 전략 제안서','진료과·지역 특화 마케팅 로드맵'],
        ];
        foreach($items as $item): ?>
        <li style="display:flex;gap:16px;align-items:flex-start;padding:20px;background:var(--gray-50);border-radius:12px">
          <span style="font-size:1.5rem;flex-shrink:0"><?php echo $item[0]; ?></span>
          <div>
            <div style="font-weight:700;color:var(--navy);margin-bottom:4px"><?php echo $item[1]; ?></div>
            <div style="font-size:.875rem;color:var(--gray-500)"><?php echo $item[2]; ?></div>
          </div>
        </li>
        <?php endforeach; ?>
      </ul>

      <div style="margin-top:32px;padding:20px;background:#fff7ed;border-radius:12px;border-left:4px solid #f97316">
        <div style="font-weight:700;color:#c2410c;margin-bottom:4px">📞 전화 상담</div>
        <div style="font-size:1.25rem;font-weight:800;color:var(--navy)">02-0000-0000</div>
        <div style="font-size:.875rem;color:var(--gray-500);margin-top:4px">평일 09:00 – 18:00</div>
      </div>
    </div>

    <!-- Form -->
    <div style="background:#fff;border:1px solid var(--gray-100);border-radius:20px;padding:40px">
      <h3 style="font-size:1.25rem;font-weight:700;color:var(--navy);margin-bottom:28px">상담 신청서 작성</h3>
      <form id="contact-form" method="post">
        <?php wp_nonce_field('mm_contact','mm_contact_nonce'); ?>
        <input type="hidden" name="action" value="mm_contact">

        <div style="margin-bottom:20px">
          <label style="display:block;font-size:.875rem;font-weight:600;color:var(--gray-700);margin-bottom:6px">병원명 <span style="color:#ef4444">*</span></label>
          <input type="text" name="hospital" required placeholder="○○의원 / ○○병원"
                 style="width:100%;padding:12px 16px;border:1.5px solid var(--gray-200);border-radius:10px;font-size:.9375rem;box-sizing:border-box">
        </div>

        <div style="margin-bottom:20px">
          <label style="display:block;font-size:.875rem;font-weight:600;color:var(--gray-700);margin-bottom:6px">진료과목 <span style="color:#ef4444">*</span></label>
          <select name="specialty" required style="width:100%;padding:12px 16px;border:1.5px solid var(--gray-200);border-radius:10px;font-size:.9375rem;background:#fff;box-sizing:border-box">
            <option value="">선택하세요</option>
            <option>성형외과</option><option>피부과</option><option>치과</option>
            <option>정형외과</option><option>한의원</option><option>비만클리닉</option><option>기타</option>
          </select>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
          <div>
            <label style="display:block;font-size:.875rem;font-weight:600;color:var(--gray-700);margin-bottom:6px">담당자명 <span style="color:#ef4444">*</span></label>
            <input type="text" name="name" required placeholder="홍길동"
                   style="width:100%;padding:12px 16px;border:1.5px solid var(--gray-200);border-radius:10px;font-size:.9375rem;box-sizing:border-box">
          </div>
          <div>
            <label style="display:block;font-size:.875rem;font-weight:600;color:var(--gray-700);margin-bottom:6px">연락처 <span style="color:#ef4444">*</span></label>
            <input type="tel" name="phone" required placeholder="010-0000-0000"
                   style="width:100%;padding:12px 16px;border:1.5px solid var(--gray-200);border-radius:10px;font-size:.9375rem;box-sizing:border-box">
          </div>
        </div>

        <div style="margin-bottom:20px">
          <label style="display:block;font-size:.875rem;font-weight:600;color:var(--gray-700);margin-bottom:6px">이메일</label>
          <input type="email" name="email" placeholder="example@hospital.com"
                 style="width:100%;padding:12px 16px;border:1.5px solid var(--gray-200);border-radius:10px;font-size:.9375rem;box-sizing:border-box">
        </div>

        <div style="margin-bottom:28px">
          <label style="display:block;font-size:.875rem;font-weight:600;color:var(--gray-700);margin-bottom:6px">문의 내용</label>
          <textarea name="message" rows="4" placeholder="현재 마케팅 고민이나 원하시는 서비스를 알려주세요."
                    style="width:100%;padding:12px 16px;border:1.5px solid var(--gray-200);border-radius:10px;font-size:.9375rem;resize:vertical;box-sizing:border-box"></textarea>
        </div>

        <div id="form-message" style="margin-bottom:16px;font-size:.875rem;min-height:20px"></div>

        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;font-size:1rem;padding:16px">
          무료 진단 신청하기 →
        </button>
        <p style="font-size:.75rem;color:var(--gray-400);text-align:center;margin-top:12px">개인정보는 상담 목적으로만 활용되며 외부에 제공되지 않습니다.</p>
      </form>
    </div>

  </div>
</div>

<?php get_footer();
