"use client";

import React, { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

const ADMIN_NAV = [
  { href: "/admin", label: "Tổng quan" },
  { href: "/admin/reports", label: "Kiểm duyệt báo cáo" },
  { href: "/admin/employers", label: "Kho nhà tuyển dụng" },
  { href: "/admin/warnings", label: "Cảnh báo công khai" },
  { href: "/admin/rules", label: "Quy tắc phát hiện" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  if (loading) {
    return (
      <div className="py-24 text-center text-sm text-slate-500">
        Đang xác thực quyền truy cập...
      </div>
    );
  }

  if (!user || user.role !== "admin") {
    return (
      <div className="mx-auto max-w-md px-4 py-24 text-center">
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-8 shadow-sm">
          <h2 className="text-xl font-bold text-rose-900">Không có quyền truy cập</h2>
          <p className="mt-2 text-sm text-rose-700">
            Khu vực này yêu cầu tài khoản có vai trò Quản trị viên (Admin).
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link
              href="/"
              className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
            >
              Về trang chủ
            </Link>
            <Link
              href="/login"
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              Đăng nhập tài khoản khác
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50/50">
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-12 items-center justify-between">
            <div className="flex items-center gap-6">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Khu vực Quản trị
              </span>
              <nav aria-label="Điều hướng quản trị" className="flex space-x-1 sm:space-x-4">
                {ADMIN_NAV.map((item) => {
                  const isActive =
                    item.href === "/admin"
                      ? pathname === "/admin"
                      : pathname?.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                        isActive
                          ? "bg-slate-900 text-white"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                      }`}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
            <div className="text-xs text-slate-500">
              Admin: <span className="font-semibold text-slate-800">{user.full_name}</span>
            </div>
          </div>
        </div>
      </div>

      <main>{children}</main>
    </div>
  );
}
