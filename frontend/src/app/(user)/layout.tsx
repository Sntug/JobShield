"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";

export default function UserLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, error, refreshUser } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const isUserPortal = ["/dashboard", "/history", "/saved", "/profile"].includes(pathname) || pathname === "/reports" || pathname.startsWith("/reports/");

  useEffect(() => {
    if (isUserPortal && !loading && !user && !error) {
      router.push("/login");
    }
  }, [isUserPortal, user, loading, error, router]);

  if (!isUserPortal) {
    return children;
  }

  if (loading && !user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <p className="text-sm font-medium text-slate-500">Đang tải thông tin tài khoản...</p>
      </div>
    );
  }

  const retryMessage = error ? (
    <div role="alert" className="m-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
      <p>{error}</p>
      <button type="button" onClick={() => void refreshUser()} className="mt-2 rounded border border-rose-300 px-3 py-2 font-medium">
        Thử lại
      </button>
    </div>
  ) : null;

  if (!user) return retryMessage;

  const navItems = [
    { href: "/dashboard", label: "Tổng quan" },
    { href: "/history", label: "Lịch sử phân tích" },
    { href: "/saved", label: "Tin đã lưu" },
    { href: "/reports", label: "Báo cáo" },
    { href: "/profile", label: "Hồ sơ & Bảo mật" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 transition-colors dark:bg-slate-950">
      <Header />
      {retryMessage}
      <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        {/* Sub-navigation bar cho user portal */}
        <div className="flex border-b border-slate-200 mb-8 overflow-x-auto dark:border-slate-800">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`border-b-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-sky-600 text-sky-700 font-semibold dark:border-sky-400 dark:text-sky-300"
                    : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300 dark:text-slate-400 dark:hover:text-slate-200"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
        {children}
      </div>
      <Footer />
    </div>
  );
}
