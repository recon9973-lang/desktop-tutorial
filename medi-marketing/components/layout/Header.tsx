"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, X, ChevronDown } from "lucide-react";
import { NAV_ITEMS } from "@/lib/data/menu";

export default function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openMobile, setOpenMobile] = useState<string | null>(null);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-white/95 backdrop-blur-sm shadow-sm border-b border-gray-100" : "bg-transparent"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">M</span>
          </div>
          <span className={`font-bold text-xl transition-colors ${scrolled ? "text-gray-900" : "text-white"}`}>
            메디<span className="text-blue-400">마케팅</span>
          </span>
        </Link>

        {/* Desktop Menu */}
        <div className="hidden lg:flex items-center gap-8">
          {NAV_ITEMS.map((item) => (
            <div key={item.label} className="relative group">
              <Link
                href={item.href}
                className={`nav-link flex items-center gap-1 text-sm font-medium py-2 transition-colors ${
                  scrolled ? "text-gray-700 hover:text-blue-600" : "text-white/90 hover:text-white"
                }`}
              >
                {item.label}
                {item.badge && (
                  <span className="ml-1 px-1.5 py-0.5 text-xs bg-cyan-100 text-cyan-700 rounded font-bold">
                    {item.badge}
                  </span>
                )}
                {item.children && <ChevronDown className="w-3 h-3" />}
              </Link>
              {item.children && (
                <div className="absolute top-full left-0 mt-2 w-52 bg-white rounded-xl shadow-xl border border-gray-100 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-50">
                  {item.children.map((child) => (
                    <Link
                      key={child.href}
                      href={child.href}
                      className="block px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                    >
                      {child.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Desktop CTA */}
        <div className="hidden lg:flex items-center gap-3">
          <Link
            href="/contact"
            className={`text-sm font-medium transition-colors ${scrolled ? "text-gray-600 hover:text-blue-600" : "text-white/80 hover:text-white"}`}
          >
            문의하기
          </Link>
          <Link
            href="#contact"
            className="btn-pulse px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition"
          >
            무료 상담 신청
          </Link>
        </div>

        {/* Mobile Toggle */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className={`lg:hidden p-2 rounded-lg transition-colors ${scrolled ? "hover:bg-gray-100 text-gray-700" : "hover:bg-white/10 text-white"}`}
        >
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </nav>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="lg:hidden bg-white border-t border-gray-100 shadow-xl">
          <div className="max-w-7xl mx-auto px-6 py-4 space-y-1">
            {NAV_ITEMS.map((item) => (
              <div key={item.label}>
                <button
                  onClick={() => setOpenMobile(openMobile === item.label ? null : item.label)}
                  className="w-full flex items-center justify-between px-3 py-3 text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                >
                  <span>{item.label}</span>
                  {item.children && (
                    <ChevronDown className={`w-4 h-4 transition-transform ${openMobile === item.label ? "rotate-180" : ""}`} />
                  )}
                </button>
                {item.children && openMobile === item.label && (
                  <div className="ml-4 mt-1 space-y-1 pb-2">
                    {item.children.map((child) => (
                      <Link
                        key={child.href}
                        href={child.href}
                        onClick={() => setMobileOpen(false)}
                        className="block px-3 py-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                      >
                        {child.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div className="pt-4 border-t border-gray-100">
              <Link
                href="#contact"
                onClick={() => setMobileOpen(false)}
                className="block w-full text-center py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition"
              >
                무료 상담 신청하기
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
