"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { ShieldCheck, Menu, X, Sparkles, Building2, ShieldAlert, LayoutDashboard, History, Bookmark, Flag, Shield } from "lucide-react";

export function Header() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const navLinks = [
    { href: "/analyze", label: "Phân tích tin", icon: Sparkles },
    { href: "/verify-employer", label: "Xác minh công ty", icon: Building2 },
    { href: "/safety", label: "An toàn", icon: ShieldAlert },
  ];

  const userNavLinks = [
    { href: "/dashboard", label: "Bảng điều khiển", icon: LayoutDashboard },
    { href: "/history", label: "Lịch sử", icon: History },
    { href: "/saved", label: "Đã lưu", icon: Bookmark },
    { href: "/reports", label: "Báo cáo", icon: Flag },
  ];

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur-md transition-colors dark:border-slate-800 dark:bg-slate-950/95">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        {/* Logo & Desktop Nav */}
        <div className="flex items-center gap-7">
          <Link
            href="/"
            className="group flex items-center gap-2.5 text-xl font-bold tracking-tight text-slate-900 dark:text-white"
          >
            <span className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-blue-700 text-white shadow-md shadow-sky-500/20 transition-transform group-hover:scale-105">
              <ShieldCheck className="size-5" />
            </span>
            <div className="flex flex-col">
              <span className="leading-tight">JobShield</span>
              <span className="text-[10px] font-medium tracking-normal text-sky-600 dark:text-sky-400">
                Phòng chống lừa đảo
              </span>
            </div>
          </Link>

          <nav
            aria-label="Điều hướng chính"
            className="hidden items-center gap-1 text-sm font-medium text-slate-600 md:flex dark:text-slate-300"
          >
            {navLinks.map((item) => {
              const active = isActive(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-2 transition-all ${
                    active
                      ? "bg-sky-50 font-semibold text-sky-700 dark:bg-sky-950/50 dark:text-sky-300"
                      : "hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-900 dark:hover:text-slate-100"
                  }`}
                >
                  <Icon className="size-4 opacity-75" />
                  <span>{item.label}</span>
                </Link>
              );
            })}

            {user && (
              <>
                <span className="mx-1 h-4 w-px bg-slate-200 dark:bg-slate-800" />
                {userNavLinks.map((item) => {
                  const active = isActive(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={`rounded-lg px-2.5 py-2 transition-all ${
                        active
                          ? "bg-slate-100 font-semibold text-slate-900 dark:bg-slate-800 dark:text-white"
                          : "hover:bg-slate-100 hover:text-slate-900 dark:hover:bg-slate-900 dark:hover:text-slate-100"
                      }`}
                    >
                      {item.label}
                    </Link>
                  );
                })}

                {user.role === "admin" && (
                  <Link
                    href="/admin"
                    className="flex items-center gap-1 rounded-lg px-2.5 py-2 font-semibold text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:text-rose-400 dark:hover:bg-rose-950/40"
                  >
                    <Shield className="size-3.5" />
                    <span>Quản trị</span>
                  </Link>
                )}
              </>
            )}
          </nav>
        </div>

        {/* Right CTA / Auth controls */}
        <div className="flex items-center gap-3">
          {!loading && (
            <>
              {user ? (
                <div className="flex items-center gap-3 text-sm">
                  <Link
                    href="/profile"
                    className="flex items-center gap-2 rounded-lg py-1 px-2 font-medium text-slate-800 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-200 dark:hover:bg-slate-800 underline decoration-slate-300 underline-offset-4"
                  >
                    <span className="flex size-6 items-center justify-center rounded-full bg-sky-100 text-xs font-bold text-sky-800 dark:bg-sky-900 dark:text-sky-200">
                      {user.full_name.charAt(0).toUpperCase()}
                    </span>
                    <span className="hidden sm:inline">{user.full_name}</span>
                  </Link>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-rose-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    Đăng xuất
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Link
                    href="/login"
                    className="hidden rounded-lg px-3 py-1.5 text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900 sm:inline-block dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white"
                  >
                    Đăng nhập
                  </Link>
                  <Link
                    href="/register"
                    className="rounded-lg bg-sky-600 px-3.5 py-1.5 text-xs sm:text-sm font-semibold text-white shadow-sm shadow-sky-600/30 transition-all hover:bg-sky-700 hover:shadow-sky-600/40"
                  >
                    Đăng ký
                  </Link>
                </div>
              )}
            </>
          )}

          {/* Mobile hamburger button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 md:hidden dark:text-slate-300 dark:hover:bg-slate-900"
            aria-label={mobileMenuOpen ? "Đóng menu" : "Mở menu điều hướng"}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="border-b border-slate-200 bg-white px-4 pt-2 pb-6 md:hidden dark:border-slate-800 dark:bg-slate-950">
          <nav aria-label="Điều hướng di động" className="space-y-1">
            <Link
              href="/"
              onClick={() => setMobileMenuOpen(false)}
              className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                pathname === "/"
                  ? "bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300"
                  : "text-slate-700 hover:bg-slate-50 dark:text-slate-300"
              }`}
            >
              Trang chủ
            </Link>
            {navLinks.map((item) => {
              const active = isActive(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${
                    active
                      ? "bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300"
                      : "text-slate-700 hover:bg-slate-50 dark:text-slate-300"
                  }`}
                >
                  <Icon className="size-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}

            {user && (
              <>
                <div className="my-2 border-t border-slate-100 pt-2 dark:border-slate-800" />
                <p className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Tài khoản của bạn
                </p>
                {userNavLinks.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:text-slate-300"
                  >
                    {item.label}
                  </Link>
                ))}
                {user.role === "admin" && (
                  <Link
                    href="/admin"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block rounded-lg px-3 py-2 text-sm font-semibold text-rose-600 hover:bg-rose-50"
                  >
                    Trang Quản trị
                  </Link>
                )}
              </>
            )}

            {!user && (
              <div className="mt-4 pt-4 border-t border-slate-100 space-y-2">
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block w-full text-center rounded-lg border border-slate-200 py-2 text-sm font-medium text-slate-700"
                >
                  Đăng nhập
                </Link>
              </div>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
