"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

export function Header() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-40">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
        <div className="flex items-center gap-6">
          <Link href="/" className="text-xl font-bold tracking-tight text-slate-900">
            JobShield
          </Link>
          <nav aria-label="Điều hướng chính" className="hidden md:flex items-center gap-5 text-sm font-medium text-slate-600">
            <Link href="/analyze" className="hover:text-slate-900 transition-colors">
              Phân tích tin
            </Link>
            <Link href="/verify-employer" className="hover:text-slate-900 transition-colors">
              Xác minh công ty
            </Link>
            <Link href="/safety" className="hover:text-slate-900 transition-colors">
              An toàn
            </Link>
            {user && (
              <>
                <Link href="/dashboard" className="hover:text-slate-900 transition-colors">
                  Bảng điều khiển
                </Link>
                <Link href="/history" className="hover:text-slate-900 transition-colors">
                  Lịch sử
                </Link>
                <Link href="/saved" className="hover:text-slate-900 transition-colors">
                  Đã lưu
                </Link>
                <Link href="/reports" className="hover:text-slate-900 transition-colors">
                  Báo cáo
                </Link>
                {user.role === "admin" && (
                  <Link href="/admin" className="font-semibold text-rose-600 hover:text-rose-800 transition-colors">
                    Quản trị
                  </Link>
                )}
              </>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {!loading && (
            <>
              {user ? (
                <div className="flex items-center gap-3 text-sm">
                  <Link
                    href="/profile"
                    className="font-medium text-slate-800 hover:text-slate-950 underline decoration-slate-300 underline-offset-4"
                  >
                    {user.full_name}
                  </Link>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    Đăng xuất
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Link
                    href="/login"
                    className="px-3 py-1.5 text-slate-700 hover:text-slate-900"
                  >
                    Đăng nhập
                  </Link>
                  <Link
                    href="/register"
                    className="rounded-lg bg-slate-900 px-3 py-1.5 text-white hover:bg-slate-800 transition-colors"
                  >
                    Đăng ký
                  </Link>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  );
}
