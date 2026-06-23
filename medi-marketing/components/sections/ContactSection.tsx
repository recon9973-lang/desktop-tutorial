"use client";

import { useState } from "react";
import { CheckCircle } from "lucide-react";

const BENEFITS = [
  { title: "무료 마케팅 현황 진단", desc: "현재 병원 온라인 마케팅 상태 분석 리포트 제공" },
  { title: "경쟁 병원 분석 포함", desc: "지역 내 경쟁 병원 키워드·SEO 현황 비교 제공" },
  { title: "맞춤 전략 제안서 제공", desc: "병원 상황에 맞는 마케팅 로드맵 무료 제안" },
];

const SERVICES_LIST = ["병원마케팅 (광고)", "홈페이지 제작", "SEO/GEO/AEO", "SNS 관리", "블로그 운영", "기타"];

export default function ContactSection() {
  const [selected, setSelected] = useState<string[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const toggle = (s: string) =>
    setSelected((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <section id="contact" className="py-24 bg-gray-900 section-fade">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid lg:grid-cols-2 gap-16 items-start">
          {/* Left */}
          <div>
            <span className="inline-block px-4 py-1.5 bg-blue-600/20 border border-blue-500/30 text-blue-400 rounded-full text-sm font-semibold mb-6">
              무료 상담 신청
            </span>
            <h2 className="text-3xl lg:text-4xl font-black text-white mb-6 leading-tight">
              지금 바로 시작하세요<br />
              <span className="text-blue-400">무료 진단은 24시간</span><br />
              안에 연락드립니다
            </h2>
            <div className="space-y-5">
              {BENEFITS.map((b) => (
                <div key={b.title} className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center flex-shrink-0">
                    <CheckCircle className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <div className="text-white font-semibold">{b.title}</div>
                    <div className="text-gray-400 text-sm">{b.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Form */}
          <div className="bg-white rounded-2xl p-8">
            {submitted ? (
              <div className="text-center py-10">
                <div className="text-5xl mb-4">🎉</div>
                <h3 className="text-2xl font-black text-gray-900 mb-2">신청 완료!</h3>
                <p className="text-gray-500">24시간 안에 담당자가 연락드립니다.</p>
              </div>
            ) : (
              <>
                <h3 className="text-xl font-bold text-gray-900 mb-6">무료 상담 신청서</h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        병원명 <span className="text-red-500">*</span>
                      </label>
                      <input
                        required
                        type="text"
                        placeholder="○○의원"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        담당자명 <span className="text-red-500">*</span>
                      </label>
                      <input
                        required
                        type="text"
                        placeholder="홍길동"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      연락처 <span className="text-red-500">*</span>
                    </label>
                    <input
                      required
                      type="tel"
                      placeholder="010-0000-0000"
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      관심 서비스 <span className="text-red-500">*</span>
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {SERVICES_LIST.map((s) => (
                        <label
                          key={s}
                          className={`flex items-center gap-2 p-2.5 border rounded-lg cursor-pointer transition ${
                            selected.includes(s)
                              ? "border-blue-500 bg-blue-50"
                              : "border-gray-200 hover:border-blue-300 hover:bg-blue-50"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selected.includes(s)}
                            onChange={() => toggle(s)}
                            className="text-blue-600 rounded"
                          />
                          <span className="text-sm text-gray-700">{s}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">문의 내용</label>
                    <textarea
                      rows={3}
                      placeholder="궁금한 점이나 현재 상황을 간단히 적어주세요"
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
                    />
                  </div>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input required type="checkbox" className="mt-0.5 text-blue-600 rounded" />
                    <span className="text-xs text-gray-500">
                      개인정보 수집·이용에 동의합니다. 수집된 정보는 상담 목적으로만 활용됩니다.{" "}
                      <a href="/privacy" className="text-blue-600 underline">개인정보처리방침</a>
                    </span>
                  </label>
                  <button
                    type="submit"
                    className="w-full py-4 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 transition text-base shadow-lg shadow-blue-500/30"
                  >
                    무료 상담 신청하기 →
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
