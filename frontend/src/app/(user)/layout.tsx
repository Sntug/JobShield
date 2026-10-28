"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { Header } from "@/components/layout/header";

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
    <div className="min-h-screen bg-slate-50">
      <Header />
      {retryMessage}
      <div className="mx-auto max-w-6xl px-6 py-8">
        {/* Sub-navigation bar cho user portal */}
        <div className="flex border-b border-slate-200 mb-8 overflow-x-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`border-b-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-slate-900 text-slate-900 font-semibold"
                    : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
        {children}
      </div>
    </div>
  );
}
